"""Shared source-mapped prose blocks and parser dispatch."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProseBlock:
    """A source-mapped block of prose."""

    context: str
    start_line: int
    end_line: int
    lines: tuple[tuple[int, str], ...]
    break_before: bool = False


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
