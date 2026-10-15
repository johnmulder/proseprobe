"""Attach static source context to finite, linked diagnostic readings."""

from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import tokenize
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from benchmarks.corpora import CorpusError, Source, _checked_bytes
from benchmarks.native_link_context import NativeSource, NativeTarget
from benchmarks.native_reference_context import VerifiedReferenceContext
from benchmarks.review_readings import (
    _caller_lines,
    _display_chunks,
    _line_parts,
    _source_rows,
)
from proseprobe.parsers.markdown import MarkdownParser
from proseprobe.parsers.python import PythonParser
from proseprobe.rules.markup import SameDocumentFragmentRule


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
        scope_end = node.end_lineno or node.lineno
        trailing_comments = []
        owner_indent = len(physical[line - 1][0][: column - 1].expandtabs(8))
        if first_body[0] > colon.end[0]:
            for token in tokens:
                if token.start[0] <= scope_end:
                    continue
                if token.type == tokenize.COMMENT:
                    comment_indent = len(
                        physical[token.start[0] - 1][0][: token.start[1]].expandtabs(8)
                    )
                    if comment_indent > owner_indent:
                        trailing_comments.append(token.start[0])
                elif token.type not in {tokenize.NL, tokenize.NEWLINE}:
                    break
        if scope_end < start and not any(
            start <= line <= end for line in trailing_comments
        ):
            continue
        owners.append(
            {
                "name": node.name,
                "node_type": "class" if isinstance(node, ast.ClassDef) else "function",
                "header_region": _region(physical, header_start, colon.end[0]),
                "scope_region": {
                    "line": node.lineno,
                    "end_line": max([scope_end, *trailing_comments]),
                },
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
    return [(chunk, None) for chunk in _display_chunks(text, 75)]


def _markdown_document(
    raw: bytes, identity: str, role: str
) -> tuple[dict[str, Any], list[tuple[str, list[tuple[str, dict[str, Any] | None]]]]]:
    text, physical = _physical(raw)
    parsed = text.replace("\r\n", "\n")
    document = SameDocumentFragmentRule._document(parsed)
    if document is None:
        raise CorpusError("generated or unsupported Markdown inventory context")
    checksum = hashlib.sha256(raw).hexdigest()
    inventory = {
        "role": role,
        "source_id": identity,
        "sha256": checksum,
        "status": "supported",
        "scope": "complete supported static headings and anchor-ID membership",
        "renderer": "github",
        "headings": [
            {
                "title": heading.title,
                "line": heading.start_line,
                "column": heading.column,
                "end_column": heading.end_column,
                "level": heading.level,
            }
            for heading in MarkdownParser(parsed).get_headings()
        ],
        "anchors": sorted(document[0]),
    }
    body = (
        _source_items(physical, 1, len(physical), identity, checksum)
        if physical
        else _metadata_items(
            {"source_id": identity, "sha256": checksum, "empty_document": True}
        )
    )
    return inventory, [
        (f"markdown-{role}", body),
        ("markdown-inventory", _metadata_items(inventory)),
    ]


def _native_targets(
    source: Source, raw: bytes, verified: VerifiedReferenceContext
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[tuple[str, list[tuple[str, dict[str, Any] | None]]]],
]:
    # This internal boundary accepts only immutable objects returned by the
    # offline reference validator. It does not authenticate arbitrary objects.
    if not isinstance(verified, VerifiedReferenceContext):
        raise CorpusError("local target context requires verified native references")
    native = verified.native
    originals = [item for item in native.sources if item.source_id == source.identity]
    if (
        len(originals) != 1
        or originals[0].raw != raw
        or native.source_group != source.source_group
    ):
        raise CorpusError("native source identity, group or bytes differ")
    if verified.renderer != "github":
        raise CorpusError("native renderer differs from selected GitHub anchor style")
    reference_map = dict(verified.references)
    if (
        len(reference_map) != len(verified.references)
        or source.identity not in reference_map
    ):
        raise CorpusError("native source reference map unavailable or duplicated")
    references = sorted(
        reference_map[source.identity],
        key=lambda item: (
            item.line,
            item.column,
            item.end_column,
            item.destination,
            item.native_path,
            item.fragment,
        ),
    )
    bound: dict[str, bytes | None] = {}
    items: tuple[NativeSource | NativeTarget, ...] = (*native.sources, *native.targets)
    for item in items:
        if item.native_path in bound and bound[item.native_path] != item.raw:
            raise CorpusError("conflicting bytes for duplicate native path")
        bound[item.native_path] = item.raw
    documents = []
    sections = []
    targets = []
    for path in sorted({item.native_path for item in references}):
        if path not in bound:
            raise CorpusError("required native target is not bound")
        target = bound[path]
        if target is None:
            targets.append({"native_path": path, "status": "absent"})
        else:
            targets.append(
                {
                    "native_path": path,
                    "status": "present",
                    "sha256": hashlib.sha256(target).hexdigest(),
                }
            )
            document, pieces = _markdown_document(target, path, "target")
            documents.append(document)
            sections.extend(pieces)
    proof = {
        "manifest_sha256": native.manifest_sha256,
        "source_group": native.source_group,
        "revision": native.revision,
        "inventory_sha256": native.inventory_sha256,
        "source_native_path": originals[0].native_path,
        "references": {source.identity: [asdict(item) for item in references]},
        "targets": targets,
        "absence_scope": "pinned inventory from the offline reference validator",
    }
    return proof, documents, [("native-context", _metadata_items(proof)), *sections]


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
    native_context: VerifiedReferenceContext | None = None,
) -> dict[str, Any]:
    """Return linked readings with static evidence; never execute reviewed code.

    Callers persist the exact rendered texts at the returned absolute paths.
    Every page repeats the caller's review scope; context grants no coverage.
    M012 requires the existing offline validator's immutable reference context;
    target paths are never reopened or resolved here. Arbitrary caller-created
    context objects do not constitute an absence proof.
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
    if (
        not link_directory.is_absolute()
        or str(link_directory).startswith("//")
        or re.search(r"[\x00-\x1f\x7f-\x9f\u2028\u2029<>#?%&\\]", str(link_directory))
    ):
        raise CorpusError("reading links require a plain absolute directory")
    if source.format == "python" and (
        {"M011", "M012"}.intersection(rule_ids)
        or markdown_anchor_style is not None
        or native_context is not None
    ):
        raise CorpusError("Markdown context cannot be supplied for Python source")
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
        if markdown_anchor_style != "github":
            raise CorpusError(
                "Markdown inventory requires explicit GitHub anchor renderer"
            )
        document, pieces = _markdown_document(raw, source.identity, "source")
        context["markdown_documents"].append(document)
        context["markdown_anchor_style"] = markdown_anchor_style
        sections.extend(pieces)
        if "M012" in rule_ids and native_context is None:
            raise CorpusError("M012 requires verified native target context")
        if native_context is not None:
            proof, documents, pieces = _native_targets(source, raw, native_context)
            context["native"] = proof
            context["markdown_documents"].extend(documents)
            sections.extend(pieces)
    context["section_roles"] = [role for role, _ in sections]
    readings = _pages(sections, context, before, after, reading_id, link_directory)
    bundle = {
        "version": 1,
        "context": context,
        "context_sha256": _digest(context),
        "readings": readings,
    }
    return {**bundle, "bundle_sha256": _digest(bundle)}
