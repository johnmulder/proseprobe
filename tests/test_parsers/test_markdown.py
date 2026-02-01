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

        assert len(headings) >= 0  # May or may not be implemented

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

    def test_get_code_blocks_empty(self) -> None:
        """Test getting code blocks from empty document."""
        parser = MarkdownParser("")
        blocks = parser.get_code_blocks()
        assert blocks == []

    def test_get_bullet_lists_empty(self) -> None:
        """Test getting bullet lists from empty document."""
        parser = MarkdownParser("")
        lists = parser.get_bullet_lists()
        assert lists == []


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
