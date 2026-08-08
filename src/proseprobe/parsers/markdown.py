"""Markdown parser for extracting structured content."""

import re
from dataclasses import dataclass

from proseprobe.parsers.prose import (
    InlineSuppression,
    ProseBlock,
    ProseSentence,
    _sentences_from_blocks,
    _validate_suppression_tokens,
)

MARKDOWN_EXTENSIONS = (".md", ".mdx", ".markdown")

# Cache for MarkdownParser instances (keyed by content hash)
_parser_cache: dict[int, "MarkdownParser"] = {}
_CACHE_MAX_SIZE = 32


def _get_cached_parser(content: str) -> "MarkdownParser":
    """Get or create a cached MarkdownParser for content.

    Uses content hash as key to avoid redundant parsing for the same content.
    """
    content_hash = hash(content)
    if content_hash in _parser_cache:
        return _parser_cache[content_hash]

    # Evict oldest entries if cache is full
    if len(_parser_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_parser_cache))
        del _parser_cache[oldest_key]

    parser = MarkdownParser(content)
    _parser_cache[content_hash] = parser
    return parser


def clear_parser_cache() -> None:
    """Clear the parser cache. Useful for testing."""
    _parser_cache.clear()


def is_markdown_file(filename: str) -> bool:
    """Return True if filename looks like Markdown."""
    return filename.lower().endswith(MARKDOWN_EXTENSIONS)


@dataclass
class MarkdownSection:
    """A section of a Markdown document."""

    level: int
    title: str
    content: str
    start_line: int
    end_line: int
    column: int
    end_column: int


@dataclass
class MarkdownLink:
    """A link in a Markdown document."""

    text: str
    url: str
    line: int
    column: int
    url_start: int = 0
    url_end: int = 0


@dataclass(frozen=True)
class MarkdownReference:
    """A Markdown reference definition or use with source positions."""

    label: str
    text: str
    destination: str | None
    line: int
    column: int
    end_column: int
    is_definition: bool
    destination_start: int = 0
    destination_end: int = 0


@dataclass(frozen=True)
class MarkdownCodeBlock:
    """A fenced Markdown code block with its opening source span."""

    start_line: int
    end_line: int
    language: str
    content: str
    fence: str
    column: int
    closed: bool


MarkdownProseBlock = ProseBlock


