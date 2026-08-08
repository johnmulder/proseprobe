"""Shared source-mapped prose blocks and parser dispatch."""

import re
from dataclasses import dataclass, field

InlineSuppression = tuple[int, int, str]


@dataclass(frozen=True)
class ProseBlock:
    """A source-mapped block of prose."""

    context: str
    start_line: int
    end_line: int
    lines: tuple[tuple[int, str], ...]
    break_before: bool = False


@dataclass(frozen=True)
class ProseSentence:
    """A sentence with exact positions in masked prose and original source."""

    context: str
    text: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    scope_id: int
    break_before: bool
    source_lines: tuple[int, ...] = field(repr=False)

    def source_position(self, offset: int = 0) -> tuple[int, int]:
        """Map a sentence-text offset to a one-based source position."""
        if offset < 0 or offset > len(self.text):
            raise ValueError("offset is outside sentence")
        prefix = self.text[:offset]
        line_index = prefix.count("\n")
        if line_index == 0:
            return self.start_line, self.start_column + offset
        return (
            self.source_lines[line_index],
            len(prefix.rsplit("\n", 1)[-1]) + 1,
        )

    def source_text(self, content: str) -> str:
        """Return the unmasked original source covered by this sentence."""
        source = content.split("\n")
        parts: list[str] = []
        for index, line_num in enumerate(self.source_lines):
            line = source[line_num - 1]
            start = self.start_column - 1 if index == 0 else 0
            end = (
                self.end_column - 1
                if index == len(self.source_lines) - 1
                else len(line)
            )
            parts.append(line[start:end])
        return "\n".join(parts)


_ABBREVIATIONS = frozenset(
    {
        "dr.",
        "e.g.",
        "eq.",
        "etc.",
        "fig.",
        "i.e.",
        "jr.",
        "mr.",
        "mrs.",
        "ms.",
        "no.",
        "prof.",
        "sr.",
        "st.",
        "vs.",
    }
)
_SENTENCE_BOUNDARY = re.compile(r"""[.!?]+["')\]\u201d\u2019]*(?=\s|$)""")
_INITIALISM = re.compile(r"(?:[A-Za-z]\.){2,}$")


def _protected_period(text: str, index: int) -> bool:
    if text[index] != ".":
        return False
    prefix = text[: index + 1]
    word = re.search(r"([A-Za-z][A-Za-z.]*)\.$", prefix)
    token = f"{word.group(1)}.".casefold() if word else ""
    return token in _ABBREVIATIONS or bool(_INITIALISM.search(prefix))


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_BOUNDARY.finditer(text):
        if _protected_period(text, match.start()):
            continue
        end = match.end()
        trimmed_start = start
        while trimmed_start < end and text[trimmed_start].isspace():
            trimmed_start += 1
        if trimmed_start < end:
            spans.append((trimmed_start, end))
        start = end
    while start < len(text) and text[start].isspace():
        start += 1
    end = len(text)
    while end > start and text[end - 1].isspace():
        end -= 1
    if start < end:
        spans.append((start, end))
    return spans


def _sentences_from_blocks(blocks: list[ProseBlock]) -> list[ProseSentence]:
    sentences: list[ProseSentence] = []
    scope_id = 0
    for block in blocks:
        chunks: list[list[tuple[int, str]]] = []
        current: list[tuple[int, str]] = []
        for line in block.lines:
            if line[1].strip():
                current.append(line)
            elif current:
                chunks.append(current)
                current = []
        if current:
            chunks.append(current)

        for chunk in chunks:
            joined = "\n".join(line for _, line in chunk)
            for sentence_index, (start, end) in enumerate(_sentence_spans(joined)):
                start_index = joined[:start].count("\n")
                end_index = joined[:end].count("\n")
                line_start = joined.rfind("\n", 0, start) + 1
                line_end = joined.rfind("\n", 0, end) + 1
                sentences.append(
                    ProseSentence(
                        context=block.context,
                        text=joined[start:end],
                        start_line=chunk[start_index][0],
                        start_column=start - line_start + 1,
                        end_line=chunk[end_index][0],
                        end_column=end - line_end + 1,
                        scope_id=scope_id,
                        break_before=bool(sentences) and sentence_index == 0,
                        source_lines=tuple(
                            line_num
                            for line_num, _ in chunk[start_index : end_index + 1]
                        ),
                    )
                )
            scope_id += 1
    return sentences


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
        from proseprobe.parsers.markdown import (
            _get_cached_parser as get_markdown_parser,
        )

        return get_markdown_parser(content).get_inline_suppressions()
    if filename.lower().endswith(".py"):
        from proseprobe.parsers.python import _get_cached_parser as get_python_parser

        return get_python_parser(content).get_inline_suppressions()
    return []


def iter_prose_lines(content: str, filename: str) -> list[tuple[int, str]]:
    """Return source-mapped prose lines for the input file type."""
    if filename.lower().endswith((".md", ".mdx", ".markdown")):
        from proseprobe.parsers.markdown import (
            _get_cached_parser as get_markdown_parser,
        )

        return get_markdown_parser(content).get_prose_lines()
    if filename.lower().endswith(".py"):
        from proseprobe.parsers.python import _get_cached_parser as get_python_parser

        return get_python_parser(content).get_prose_lines()
    return list(enumerate(content.split("\n"), start=1))


def iter_prose_blocks(content: str, filename: str) -> list[ProseBlock]:
    """Return source-mapped prose blocks for the input file type."""
    if filename.lower().endswith((".md", ".mdx", ".markdown")):
        from proseprobe.parsers.markdown import (
            _get_cached_parser as get_markdown_parser,
        )

        return get_markdown_parser(content).get_prose_blocks()
    if filename.lower().endswith(".py"):
        from proseprobe.parsers.python import _get_cached_parser as get_python_parser

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


def iter_prose_sentences(content: str, filename: str) -> list[ProseSentence]:
    """Return cached source-mapped prose sentences for supported file types."""
    if filename.lower().endswith((".md", ".mdx", ".markdown")):
        from proseprobe.parsers.markdown import (
            _get_cached_parser as get_markdown_parser,
        )

        return get_markdown_parser(content).get_prose_sentences()
    if filename.lower().endswith(".py"):
        from proseprobe.parsers.python import _get_cached_parser as get_python_parser

        return get_python_parser(content).get_prose_sentences()
    return _sentences_from_blocks(iter_prose_blocks(content, filename))


def iter_prose_scopes(content: str, filename: str) -> list[ProseBlock]:
    """Return independent scopes for document-level prose thresholds."""
    if filename.lower().endswith(".py"):
        return iter_prose_blocks(content, filename)

    lines = iter_prose_lines(content, filename)
    if not lines:
        return []
    return [ProseBlock("body", lines[0][0], lines[-1][0], tuple(lines))]
