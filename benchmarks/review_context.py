"""Attach static source context to finite, linked diagnostic readings."""

from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import tokenize
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from benchmarks.corpora import CorpusError, Source, _checked_bytes
from benchmarks.review_readings import (
    _caller_lines,
    _display_chunks,
    _line_parts,
    _source_rows,
)
from proseprobe.parsers.python import PythonParser


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _physical(raw: bytes) -> tuple[str, list[tuple[str, str]]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CorpusError("context source must be UTF-8") from error
    if "\r" in text.replace("\r\n", "") or re.search(
        r"[\v\f\x1c-\x1e\x85\u2028\u2029]", text
    ):
        raise CorpusError("context requires LF or CRLF physical line separators")
    return text, [_line_parts(line) for line in text.splitlines(keepends=True)]


def _region(physical: list[tuple[str, str]], start: int, end: int) -> dict[str, int]:
    if (
        type(start) is not int
        or type(end) is not int
        or not 1 <= start <= end <= len(physical)
    ):
        raise CorpusError("invalid source line region")
    return {
        "line": start,
        "column": 1,
        "end_line": end,
        "end_column": len(physical[end - 1][0]) + 1,
    }


def _python_owners(
    text: str, physical: list[tuple[str, str]], start: int, end: int
) -> list[dict[str, Any]]:
    parser = PythonParser(text)
    tree = parser.get_syntax_tree()
    if tree is None:
        raise CorpusError("unsupported Python syntax; owning context unavailable")
    tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    owners = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if (node.end_lineno or node.lineno) < start:
            continue
        line, column, _, _ = parser.get_node_span(node)
        header_start = line
        if node.decorator_list:
            first = min(parser.get_node_span(item)[:2] for item in node.decorator_list)
            decorators = [
                token.start[0]
                for token in tokens
                if token.type == tokenize.OP
                and token.string == "@"
                and token.start[1] == column - 1
                and token.start < (first[0], first[1] - 1)
            ]
            if not decorators:
                raise CorpusError("owning decorator context unavailable")
            header_start = decorators[-1]
        if header_start > end:
            continue
        first_body = parser.get_node_span(node.body[0])[:2]
        body_start = (first_body[0], first_body[1] - 1)
        colon = None
        for token in tokens:
            if token.start < (line, column - 1):
                continue
            if token.type == tokenize.NEWLINE or token.start >= body_start:
                break
            if token.type == tokenize.OP and token.string == ":":
                colon = token
        if colon is None:
            raise CorpusError("owning signature colon unavailable")
        owners.append(
            {
                "name": node.name,
                "node_type": "class" if isinstance(node, ast.ClassDef) else "function",
                "header_region": _region(physical, header_start, colon.end[0]),
                "scope_region": {"line": node.lineno, "end_line": node.end_lineno},
            }
        )
    return sorted(
        owners, key=lambda item: (item["header_region"]["line"], item["name"])
    )


def _source_items(
    physical: list[tuple[str, str]], start: int, end: int, identity: str, checksum: str
) -> list[tuple[str, dict[str, Any] | None]]:
    displayed, rows = _source_rows(physical, start, end)
    return [
        (line, {**row, "source_id": identity, "sha256": checksum})
        for line, row in zip(displayed, rows, strict=True)
    ]


def _metadata_items(value: Any) -> list[tuple[str, dict[str, Any] | None]]:
    text = json.dumps(value, sort_keys=True, ensure_ascii=True)
    return [(chunk, None) for chunk in _display_chunks(text, 80)]


def _pages(
    sections: list[tuple[str, list[tuple[str, dict[str, Any] | None]]]],
    context: dict[str, Any],
    before: list[str],
    after: list[str],
    reading_id: str,
    directory: Path,
) -> list[dict[str, Any]]:
    digest = _digest(context)
    longest = max(
        (
            len(match.group())
            for _, items in sections
            for line, _ in items
            for match in re.finditer(r"`+", line)
        ),
        default=2,
    )
    fence = "`" * max(3, longest + 1)
    # The fixed envelope includes both navigation slots, even at the endpoints.
    capacity = 80 - len(before) - len(after) - 11
    if capacity < 1:
        raise CorpusError("mandatory context leaves no room within 80 lines")
    parts = [
        (role, items[offset : offset + capacity])
        for role, items in sections
        for offset in range(0, len(items), capacity)
    ]
    paths = [
        str(directory / f"{reading_id}-{index:04d}.txt")
        for index in range(1, len(parts) + 1)
    ]
    result = []
    for index, ((role, items), path) in enumerate(zip(parts, paths, strict=True), 1):
        heading = [
            f"Context reading {index}/{len(parts)}: {role}",
            f"Read: [this reading](<{path}>)",
            f"Context: {digest}",
            "Rules: " + ", ".join(context["rule_ids"]),
            f"Previous: [reading](<{paths[index - 2]}>)"
            if index > 1
            else "Previous: none",
            f"Next: [reading](<{paths[index]}>)"
            if index < len(parts)
            else "Next: none",
            "Source rows: original code points; other rows: derived metadata.",
            "Context supplies evidence, not reviewed or clean coverage.",
            fence + "text",
        ]
        lines = before + heading + [line for line, _ in items] + [fence, ""] + after
        if len(lines) > 80 or any(len(line) > 80 for line in lines):
            raise CorpusError(
                "mandatory reading metadata or link exceeds 80 line/character bounds"
            )
        rows = [
            {**row, "reading_line": len(before) + len(heading) + offset + 1}
            for offset, (_, row) in enumerate(items)
            if row is not None
        ]
        rendered = "\n".join(lines) + "\n"
        result.append(
            {
                "role": role,
                "index": index,
                "total": len(parts),
                "path": path,
                "rendered_text": rendered,
                "rendered_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
                "rows": rows,
            }
        )
    return result


def build_contextual_readings(
    source: Source,
    cache_root: Path,
    *,
    start_line: int,
    end_line: int,
    rule_ids: Sequence[str],
    instructions: str,
    questions: str,
    reading_id: str,
    link_directory: Path,
    markdown_anchor_style: str | None = None,
    native_context: Any = None,
) -> dict[str, Any]:
    """Return linked readings with static evidence; never execute reviewed code.

    Callers persist the exact rendered texts at the returned absolute paths.
    Every page repeats the caller's review scope; context grants no coverage.
    """
    if source.split != "development" or source.format not in {"python", "markdown"}:
        raise CorpusError(
            "context requires a development raw Markdown or Python source"
        )
    if (
        isinstance(rule_ids, str)
        or not rule_ids
        or len(set(rule_ids)) != len(rule_ids)
        or any(
            not isinstance(rule, str) or re.fullmatch(r"[A-Z]\d{3}", rule) is None
            for rule in rule_ids
        )
    ):
        raise CorpusError("declare unique complete rule IDs")
    if (
        not isinstance(reading_id, str)
        or re.fullmatch(r"[A-Za-z0-9_-]{1,32}", reading_id) is None
    ):
        raise CorpusError("invalid reading ID")
    if not link_directory.is_absolute() or re.search(
        r"[\x00-\x1f<>]", str(link_directory)
    ):
        raise CorpusError("reading links require a plain absolute directory")
    before, after = (
        _caller_lines(instructions, "instructions"),
        _caller_lines(questions, "questions"),
    )
    raw = _checked_bytes(source, cache_root)
    text, physical = _physical(raw)
    region = _region(physical, start_line, end_line)
    context: dict[str, Any] = {
        "source_id": source.identity,
        "sha256": source.sha256,
        "split": source.split,
        "format": source.format,
        "source_group": source.source_group,
        "pair_group": source.pair_group,
        "region": region,
        "rule_ids": list(rule_ids),
        "reading_id": reading_id,
        "link_directory": str(link_directory),
        "instructions": instructions,
        "questions": questions,
        "python_owners": [],
        "markdown_documents": [],
    }
    sections = [
        (
            "focus",
            _source_items(
                physical, start_line, end_line, source.identity, source.sha256
            ),
        )
    ]
    if source.format == "python":
        owners = _python_owners(text, physical, start_line, end_line)
        context["python_owners"] = owners
        context["python_scope"] = "lexical-owners" if owners else "module"
        context["python_evidence"] = (
            "Raw headers only; module bindings and runtime behavior are not verified."
        )
        for owner in owners:
            header = owner["header_region"]
            sections.append(
                (
                    "python-owner",
                    _metadata_items(owner)
                    + _source_items(
                        physical,
                        header["line"],
                        header["end_line"],
                        source.identity,
                        source.sha256,
                    ),
                )
            )
        if not owners:
            sections.append(
                (
                    "python-owner",
                    _metadata_items({"python_scope": "module", "owners": []}),
                )
            )
    elif (
        {"M011", "M012"}.intersection(rule_ids)
        or markdown_anchor_style is not None
        or native_context is not None
    ):
        raise CorpusError("Markdown link context is not yet supported")
    context["section_roles"] = [role for role, _ in sections]
    readings = _pages(sections, context, before, after, reading_id, link_directory)
    bundle = {
        "version": 1,
        "context": context,
        "context_sha256": _digest(context),
        "readings": readings,
    }
    return {**bundle, "bundle_sha256": _digest(bundle)}