class MarkdownParser:
    """Parser for Markdown documents.

    Extracts structural information for rule checking.
    """

    def __init__(self, content: str) -> None:
        """Initialize parser with content.

        Args:
            content: Markdown document content.
        """
        self.content = content
        self._lines = content.split("\n")
        self._code_blocks: list[MarkdownCodeBlock] | None = None
        self._code_block_lines: set[int] | None = None
        self._setext_heading_lines: set[int] | None = None
        self._setext_underline_lines: set[int] | None = None
        self._html_block_lines: set[int] | None = None
        self._prose_blocks: list[MarkdownProseBlock] | None = None
        self._prose_sentences: list[ProseSentence] | None = None
        self._inline_suppressions: list[InlineSuppression] | None = None
        self._references: list[MarkdownReference] | None = None
        self._blockquote_re = re.compile(r"^(?:\s{0,3}>\s?)+")
        self._html_block_tags = {
            "div",
            "section",
            "article",
            "aside",
            "nav",
            "header",
            "footer",
            "table",
            "thead",
            "tbody",
            "tr",
            "td",
            "th",
            "pre",
            "code",
            "script",
            "style",
            "textarea",
            "details",
            "summary",
            "figure",
            "figcaption",
        }

    def _ensure_code_blocks(self) -> None:
        if self._code_blocks is not None and self._code_block_lines is not None:
            return

        blocks: list[MarkdownCodeBlock] = []
        code_lines: set[int] = set()

        in_block = False
        fence_char = ""
        fence_len = 0
        opening_fence = ""
        opening_column = 0
        blockquoted_fence = False
        language = ""
        start_line = 0
        content_lines: list[str] = []

        fence_re = re.compile(r"^( {0,3})(`{3,}|~{3,})\s*([\w+-]+)?\s*$")

        for line_num, line in enumerate(self._lines, start=1):
            fence_line, blockquote_prefix_length = self._strip_blockquote_prefix(line)
            if not in_block:
                match = fence_re.match(fence_line)
                if match:
                    opening_fence = match.group(2)
                    fence_char = opening_fence[0]
                    fence_len = len(opening_fence)
                    opening_column = blockquote_prefix_length + match.start(2) + 1
                    blockquoted_fence = blockquote_prefix_length > 0
                    language = match.group(3) or ""
                    start_line = line_num
                    content_lines = []
                    in_block = True
                    code_lines.add(line_num)
                continue

            code_lines.add(line_num)
            active_line = fence_line if blockquoted_fence else line
            close_re = re.compile(
                rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_len},}}\s*$"
            )
            if close_re.match(active_line):
                blocks.append(
                    MarkdownCodeBlock(
                        start_line=start_line,
                        end_line=line_num,
                        language=language,
                        content="\n".join(content_lines),
                        fence=opening_fence,
                        column=opening_column,
                        closed=True,
                    )
                )
                in_block = False
            else:
                content_lines.append(active_line)

        if in_block:
            blocks.append(
                MarkdownCodeBlock(
                    start_line=start_line,
                    end_line=len(self._lines),
                    language=language,
                    content="\n".join(content_lines),
                    fence=opening_fence,
                    column=opening_column,
                    closed=False,
                )
            )

        self._code_blocks = blocks
        self._code_block_lines = code_lines

    def _code_lines(self) -> set[int]:
        self._ensure_code_blocks()
        return self._code_block_lines or set()

    def _ensure_html_blocks(self) -> None:
        if self._html_block_lines is not None:
            return

        self._ensure_code_blocks()
        code_lines = self._code_lines()
        html_lines: set[int] = set()

        comment_start_re = re.compile(r"^\s*<!--")
        comment_end_re = re.compile(r".*-->\s*$")
        tag_start_re = re.compile(r"^\s*<([a-zA-Z][\w:-]*)\b[^>]*>\s*$")
        tag_end_template = r"^\s*</{tag}>\s*$"

        in_comment = False
        open_tag: str | None = None

        for line_num, line in enumerate(self._lines, start=1):
            if line_num in code_lines:
                continue

            if in_comment:
                html_lines.add(line_num)
                if comment_end_re.match(line):
                    in_comment = False
                continue

            if comment_start_re.match(line):
                html_lines.add(line_num)
                if not comment_end_re.match(line):
                    in_comment = True
                continue

            if open_tag:
                html_lines.add(line_num)
                end_re = re.compile(tag_end_template.format(tag=re.escape(open_tag)))
                if end_re.match(line):
                    open_tag = None
                continue

            start_match = tag_start_re.match(line)
            if start_match:
                tag = start_match.group(1).lower()
                if tag in self._html_block_tags:
                    html_lines.add(line_num)
                    if line.strip().endswith("/>"):
                        continue
                    end_re = re.compile(tag_end_template.format(tag=re.escape(tag)))
                    if end_re.match(line):
                        continue
                    open_tag = tag

        self._html_block_lines = html_lines

    def _html_lines(self) -> set[int]:
        self._ensure_html_blocks()
        return self._html_block_lines or set()

    def _ensure_setext_headings(self) -> None:
        if (
            self._setext_heading_lines is not None
            and self._setext_underline_lines is not None
        ):
            return

        self._ensure_code_blocks()
        code_lines = self._code_lines()
        heading_lines: set[int] = set()
        underline_lines: set[int] = set()
        setext_re = re.compile(r"^ {0,3}(=+|-+)\s*$")

        for idx in range(len(self._lines) - 1):
            line_num = idx + 1
            next_line_num = idx + 2
            if line_num in code_lines or next_line_num in code_lines:
                continue
            line_text, _ = self._strip_blockquote_prefix(self._lines[idx])
            next_text, _ = self._strip_blockquote_prefix(self._lines[idx + 1])
            if not line_text.strip():
                continue
            if setext_re.match(next_text):
                heading_lines.add(line_num)
                underline_lines.add(next_line_num)

        self._setext_heading_lines = heading_lines
        self._setext_underline_lines = underline_lines

    def _setext_lines(self) -> tuple[set[int], set[int]]:
        self._ensure_setext_headings()
        return (
            self._setext_heading_lines or set(),
            self._setext_underline_lines or set(),
        )

    def get_headings(self) -> list[MarkdownSection]:
        """Extract all headings from the document.

        Returns:
            List of heading sections.
        """
        self._ensure_code_blocks()
        code_lines = self._code_lines()
        html_lines = self._html_lines()
        headings: list[tuple[int, int, str, int, int]] = []
        heading_re = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*$")
        setext_re = re.compile(r"^ {0,3}(=+|-+)\s*$")
        idx = 0
        while idx < len(self._lines):
            line_num = idx + 1
            if line_num in code_lines or line_num in html_lines:
                idx += 1
                continue
            raw_line = self._lines[idx]
            stripped_line, prefix_len = self._strip_blockquote_prefix(raw_line)
            match = heading_re.match(stripped_line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                title = re.sub(r"\s+#+\s*$", "", title).strip()
                column = prefix_len + match.start(2) + 1
                headings.append((line_num, level, title, column, column + len(title)))
                idx += 1
                continue

            if idx + 1 < len(self._lines):
                next_line_num = idx + 2
                if next_line_num not in code_lines and next_line_num not in html_lines:
                    next_stripped, _ = self._strip_blockquote_prefix(
                        self._lines[idx + 1]
                    )
                    setext_match = setext_re.match(next_stripped)
                    if setext_match and stripped_line.strip():
                        level = 1 if setext_match.group(1).startswith("=") else 2
                        title = stripped_line.strip()
                        leading = len(stripped_line) - len(stripped_line.lstrip())
                        column = prefix_len + leading + 1
                        headings.append(
                            (line_num, level, title, column, column + len(title))
                        )
                        idx += 2
                        continue

            idx += 1

        sections: list[MarkdownSection] = []
        for idx, (line_num, level, title, column, end_column) in enumerate(headings):
            next_line = headings[idx + 1][0] if idx + 1 < len(headings) else None
            end_line = (next_line - 1) if next_line else len(self._lines)
            content_lines: list[str] = []
            for content_line in range(line_num + 1, end_line + 1):
                if content_line in code_lines:
                    continue
                content_lines.append(self._lines[content_line - 1])
            sections.append(
                MarkdownSection(
                    level=level,
                    title=title,
                    content="\n".join(content_lines).rstrip(),
                    start_line=line_num,
                    end_line=end_line,
                    column=column,
                    end_column=end_column,
                )
            )

        return sections

    def get_paragraphs(self) -> list[tuple[int, int, str]]:
        """Extract all paragraphs with line numbers.

        Returns:
            List of (start_line, end_line, text) tuples.
        """
        self._ensure_code_blocks()
        code_lines = self._code_lines()
        html_lines = self._html_lines()
        setext_headings, setext_underline = self._setext_lines()
        paragraphs: list[tuple[int, int, str]] = []
        heading_re = re.compile(r"^ {0,3}(#{1,6})\s+")
        list_re = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")

        current_lines: list[str] = []
        start_line = 0

        def flush(end_line: int) -> None:
            nonlocal current_lines, start_line
            if current_lines:
                paragraphs.append(
                    (start_line, end_line, "\n".join(current_lines).rstrip())
                )
                current_lines = []
                start_line = 0

        for line_num, line in enumerate(self._lines, start=1):
            if line_num in code_lines or line_num in html_lines:
                flush(line_num - 1)
                continue
            stripped_line, _ = self._strip_blockquote_prefix(line)
            if line_num in setext_headings or line_num in setext_underline:
                flush(line_num - 1)
                continue
            if heading_re.match(stripped_line) or list_re.match(stripped_line):
                flush(line_num - 1)
                continue
            if not stripped_line.strip():
                flush(line_num - 1)
                continue

            if not current_lines:
                start_line = line_num
            current_lines.append(stripped_line)

        flush(len(self._lines))
        return paragraphs

    @staticmethod
    def _normalize_reference_label(label: str) -> str:
        """Normalize a reference label for CommonMark-style matching."""
        unescaped: list[str] = []
        index = 0
        while index < len(label):
            if (
                label[index] == "\\"
                and index + 1 < len(label)
                and label[index + 1] in "[]"
            ):
                unescaped.append(label[index + 1])
                index += 2
                continue
            unescaped.append(label[index])
            index += 1
        return " ".join("".join(unescaped).split()).casefold()

    @classmethod
    def _parse_reference_label(
        cls,
        line: str,
        start: int,
        *,
        allow_empty: bool = False,
    ) -> tuple[str, int] | None:
        """Return raw label text and its closing-bracket index."""
        if start >= len(line) or line[start] != "[":
            return None
        index = start + 1
        chars: list[str] = []
        while index < len(line):
            char = line[index]
            if char == "\\" and index + 1 < len(line):
                chars.extend((char, line[index + 1]))
                index += 2
                continue
            if char == "[":
                return None
            if char == "]":
                raw = "".join(chars)
                if allow_empty or cls._normalize_reference_label(raw):
                    return raw, index
                return None
            chars.append(char)
            index += 1
        return None

    @classmethod
    def _reference_definition(
        cls,
        line: str,
        line_num: int,
        prefix_len: int,
    ) -> MarkdownReference | None:
        """Parse one single-line reference definition."""
        start = len(line) - len(line.lstrip())
        parsed = cls._parse_reference_label(line, start)
        if parsed is None:
            return None
        text, closing = parsed
        after_label = closing + 1
        if after_label >= len(line) or line[after_label] != ":":
            return None
        destination_match = re.match(r"\s*(\S*)", line[after_label + 1 :])
        if destination_match is None:
            return None
        label = cls._normalize_reference_label(text)
        if label.startswith("^"):
            return None
        destination = destination_match.group(1)
        destination_start = (
            after_label + 1 + destination_match.start(1) + 1 + prefix_len
        )
        destination_end = after_label + 1 + destination_match.end(1) + 1 + prefix_len
        return MarkdownReference(
            label=label,
            text=text,
            destination=destination,
            line=line_num,
            column=start + 1 + prefix_len,
            end_column=closing + 2 + prefix_len,
            is_definition=True,
            destination_start=destination_start,
            destination_end=destination_end,
        )

    def get_references(self) -> list[MarkdownReference]:
        """Extract reference definitions and unambiguous reference uses."""
        if self._references is not None:
            return self._references

        self._ensure_code_blocks()
        code_lines = self._code_lines()
        html_lines = self._html_lines()
        definitions: list[MarkdownReference] = []
        definition_lines: set[int] = set()

        for line_num, line in enumerate(self._lines, start=1):
            if line_num in code_lines or line_num in html_lines:
                continue
            stripped_line, prefix_len = self._strip_blockquote_prefix(line)
            definition = self._reference_definition(
                stripped_line,
                line_num,
                prefix_len,
            )
            if definition is not None:
                definitions.append(definition)
                definition_lines.add(line_num)

        defined_labels = {definition.label for definition in definitions}
        uses: list[MarkdownReference] = []

        for line_num, line in enumerate(self._lines, start=1):
            if (
                line_num in code_lines
                or line_num in html_lines
                or line_num in definition_lines
            ):
                continue
            stripped_line, prefix_len = self._strip_blockquote_prefix(line)
            masked = self._mask_inline_code(stripped_line)
            index = 0
            while index < len(masked):
                if masked[index] != "[" or (index > 0 and masked[index - 1] == "\\"):
                    index += 1
                    continue
                first = self._parse_reference_label(masked, index)
                if first is None:
                    index += 1
                    continue
                text, first_closing = first
                after_first = first_closing + 1
                if after_first < len(masked) and masked[after_first] == "(":
                    inline_end = masked.find(")", after_first + 1)
                    index = inline_end + 1 if inline_end >= 0 else after_first + 1
                    continue

                source_start = (
                    index - 1 if index > 0 and masked[index - 1] == "!" else index
                )
                label = self._normalize_reference_label(text)
                end = first_closing
                if after_first < len(masked) and masked[after_first] == "[":
                    second = self._parse_reference_label(
                        masked,
                        after_first,
                        allow_empty=True,
                    )
                    if second is None:
                        index = after_first + 1
                        continue
                    explicit_label, end = second
                    label = self._normalize_reference_label(explicit_label or text)
                elif label not in defined_labels:
                    index = first_closing + 1
                    continue

                if label and not label.startswith("^"):
                    uses.append(
                        MarkdownReference(
                            label=label,
                            text=text,
                            destination=None,
                            line=line_num,
                            column=source_start + 1 + prefix_len,
                            end_column=end + 2 + prefix_len,
                            is_definition=False,
                        )
                    )
                index = end + 1

        self._references = sorted(
            [*definitions, *uses],
            key=lambda reference: (reference.line, reference.column),
        )
        return self._references

    def get_links(self) -> list[MarkdownLink]:
        """Extract all links from the document.

        Returns:
            List of links with positions.
        """
        self._ensure_code_blocks()
        code_lines = self._code_lines()
        html_lines = self._html_lines()
        links: list[MarkdownLink] = []
        link_re = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")
        autolink_re = re.compile(r"<(https?://[^>\s]+)>")
        references = self.get_references()
        reference_defs: dict[str, MarkdownReference] = {}
        uses_by_line: dict[int, list[MarkdownReference]] = {}
        used_refs: set[str] = set()

        for reference in references:
            if reference.is_definition:
                reference_defs.setdefault(reference.label, reference)
            else:
                uses_by_line.setdefault(reference.line, []).append(reference)

        for line_num, line in enumerate(self._lines, start=1):
            if line_num in code_lines or line_num in html_lines:
                continue
            stripped_line, prefix_len = self._strip_blockquote_prefix(line)
            masked = self._mask_inline_code(stripped_line)
            for match in link_re.finditer(masked):
                links.append(
                    MarkdownLink(
                        text=match.group(1),
                        url=match.group(2),
                        line=line_num,
                        column=match.start() + 1 + prefix_len,
                        url_start=match.start(2) + 1 + prefix_len,
                        url_end=match.end(2) + 1 + prefix_len,
                    )
                )
            for reference in uses_by_line.get(line_num, []):
                definition = reference_defs.get(reference.label)
                if definition is None or definition.destination is None:
                    continue
                used_refs.add(reference.label)
                links.append(
                    MarkdownLink(
                        text=reference.text,
                        url=definition.destination,
                        line=line_num,
                        column=reference.column,
                    )
                )
            for match in autolink_re.finditer(masked):
                links.append(
                    MarkdownLink(
                        text=match.group(1),
                        url=match.group(1),
                        line=line_num,
                        column=match.start() + 1 + prefix_len,
                        url_start=match.start(1) + 1 + prefix_len,
                        url_end=match.end(1) + 1 + prefix_len,
                    )
                )

        for label, definition in reference_defs.items():
            if label in used_refs or definition.destination is None:
                continue
            links.append(
                MarkdownLink(
                    text=definition.text,
                    url=definition.destination,
                    line=definition.line,
                    column=definition.destination_start,
                    url_start=definition.destination_start,
                    url_end=definition.destination_end,
                )
            )

        return links

    def get_code_block_records(self) -> list[MarkdownCodeBlock]:
        """Return fenced code blocks with source and closure metadata."""
        self._ensure_code_blocks()
        return list(self._code_blocks or [])

    def get_code_blocks(self) -> list[tuple[int, int, str, str]]:
        """Extract fenced code blocks as backward-compatible tuples."""
        return [
            (block.start_line, block.end_line, block.language, block.content)
            for block in self.get_code_block_records()
        ]

    def get_bullet_lists(self) -> list[tuple[int, int, list[str]]]:
        """Extract bullet lists.

        Returns:
            List of (start_line, end_line, items) tuples.
        """
        self._ensure_code_blocks()
        code_lines = self._code_lines()
        html_lines = self._html_lines()
        list_re = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*)")
        lists: list[tuple[int, int, list[str]]] = []

        current_items: list[str] = []
        start_line = 0

        def flush(end_line: int) -> None:
            nonlocal current_items, start_line
            if current_items:
                lists.append((start_line, end_line, current_items))
                current_items = []
                start_line = 0

        for line_num, line in enumerate(self._lines, start=1):
            if line_num in code_lines or line_num in html_lines:
                flush(line_num - 1)
                continue
            stripped_line, _ = self._strip_blockquote_prefix(line)
            match = list_re.match(stripped_line)
            if match:
                if not current_items:
                    start_line = line_num
                current_items.append(match.group(1).strip())
                continue

            flush(line_num - 1)

        flush(len(self._lines))
        return lists

    def get_lines(self) -> list[tuple[int, str]]:
        """Return non-code lines with line numbers."""
        self._ensure_code_blocks()
        code_lines = self._code_lines()
        html_lines = self._html_lines()
        return [
            (line_num, line)
            for line_num, line in enumerate(self._lines, start=1)
            if line_num not in code_lines and line_num not in html_lines
        ]

    def get_inline_suppressions(self) -> list[InlineSuppression]:
        """Return standalone directives and their next-line targets."""
        if self._inline_suppressions is not None:
            return self._inline_suppressions

        directive_re = re.compile(
            r"^\s*<!--\s*proseprobe-ignore-next-line(?:\s+(.*?))?\s*-->\s*$",
            re.IGNORECASE,
        )
        suppressions: list[InlineSuppression] = []
        code_lines = self._code_lines()
        for line_num, line in enumerate(self._lines, start=1):
            if line_num in code_lines:
                continue
            stripped = line.strip()
            if not stripped.lower().startswith("<!--") or (
                "proseprobe-ignore-next-line" not in stripped.lower()
            ):
                continue
            match = directive_re.fullmatch(line)
            if match is None:
                raise ValueError(f"line {line_num}: malformed inline suppression")
            raw = _validate_suppression_tokens(match.group(1) or "", line_num)
            suppressions.append((line_num, line_num + 1, raw))

        self._inline_suppressions = suppressions
        return suppressions

    def get_prose_blocks(self) -> list[MarkdownProseBlock]:
        """Return source-mapped prose blocks grouped by Markdown context."""
        if self._prose_blocks is not None:
            return self._prose_blocks

        code_lines = self._code_lines()
        html_lines = self._html_lines()
        setext_headings, setext_underlines = self._setext_lines()
        skipped_lines = (
            code_lines
            | html_lines
            | self._front_matter_lines()
            | self._mdx_block_lines()
        )
        heading_re = re.compile(r"^ {0,3}#{1,6}[ \t]+")
        trailing_heading_re = re.compile(r"[ \t]+#+[ \t]*$")
        list_re = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")

        blocks: list[MarkdownProseBlock] = []
        current_context = ""
        current_lines: list[tuple[int, str]] = []
        current_break = False
        list_indent = 0
        pending_break = False

        def flush() -> None:
            nonlocal current_context, current_lines, current_break, list_indent
            if current_lines:
                blocks.append(
                    MarkdownProseBlock(
                        context=current_context,
                        start_line=current_lines[0][0],
                        end_line=current_lines[-1][0],
                        lines=tuple(current_lines),
                        break_before=current_break,
                    )
                )
            current_context = ""
            current_lines = []
            current_break = False
            list_indent = 0

        for line_num, line in enumerate(self._lines, start=1):
            stripped_line, quote_prefix = self._strip_blockquote_prefix(line)
            if line_num in skipped_lines or self._is_table_row(stripped_line):
                flush()
                pending_break = True
                continue
            if line_num in setext_underlines:
                flush()
                continue
            if not stripped_line.strip():
                flush()
                continue

            chars = list(line)
            self._mask_chars(chars, 0, quote_prefix)
            heading_match = heading_re.match(stripped_line)
            list_match = list_re.match(stripped_line)
            next_list_indent = list_match.end() if list_match else 0
            force_new = False

            if quote_prefix:
                context = "blockquote"
            elif line_num in setext_headings:
                context = "heading"
                force_new = True
            elif heading_match:
                context = "heading"
                force_new = True
                self._mask_chars(chars, 0, heading_match.end())
                trailing_match = trailing_heading_re.search(stripped_line)
                if trailing_match:
                    self._mask_chars(
                        chars, trailing_match.start(), trailing_match.end()
                    )
            elif list_match:
                context = "list_item"
                force_new = True
                self._mask_chars(chars, 0, next_list_indent)
            elif (
                current_context == "list_item"
                and list_indent
                and len(line) - len(line.lstrip()) >= list_indent
            ):
                context = "list_item"
            else:
                context = "body"

            prose = self._mask_inline_code_and_links("".join(chars))
            if not prose.strip():
                continue
            if force_new or (current_context and context != current_context):
                flush()
            if not current_lines:
                current_context = context
                current_break = pending_break
                list_indent = next_list_indent
                pending_break = False
            current_lines.append((line_num, prose))

        flush()
        self._prose_blocks = blocks
        return blocks

    def get_prose_lines(self) -> list[tuple[int, str]]:
        """Return source-width-preserving Markdown prose lines."""
        return [line for block in self.get_prose_blocks() for line in block.lines]

    def get_prose_sentences(self) -> list[ProseSentence]:
        """Return cached source-mapped prose sentences."""
        if self._prose_sentences is None:
            self._prose_sentences = _sentences_from_blocks(self.get_prose_blocks())
        return self._prose_sentences

    @staticmethod
    def _is_table_row(line: str) -> bool:
        """Return True when a line looks like a Markdown table row."""
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            return False
        return stripped.count("|") >= 2

    @staticmethod
    def _mask_chars(chars: list[str], start: int, end: int) -> None:
        """Mask a character range without changing source offsets."""
        for idx in range(start, end):
            chars[idx] = " "

    def _front_matter_lines(self) -> set[int]:
        """Return a complete leading YAML or TOML front-matter span."""
        if not self._lines or self._lines[0].strip() not in {"---", "+++"}:
            return set()
        delimiter = self._lines[0].strip()
        for idx, line in enumerate(self._lines[1:], start=2):
            if line.strip() == delimiter:
                return set(range(1, idx + 1))
        return set()

    def _mdx_block_lines(self) -> set[int]:
        """Return narrow top-level MDX statement and component block spans."""
        mdx_lines: set[int] = set()
        import_re = re.compile(r'^\s*import\s+.+\s+from\s+["\'][^"\']+["\'];?\s*$')
        export_re = re.compile(
            r"^\s*export\s+(?:default|const|let|var|function|class|\{)\b"
        )
        open_re = re.compile(r"^\s*<([A-Z][\w.:]*)\b[^>]*>\s*$")
        self_closing_re = re.compile(r"^\s*<[A-Z][\w.:]*\b[^>]*/>\s*$")
        open_tag = ""

        for line_num, line in enumerate(self._lines, start=1):
            if open_tag:
                mdx_lines.add(line_num)
                if re.match(rf"^\s*</{re.escape(open_tag)}>\s*$", line):
                    open_tag = ""
                continue
            if (
                import_re.match(line)
                or export_re.match(line)
                or self_closing_re.match(line)
            ):
                mdx_lines.add(line_num)
                continue
            match = open_re.match(line)
            if match:
                mdx_lines.add(line_num)
                open_tag = match.group(1)
        return mdx_lines

    def _find_inline_code_spans(self, line: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        length = len(line)
        i = 0
        while i < length:
            if line[i] != "`":
                i += 1
                continue
            run_len = 1
            while i + run_len < length and line[i + run_len] == "`":
                run_len += 1
            j = i + run_len
            while j < length:
                if line[j] != "`":
                    j += 1
                    continue
                close_len = 1
                while j + close_len < length and line[j + close_len] == "`":
                    close_len += 1
                if close_len == run_len:
                    spans.append((i, j + close_len))
                    i = j + close_len
                    break
                j += close_len
            else:
                i += run_len
        return spans

    def _mask_inline_code(self, line: str) -> str:
        chars = list(line)
        for start, end in self._find_inline_code_spans(line):
            for idx in range(start, end):
                chars[idx] = " "
        return "".join(chars)

    def _mask_inline_code_and_links(self, line: str) -> str:
        masked = self._mask_inline_code(line)
        chars = list(masked)
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", masked):
            url_start = match.start(2)
            url_end = match.end(2)
            for idx in range(url_start, url_end):
                chars[idx] = " "
        for match in re.finditer(r"^\s*\[([^\]]+)\]:\s*(\S+)", masked):
            url_start = match.start(2)
            url_end = match.end(2)
            for idx in range(url_start, url_end):
                chars[idx] = " "
        for match in re.finditer(r"<(https?://[^>\s]+)>", masked):
            url_start = match.start(1)
            url_end = match.end(1)
            for idx in range(url_start, url_end):
                chars[idx] = " "
        return "".join(chars)

    def _strip_blockquote_prefix(self, line: str) -> tuple[str, int]:
        match = self._blockquote_re.match(line)
        if not match:
            return line, 0
        return line[match.end() :], match.end()


def iter_prose_lines(content: str, filename: str) -> list[tuple[int, str]]:
    """Return line-numbered prose lines for Markdown, raw lines otherwise."""
    if is_markdown_file(filename):
        return _get_cached_parser(content).get_prose_lines()
    return list(enumerate(content.split("\n"), start=1))


def iter_prose_blocks(content: str, filename: str) -> list[MarkdownProseBlock]:
    """Return source-mapped prose blocks for Markdown or plain text."""
    if is_markdown_file(filename):
        return _get_cached_parser(content).get_prose_blocks()

    blocks: list[MarkdownProseBlock] = []
    current: list[tuple[int, str]] = []
    for line_num, line in enumerate(content.split("\n"), start=1):
        if line.strip():
            current.append((line_num, line))
        elif current:
            blocks.append(
                MarkdownProseBlock(
                    "body", current[0][0], current[-1][0], tuple(current)
                )
            )
            current = []
    if current:
        blocks.append(
            MarkdownProseBlock("body", current[0][0], current[-1][0], tuple(current))
        )
    return blocks


def iter_non_code_lines(content: str, filename: str) -> list[tuple[int, str]]:
    """Return line-numbered lines excluding code blocks for Markdown."""
    if is_markdown_file(filename):
        return _get_cached_parser(content).get_lines()
    return list(enumerate(content.split("\n"), start=1))


# Pattern for headings that indicate example/demo content
_EXAMPLE_HEADING_RE = re.compile(
    r"\b(example|template|bad|detected|demo|before)\b", re.IGNORECASE
)


def is_example_line(content: str, filename: str, line_num: int) -> bool:
    """Return True if *line_num* falls under an example-style heading.

    Example-style headings contain words like "example", "template", "bad",
    "detected", "demo", or "before".  Content under such headings is expected to
    demonstrate the very patterns a rule flags, so matches should be
    downgraded to LOW confidence.
    """
    if not is_markdown_file(filename):
        return False

    parser = _get_cached_parser(content)
    headings = parser.get_headings()

    # Walk headings in reverse to find the nearest heading *before* line_num.
    for section in reversed(headings):
        if (
            section.start_line <= line_num <= section.end_line
            and _EXAMPLE_HEADING_RE.search(section.title)
        ):
            return True
    return False
