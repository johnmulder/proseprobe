"""Shared source-mapped prose blocks and parser dispatch."""

import re
from dataclasses import dataclass

InlineSuppression = tuple[int, int, str]


@dataclass(frozen=True)
class ProseBlock:
    """A source-mapped block of prose."""

    context: str
    start_line: int
    end_line: int
    lines: tuple[tuple[int, str], ...]
    break_before: bool = False


def _validate_suppression_tokens(raw: str, line: int) -> str:
    """Return a trimmed token list or reject malformed directive syntax."""
    raw = raw.strip()
    tokens = raw.split(",")
    if not raw or any(
        not token.strip() or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", token.strip())
        for token in tokens
    ):
        raise ValueError(f"line {line}: malformed inline suppression")
    return raw


def iter_inline_suppressions(content: str, filename: str) -> list[InlineSuppression]:
    """Return source-mapped inline suppressions for a supported file type."""
    if filename.lower().endswith((".md", ".mdx", ".markdown")):
        from slop_lint.parsers.markdown import (
            _get_cached_parser as get_markdown_parser,
        )

        return get_markdown_parser(content).get_inline_suppressions()
    if filename.lower().endswith(".py"):
        from slop_lint.parsers.python import _get_cached_parser as get_python_parser

        return get_python_parser(content).get_inline_suppressions()
    return []


def iter_prose_lines(content: str, filename: str) -> list[tuple[int, str]]:
    """Return source-mapped prose lines for the input file type."""
    if filename.lower().endswith((".md", ".mdx", ".markdown")):
        from slop_lint.parsers.markdown import (
            _get_cached_parser as get_markdown_parser,
        )

        return get_markdown_parser(content).get_prose_lines()
    if filename.lower().endswith(".py"):
        from slop_lint.parsers.python import _get_cached_parser as get_python_parser

        return get_python_parser(content).get_prose_lines()
    return list(enumerate(content.split("\n"), start=1))


def iter_prose_blocks(content: str, filename: str) -> list[ProseBlock]:
    """Return source-mapped prose blocks for the input file type."""
    if filename.lower().endswith((".md", ".mdx", ".markdown")):
        from slop_lint.parsers.markdown import (
            _get_cached_parser as get_markdown_parser,
        )

        return get_markdown_parser(content).get_prose_blocks()
    if filename.lower().endswith(".py"):
        from slop_lint.parsers.python import _get_cached_parser as get_python_parser

        return get_python_parser(content).get_prose_blocks()

    blocks: list[ProseBlock] = []
    current: list[tuple[int, str]] = []
    for line_num, line in enumerate(content.split("\n"), start=1):
        if line.strip():
            current.append((line_num, line))
        elif current:
            blocks.append(
                ProseBlock("body", current[0][0], current[-1][0], tuple(current))
            )
            current = []
    if current:
        blocks.append(ProseBlock("body", current[0][0], current[-1][0], tuple(current)))
    return blocks


def iter_prose_scopes(content: str, filename: str) -> list[ProseBlock]:
    """Return independent scopes for document-level prose thresholds."""
    if filename.lower().endswith(".py"):
        return iter_prose_blocks(content, filename)

    lines = iter_prose_lines(content, filename)
    if not lines:
        return []
    return [ProseBlock("body", lines[0][0], lines[-1][0], tuple(lines))]
