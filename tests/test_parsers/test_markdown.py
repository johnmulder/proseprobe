"""Tests for Markdown parser."""

from humanize.parsers.markdown import MarkdownLink, MarkdownParser, MarkdownSection


class TestMarkdownParser:
    """Tests for MarkdownParser class."""

    def test_init(self) -> None:
        """Test parser initialization."""
        content = "# Hello\n\nWorld"
        parser = MarkdownParser(content)

        assert parser.content == content
        assert parser._lines == ["# Hello", "", "World"]

    def test_get_headings_empty(self) -> None:
        """Test getting headings from empty document."""
        parser = MarkdownParser("")
        headings = parser.get_headings()
        assert headings == []

    def test_get_headings_h1(self) -> None:
        """Test extracting H1 headings."""
        content = "# Main Title\n\nSome content here."
        parser = MarkdownParser(content)
        headings = parser.get_headings()

        assert len(headings) == 1
        assert headings[0].level == 1
        assert headings[0].title == "Main Title"

    def test_get_headings_strips_trailing_hashes(self) -> None:
        """Test stripping trailing heading markers."""
        content = "## Heading ##\nText"
        parser = MarkdownParser(content)
        headings = parser.get_headings()

        assert len(headings) == 1
        assert headings[0].title == "Heading"

    def test_get_headings_preserves_punctuation_and_emoji(self) -> None:
        """Test headings preserve punctuation and emoji."""
        content = "## Plan: Launch! 🚀\nText"
        parser = MarkdownParser(content)
        headings = parser.get_headings()

        assert len(headings) == 1
        assert headings[0].title == "Plan: Launch! 🚀"

    def test_get_paragraphs_empty(self) -> None:
        """Test getting paragraphs from empty document."""
        parser = MarkdownParser("")
        paragraphs = parser.get_paragraphs()
        assert paragraphs == []

    def test_get_links_empty(self) -> None:
        """Test getting links from empty document."""
        parser = MarkdownParser("")
        links = parser.get_links()
        assert links == []

    def test_get_links(self) -> None:
        """Test extracting markdown links."""
        content = "See [Example](https://example.com) for details."
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert len(links) == 1
        assert links[0].text == "Example"
        assert links[0].url == "https://example.com"
        assert links[0].line == 1

    def test_get_links_ignores_inline_code(self) -> None:
        """Test that links inside inline code are ignored."""
        content = "Use `[Example](https://example.com)` in text."
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert links == []

    def test_get_links_ignores_inline_code_double_ticks(self) -> None:
        """Test that links inside double-backtick code are ignored."""
        content = "Use ``[Example](https://example.com)`` in text."
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert links == []

    def test_get_links_with_inline_code_and_link(self) -> None:
        """Test links still parse when inline code appears before."""
        content = "Use ``code `with` ticks`` and [Example](https://example.com)."
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert len(links) == 1
        assert links[0].text == "Example"
    def test_get_code_blocks_empty(self) -> None:
        """Test getting code blocks from empty document."""
        parser = MarkdownParser("")
        blocks = parser.get_code_blocks()
        assert blocks == []

    def test_get_code_blocks(self) -> None:
        """Test extracting fenced code blocks."""
        content = "Text\n```python\nprint('hi')\n```\nAfter"
        parser = MarkdownParser(content)
        blocks = parser.get_code_blocks()

        assert len(blocks) == 1
        start_line, end_line, language, code = blocks[0]
        assert language == "python"
        assert "print('hi')" in code
        assert start_line == 2
        assert end_line == 4

    def test_get_code_blocks_with_tildes(self) -> None:
        """Test extracting tildes fenced code blocks."""
        content = "Text\n~~~\ncode\n~~~\nAfter"
        parser = MarkdownParser(content)
        blocks = parser.get_code_blocks()

        assert len(blocks) == 1
        start_line, end_line, _, code = blocks[0]
        assert start_line == 2
        assert end_line == 4
        assert code.strip() == "code"

    def test_get_code_blocks_with_indentation(self) -> None:
        """Test extracting indented fenced code blocks."""
        content = "Text\n   ```\ncode\n   ```\nAfter"
        parser = MarkdownParser(content)
        blocks = parser.get_code_blocks()

        assert len(blocks) == 1
        start_line, end_line, _, code = blocks[0]
        assert start_line == 2
        assert end_line == 4
        assert code.strip() == "code"

    def test_get_bullet_lists_empty(self) -> None:
        """Test getting bullet lists from empty document."""
        parser = MarkdownParser("")
        lists = parser.get_bullet_lists()
        assert lists == []

    def test_get_bullet_lists(self) -> None:
        """Test extracting bullet lists."""
        content = "- One\n- Two\n\nAfter"
        parser = MarkdownParser(content)
        lists = parser.get_bullet_lists()

        assert len(lists) == 1
        start_line, end_line, items = lists[0]
        assert start_line == 1
        assert end_line == 2
        assert items == ["One", "Two"]

    def test_get_bullet_lists_numbered_and_reset(self) -> None:
        """Test extracting numbered lists and list resets."""
        content = "1. One\n2. Two\n\n- Three"
        parser = MarkdownParser(content)
        lists = parser.get_bullet_lists()

        assert len(lists) == 2
        assert lists[0][0] == 1
        assert lists[0][1] == 2
        assert lists[0][2] == ["One", "Two"]
        assert lists[1][0] == 4
        assert lists[1][1] == 4
        assert lists[1][2] == ["Three"]

    def test_get_bullet_lists_nested(self) -> None:
        """Test extracting nested list items."""
        content = "- Parent\n  - Child\n- Sibling"
        parser = MarkdownParser(content)
        lists = parser.get_bullet_lists()

        assert len(lists) == 1
        assert lists[0][2] == ["Parent", "Child", "Sibling"]

    def test_get_paragraphs_skips_code(self) -> None:
        """Test paragraphs skip fenced code blocks."""
        content = "Para one.\n\n```txt\ncode line\n```\n\nPara two."
        parser = MarkdownParser(content)
        paragraphs = parser.get_paragraphs()

        assert len(paragraphs) == 2
        assert "Para one." in paragraphs[0][2]
        assert "Para two." in paragraphs[1][2]

    def test_get_paragraphs_skip_lists_and_headings(self) -> None:
        """Test paragraphs skip list and heading lines."""
        content = "# Title\n\nPara one.\n- Item\n\nPara two."
        parser = MarkdownParser(content)
        paragraphs = parser.get_paragraphs()

        assert len(paragraphs) == 2
        assert "Para one." in paragraphs[0][2]
        assert "Para two." in paragraphs[1][2]

    def test_get_headings_ignores_code_block(self) -> None:
        """Test headings inside code blocks are ignored."""
        content = "```md\n# Not a heading\n```\n# Real Heading"
        parser = MarkdownParser(content)
        headings = parser.get_headings()

        assert len(headings) == 1
        assert headings[0].title == "Real Heading"


class TestMarkdownSection:
    """Tests for MarkdownSection dataclass."""

    def test_create_section(self) -> None:
        """Test creating a section."""
        section = MarkdownSection(
            level=1,
            title="Test Title",
            content="Some content",
            start_line=1,
            end_line=3,
        )

        assert section.level == 1
        assert section.title == "Test Title"
        assert section.content == "Some content"
        assert section.start_line == 1
        assert section.end_line == 3


class TestMarkdownLink:
    """Tests for MarkdownLink dataclass."""

    def test_create_link(self) -> None:
        """Test creating a link."""
        link = MarkdownLink(
            text="Example",
            url="https://example.com",
            line=5,
            column=10,
        )

        assert link.text == "Example"
        assert link.url == "https://example.com"
        assert link.line == 5
        assert link.column == 10
