"""Prepare bounded source readings without inferring human review coverage."""

import hashlib
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from benchmarks.corpora import CorpusError, Source, _checked_bytes


def _caller_lines(text: str, name: str) -> list[str]:
    if not isinstance(text, str):
        raise CorpusError(f"{name} must be text")
    lines = text.splitlines()
    if any(len(line) > 80 for line in lines):
        raise CorpusError(f"{name} exceeds 80 characters on one line")
    return lines


def _line_parts(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line and line[-1] in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029":
        return line[:-1], line[-1]
    return line, ""


def _display_chunks(body: str, width: int) -> list[str]:
    chunks = []
    offset = 0
    while offset < len(body):
        end = min(offset + width, len(body))
        if end < len(body):
            separator = max(body.rfind(" ", offset, end), body.rfind("\t", offset, end))
            if separator >= offset and body[offset:separator].strip(" \t"):
                end = separator + 1
        chunks.append(body[offset:end])
        offset = end
    return chunks or [""]


def _source_rows(
    physical: list[tuple[str, str]], start_line: int, end_line: int
) -> tuple[list[str], list[dict[str, Any]]]:
    """Render exact source chunks before their reading positions are assigned."""
    selected = physical[start_line - 1 : end_line]
    line_digits = len(str(end_line))
    column_digits = len(str(max(len(body) + 1 for body, _ending in selected)))
    rows: list[dict[str, Any]] = []
    displayed: list[str] = []
    for number, (body, ending) in enumerate(selected, start=start_line):
        prefix_width = line_digits + column_digits * 2 + 7
        width = 80 - prefix_width
        if width < 1:
            raise CorpusError("source coordinate labels exceed 80 characters")
        chunks = _display_chunks(body, width)
        column = 1
        for index, chunk in enumerate(chunks):
            end_column = column + len(chunk)
            prefix = (
                f"L{number:>{line_digits}} "
                f"C{column:>{column_digits}}-{end_column:>{column_digits}} | "
            )
            displayed.append(prefix + chunk)
            rows.append(
                {
                    "line": number,
                    "column": column,
                    "end_line": number,
                    "end_column": end_column,
                    "text": chunk,
                    "source_line_ending": ending if index == len(chunks) - 1 else "",
                }
            )
            column = end_column
    return displayed, rows


def build_reading(
    source: Source,
    cache_root: Path,
    *,
    start_line: int,
    end_line: int,
    rule_ids: Sequence[str],
    instructions: str,
    questions: str,
) -> dict[str, Any]:
    """Render selected full lines and record presentation-only continuations.

    Width counts Unicode code points. The row map retains literal chunks and
    original line endings; display separators do not change the bound source.
    This helper creates no issue annotations or declarations of clean coverage.
    """
    if source.split != "development":
        raise CorpusError("blind readings require a development source")
    if source.format not in {"markdown", "python"}:
        raise CorpusError("blind readings require raw Markdown or Python sources")
    if (
        isinstance(rule_ids, str)
        or not rule_ids
        or any(
            not isinstance(rule, str) or re.fullmatch(r"[A-Z]\d{3}", rule) is None
            for rule in rule_ids
        )
        or len(set(rule_ids)) != len(rule_ids)
    ):
        raise CorpusError("declare unique, nonempty, complete rule IDs")
    before = _caller_lines(instructions, "instructions")
    after = _caller_lines(questions, "questions")
    try:
        text = _checked_bytes(source, cache_root).decode("utf-8")
    except UnicodeDecodeError as error:
        raise CorpusError("source must be UTF-8") from error
    physical = [_line_parts(line) for line in text.splitlines(keepends=True)]
    if (
        type(start_line) is not int
        or type(end_line) is not int
        or not 1 <= start_line <= end_line <= len(physical)
    ):
        raise CorpusError("invalid source line region")
    selected = physical[start_line - 1 : end_line]
    displayed, rows = _source_rows(physical, start_line, end_line)
    fence_length = max(
        (
            len(match.group()) + 1
            for line in displayed
            for match in re.finditer(r"`+", line)
        ),
        default=3,
    )
    fence = "`" * max(3, fence_length)
    heading = [
        "Rules: " + ", ".join(rule_ids),
        "Rows are display chunks; L/C ranges refer to original code points.",
        "Character endpoints are exclusive; original line endings are mapped.",
        "",
        fence + "text",
    ]
    first_source_row = len(before) + len(heading) + 1
    for index, row in enumerate(rows):
        row["reading_line"] = first_source_row + index
    output = before + heading + displayed + [fence, ""] + after
    if len(output) > 80:
        raise CorpusError("complete reading exceeds 80 lines; choose a smaller region")
    if any(len(line) > 80 for line in output):
        raise CorpusError("complete reading exceeds 80 characters on one line")
    rendered = "\n".join(output) + "\n"
    return {
        "version": 1,
        "source_id": source.identity,
        "sha256": source.sha256,
        "source_group": source.source_group,
        "pair_group": source.pair_group,
        "split": source.split,
        "format": source.format,
        "region": {
            "line": start_line,
            "column": 1,
            "end_line": end_line,
            "end_column": len(selected[-1][0]) + 1,
        },
        "rule_ids": list(rule_ids),
        "rendered_text": rendered,
        "rendered_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "rows": rows,
    }
