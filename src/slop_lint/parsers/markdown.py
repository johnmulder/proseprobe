"""Markdown parser for extracting structured content."""

import re
from dataclasses import dataclass

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
        # Remove first (oldest) entry
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


@dataclass
class MarkdownLink:
    """A link in a Markdown document."""

    text: str
    url: str
    line: int
    column: int
    url_start: int = 0
    url_end: int = 0


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
        self._code_blocks: list[tuple[int, int, str, str]] | None = None
        self._code_block_lines: set[int] | None = None
        self._setext_heading_lines: set[int] | None = None
        self._setext_underline_lines: set[int] | None = None
        self._html_block_lines: set[int] | None = None
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
            "details",
            "summary",
            "figure",
            "figcaption",
        }

    def _ensure_code_blocks(self) -> None:
        if self._code_blocks is not None and self._code_block_lines is not None:
            return

        blocks: list[tuple[int, int, str, str]] = []
        code_lines: set[int] = set()

        in_block = False
        fence_char = ""
        fence_len = 0
        language = ""
        start_line = 0
        content_lines: list[str] = []

        fence_re = re.compile(r"^( {0,3})(`{3,}|~{3,})\s*([\w+-]+)?\s*$")

        for line_num, line in enumerate(self._lines, start=1):
            if not in_block:
                match = fence_re.match(line)
                if match:
                    fence = match.group(2)
                    fence_char = fence[0]
                    fence_len = len(fence)
                    language = match.group(3) or ""
                    start_line = line_num
                    content_lines = []
                    in_block = True
                    code_lines.add(line_num)
                continue

            code_lines.add(line_num)
            close_re = re.compile(
                rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_len},}}\s*$"
            )
            if close_re.match(line):
                blocks.append(
                    (start_line, line_num, language, "\n".join(content_lines))
                )
                in_block = False
                fence_char = ""
                fence_len = 0
                language = ""
                content_lines = []
            else:
                content_lines.append(line)

        if in_block:
            blocks.append(
                (start_line, len(self._lines), language, "\n".join(content_lines))
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
        headings: list[tuple[int, int, str]] = []
        heading_re = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
        setext_re = re.compile(r"^ {0,3}(=+|-+)\s*$")
        idx = 0
        while idx < len(self._lines):
            line_num = idx + 1
            if line_num in code_lines or line_num in html_lines:
                idx += 1
                continue
            raw_line = self._lines[idx]
            stripped_line, _ = self._strip_blockquote_prefix(raw_line)
            match = heading_re.match(stripped_line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                title = re.sub(r"\s+#+\s*$", "", title).strip()
                headings.append((line_num, level, title))
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
                        headings.append((line_num, level, stripped_line.strip()))
                        idx += 2
                        continue

            idx += 1

        sections: list[MarkdownSection] = []
        for idx, (line_num, level, title) in enumerate(headings):
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
        heading_re = re.compile(r"^(#{1,6})\s+")
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

    def get_links(self) -> list[MarkdownLink]:
        """Extract all links from the document.

        Returns:
            List of links with positions.
        """
        self._ensure_code_blocks()
        code_lines = self._code_lines()
        html_lines = self._html_lines()
        links: list[MarkdownLink] = []
        link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        ref_def_re = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)")
        ref_use_re = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")
        autolink_re = re.compile(r"<(https?://[^>\s]+)>")

        reference_defs: dict[str, tuple[str, int, int, int]] = {}
        used_refs: set[str] = set()

        for line_num, line in enumerate(self._lines, start=1):
            if line_num in code_lines or line_num in html_lines:
                continue
            stripped_line, prefix_len = self._strip_blockquote_prefix(line)
            match = ref_def_re.match(stripped_line)
            if match:
                ref_id = match.group(1).strip().lower()
                url = match.group(2)
                url_start = match.start(2) + 1 + prefix_len
                url_end = match.end(2) + 1 + prefix_len
                reference_defs[ref_id] = (url, line_num, url_start, url_end)

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
            for match in ref_use_re.finditer(masked):
                ref_text = match.group(1).strip()
                ref_id = match.group(2).strip().lower() or ref_text.lower()
                if ref_id in reference_defs:
                    url, _, _, _ = reference_defs[ref_id]
                    used_refs.add(ref_id)
                    links.append(
                        MarkdownLink(
                            text=ref_text,
                            url=url,
                            line=line_num,
                            column=match.start() + 1 + prefix_len,
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

        for ref_id, (url, line_num, url_start, url_end) in reference_defs.items():
            if ref_id in used_refs:
                continue
            links.append(
                MarkdownLink(
                    text=ref_id,
                    url=url,
                    line=line_num,
                    column=url_start,
                    url_start=url_start,
                    url_end=url_end,
                )
            )

        return links

    def get_code_blocks(self) -> list[tuple[int, int, str, str]]:
        """Extract fenced code blocks.

        Returns:
            List of (start_line, end_line, language, content) tuples.
        """
        self._ensure_code_blocks()
        return self._code_blocks or []

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

    def get_prose_lines(self) -> list[tuple[int, str]]:
        """Return non-code lines with inline code and link URLs masked."""
        lines = self.get_lines()
        return [
            (line_num, self._mask_inline_code_and_links(line))
            for line_num, line in lines
        ]

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
        stripped_line, _ = self._strip_blockquote_prefix(line)
        masked = self._mask_inline_code(stripped_line)
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


def iter_non_code_lines(content: str, filename: str) -> list[tuple[int, str]]:
    """Return line-numbered lines excluding code blocks for Markdown."""
    if is_markdown_file(filename):
        return _get_cached_parser(content).get_lines()
    return list(enumerate(content.split("\n"), start=1))


# Pattern for headings that indicate example/demo content
_EXAMPLE_HEADING_RE = re.compile(
    r"\b(example|bad|detected|demo|before)\b", re.IGNORECASE
)


def is_example_line(content: str, filename: str, line_num: int) -> bool:
    """Return True if *line_num* falls under an example-style heading.

    Example-style headings contain words like "example", "bad", "detected",
    "demo", or "before".  Content under such headings is expected to
    demonstrate the very patterns a rule flags, so matches should be
    downgraded to LOW confidence.
    """
    if not is_markdown_file(filename):
        return False

    parser = _get_cached_parser(content)
    headings = parser.get_headings()

    # Walk headings in reverse to find the nearest heading *before* line_num.
    for section in reversed(headings):
        if section.start_line <= line_num <= section.end_line and _EXAMPLE_HEADING_RE.search(section.title):
            return True
    return False
