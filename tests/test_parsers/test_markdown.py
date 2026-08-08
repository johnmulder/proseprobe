"""Tests for Markdown parser."""

import pytest

from proseprobe.parsers.markdown import (
    MarkdownCodeBlock,
    MarkdownLink,
    MarkdownParser,
    MarkdownProseBlock,
    MarkdownReference,
    MarkdownSection,
    _get_cached_parser,
    _parser_cache,
    clear_parser_cache,
    is_example_line,
    is_markdown_file,
    iter_non_code_lines,
    iter_prose_blocks,
    iter_prose_lines,
)
from proseprobe.parsers.prose import iter_inline_suppressions


def test_heading_records_preserve_exact_title_source_spans() -> None:
    source = "  ## Reliable System Design ##\n\n> Setext Title\n> ============"

    headings = MarkdownParser(source).get_headings()

    assert [
        source.splitlines()[heading.start_line - 1][
            heading.column - 1 : heading.end_column - 1
        ]
        for heading in headings
    ] == ["Reliable System Design", "Setext Title"]


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

    def test_get_headings_setext(self) -> None:
        """Test extracting setext headings."""
        content = "Main Title\n====\n\nSub Title\n----\n"
        parser = MarkdownParser(content)
        headings = parser.get_headings()

        assert len(headings) == 2
        assert headings[0].level == 1
        assert headings[0].title == "Main Title"
        assert headings[1].level == 2
        assert headings[1].title == "Sub Title"

    def test_get_headings_setext_blockquote(self) -> None:
        """Test extracting setext headings inside blockquotes."""
        content = "> Quoted Title\n> ----\n\nText"
        parser = MarkdownParser(content)
        headings = parser.get_headings()

        assert len(headings) == 1
        assert headings[0].level == 2
        assert headings[0].title == "Quoted Title"

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

    def test_template_heading_is_example_context(self) -> None:
        """Template sections should be recognized as example content."""
        content = "## Template\n\nYOUR CONTENT HERE\n\n## Result\n\nPublished."

        assert is_example_line(content, "guide.md", 3)
        assert not is_example_line(content, "guide.md", 7)

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

    def test_prose_lines_exclude_table_rows(self) -> None:
        """Table markup should not be treated as prose sentences."""
        content = """\
| Prefix | Category |
|--------|----------|
| `V` | Vocabulary |

This is prose.
"""
        parser = MarkdownParser(content)

        lines = parser.get_prose_lines()

        assert lines == [(5, "This is prose.")]

    def test_prose_lines_mask_list_markers_but_keep_item_text(self) -> None:
        """List item text is prose, but the bullet marker is masked."""
        content = """\
- First item explains the behavior.
- Second item explains the tradeoff.

This is prose.
"""
        parser = MarkdownParser(content)

        lines = parser.get_prose_lines()

        assert lines == [
            (1, "  First item explains the behavior."),
            (2, "  Second item explains the tradeoff."),
            (4, "This is prose."),
        ]

    def test_get_prose_blocks_classifies_markdown_contexts(self) -> None:
        """Prose blocks retain their structural Markdown context."""
        content = """\
# Heading

Body text.

- First item.
  Continued item text.
  - Nested item.

> Quoted text.
"""

        blocks = iter_prose_blocks(content, "test.md")

        assert all(isinstance(block, MarkdownProseBlock) for block in blocks)
        assert [
            (block.context, block.start_line, block.end_line) for block in blocks
        ] == [
            ("heading", 1, 1),
            ("body", 3, 3),
            ("list_item", 5, 6),
            ("list_item", 7, 7),
            ("blockquote", 9, 9),
        ]
        assert blocks[0].lines == ((1, "  Heading"),)
        assert blocks[2].lines[0] == (5, "  First item.")
        assert blocks[4].lines == ((9, "  Quoted text."),)

    def test_get_prose_blocks_classifies_setext_heading(self) -> None:
        """A Setext title is a heading block and its underline is syntax."""
        blocks = MarkdownParser("Title\n-----\n\nBody.").get_prose_blocks()

        assert [
            (block.context, block.start_line, block.end_line) for block in blocks
        ] == [
            ("heading", 1, 1),
            ("body", 4, 4),
        ]
        assert blocks[0].lines == ((1, "Title"),)

    def test_unindented_text_ends_a_list_item_block(self) -> None:
        """Unindented prose after a list item returns to body context."""
        blocks = MarkdownParser("- Item.\nBody.").get_prose_blocks()

        assert [block.context for block in blocks] == ["list_item", "body"]

    def test_get_prose_blocks_marks_skipped_constructs_as_breaks(self) -> None:
        """Code, HTML, and table content create structural sequence breaks."""
        content = """\
Before.

```text
hidden
```

After code.

<div>
hidden
</div>

After HTML.

| A | B |
| - | - |

After table.
"""

        blocks = MarkdownParser(content).get_prose_blocks()

        assert [block.lines[0][1] for block in blocks] == [
            "Before.",
            "After code.",
            "After HTML.",
            "After table.",
        ]
        assert [block.break_before for block in blocks] == [False, True, True, True]

    def test_get_prose_blocks_skips_front_matter_and_mdx(self) -> None:
        """Front matter and simple MDX constructs are structural barriers."""
        content = """\
---
title: Hidden
---
import Card from "./Card"

<Card>
Hidden component text.
</Card>

Visible prose.
"""

        blocks = MarkdownParser(content).get_prose_blocks()

        assert len(blocks) == 1
        assert blocks[0].lines == ((10, "Visible prose."),)
        assert blocks[0].break_before is True

    def test_get_prose_blocks_unclosed_fence_is_a_break(self) -> None:
        """An unclosed fence excludes the remainder of the document."""
        blocks = MarkdownParser("Visible.\n\n```text\nhidden").get_prose_blocks()

        assert len(blocks) == 1
        assert blocks[0].lines == ((1, "Visible."),)

    def test_prose_mask_preserves_source_columns(self) -> None:
        """Masking Markdown syntax keeps matches at source offsets."""
        source = "- Use `code` before pivotal [docs](https://example.com)."

        line = MarkdownParser(source).get_prose_lines()[0][1]

        assert len(line) == len(source)
        assert line.index("pivotal") == source.index("pivotal")
        assert "code" not in line
        assert "https://example.com" not in line

    def test_get_links(self) -> None:
        """Test extracting markdown links."""
        content = "See [Example](https://example.com) for details."
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert len(links) == 1
        assert links[0].text == "Example"
        assert links[0].url == "https://example.com"
        assert links[0].line == 1

    def test_get_links_url_span(self) -> None:
        """Test link URL spans map to the source line."""
        content = "See [Example](https://example.com/path) for details."
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert len(links) == 1
        link = links[0]
        assert (
            content[link.url_start - 1 : link.url_end - 1] == "https://example.com/path"
        )

    def test_get_links_retains_empty_inline_destination_span(self) -> None:
        """An empty inline destination should retain its insertion point."""
        [link] = MarkdownParser("[example]()").get_links()

        assert (
            link.url,
            link.line,
            link.column,
            link.url_start,
            link.url_end,
        ) == ("", 1, 1, 11, 11)

    def test_get_links_autolink(self) -> None:
        """Test extracting autolink URLs."""
        content = "See <https://example.com/path> for details."
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert len(links) == 1
        assert links[0].url == "https://example.com/path"
        assert (
            content[links[0].url_start - 1 : links[0].url_end - 1]
            == "https://example.com/path"
        )

    def test_get_links_reference_definition(self) -> None:
        """Test extracting reference link definitions."""
        content = "[ref]: https://example.com"
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert len(links) == 1
        assert links[0].url == "https://example.com"
        assert links[0].line == 1

    def test_get_links_reference_usage(self) -> None:
        """Test extracting reference link usage."""
        content = "[ref]: https://example.com\n\nSee [ref][ref]."
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert any(
            link.url == "https://example.com" and link.line == 3 for link in links
        )

    def test_get_links_reference_collapsed(self) -> None:
        """Test extracting collapsed reference link usage."""
        content = "[ref]: https://example.com\n\nSee [ref][]."
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert any(
            link.url == "https://example.com" and link.line == 3 for link in links
        )

    def test_get_references_returns_ordered_records_with_source_spans(self) -> None:
        """Definitions and uses should retain exact source locations."""
        content = "[ref]: /one\n\nSee [text][ref]."

        references = MarkdownParser(content).get_references()

        assert all(isinstance(reference, MarkdownReference) for reference in references)
        assert [reference.is_definition for reference in references] == [True, False]
        definition, use = references
        assert (
            definition.label,
            definition.text,
            definition.destination,
            definition.line,
            definition.column,
            definition.end_column,
            definition.destination_start,
            definition.destination_end,
        ) == ("ref", "ref", "/one", 1, 1, 6, 8, 12)
        assert (
            use.label,
            use.text,
            use.destination,
            use.line,
            use.column,
            use.end_column,
        ) == ("ref", "text", None, 3, 5, 16)

    def test_get_references_retains_empty_definition_destination(self) -> None:
        """An empty definition should remain available to markup rules."""
        [reference] = MarkdownParser("[ref]:").get_references()

        assert reference.is_definition is True
        assert (
            reference.destination,
            reference.line,
            reference.destination_start,
            reference.destination_end,
        ) == ("", 1, 7, 7)

    def test_get_references_keeps_undefined_full_collapsed_and_image_uses(
        self,
    ) -> None:
        """Unambiguous reference syntax should be exposed without definitions."""
        content = "[text][missing]\n[missing][]\n![diagram][image]"

        references = MarkdownParser(content).get_references()

        assert [
            (reference.label, reference.text, reference.line, reference.column)
            for reference in references
        ] == [
            ("missing", "text", 1, 1),
            ("missing", "missing", 2, 1),
            ("image", "diagram", 3, 1),
        ]

    def test_get_references_normalizes_case_whitespace_and_escaped_brackets(
        self,
    ) -> None:
        """Reference labels should use CommonMark-style normalized matching."""
        content = "[A  Ref\\[\\]]: /one\n\nSee [text][a\tref\\[\\]]."

        references = MarkdownParser(content).get_references()

        assert [reference.label for reference in references] == ["a ref[]", "a ref[]"]
        assert MarkdownParser(content).get_links()[-1].url == "/one"

    def test_get_references_retains_duplicates_and_first_definition_wins(
        self,
    ) -> None:
        """All definitions should remain visible while the first resolves links."""
        content = "[ref]: /first\n[REF]: /second\n\nUse [text][ref]."
        parser = MarkdownParser(content)

        definitions = [
            reference
            for reference in parser.get_references()
            if reference.is_definition
        ]
        usage = next(link for link in parser.get_links() if link.line == 4)

        assert [reference.destination for reference in definitions] == [
            "/first",
            "/second",
        ]
        assert usage.url == "/first"

    def test_get_references_recognizes_only_resolved_shortcuts(self) -> None:
        """Bare brackets are references only when a definition exists."""
        content = "[known]: /url\n\n[known] and [unknown]"

        uses = [
            reference
            for reference in MarkdownParser(content).get_references()
            if not reference.is_definition
        ]

        assert [(reference.label, reference.text) for reference in uses] == [
            ("known", "known")
        ]

    def test_get_references_ignores_non_reference_contexts(self) -> None:
        """Footnotes, inline links, code, and HTML blocks are out of scope."""
        content = """\
[^note]: Footnote text
[inline](/url)
`[code][missing]`
```markdown
[fenced][missing]
```
<div>
[html][missing]
</div>
"""

        assert MarkdownParser(content).get_references() == []

    def test_get_links_in_table(self) -> None:
        """Test extracting links inside markdown tables."""
        content = (
            "| Name | Link |\n| --- | --- |\n| Example | [Site](https://example.com) |"
        )
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert len(links) == 1
        assert links[0].url == "https://example.com"

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

    def test_unquoted_fence_preserves_blockquote_marker_in_content(self) -> None:
        content = "```text\n> quoted-looking code\n```"

        [block] = MarkdownParser(content).get_code_blocks()

        assert block[3] == "> quoted-looking code"

    def test_get_code_blocks_unclosed(self) -> None:
        """Test unclosed fenced code blocks extend to EOF."""
        content = "Text\n```\ncode line"
        parser = MarkdownParser(content)
        blocks = parser.get_code_blocks()

        assert len(blocks) == 1
        start_line, end_line, _, code = blocks[0]
        assert start_line == 2
        assert end_line == 3
        assert "code line" in code

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            (
                "```python\npass\n```",
                (1, 3, "python", "pass", "```", 1, True),
            ),
            (
                "  ~~~~\nbody\n~~~~~",
                (1, 3, "", "body", "~~~~", 3, True),
            ),
            (
                "````\n~~~\n```\nbody",
                (1, 4, "", "~~~\n```\nbody", "````", 1, False),
            ),
        ],
    )
    def test_get_code_block_records_preserve_fence_state(
        self,
        content: str,
        expected: tuple[int, int, str, str, str, int, bool],
    ) -> None:
        """Fence records should retain their opener, span, and closure state."""
        parser = MarkdownParser(content)

        [block] = parser.get_code_block_records()

        assert isinstance(block, MarkdownCodeBlock)
        assert (
            block.start_line,
            block.end_line,
            block.language,
            block.content,
            block.fence,
            block.column,
            block.closed,
        ) == expected
        assert parser.get_code_blocks() == [expected[:4]]

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

    def test_get_headings_blockquote(self) -> None:
        """Test headings inside blockquotes are detected."""
        content = "> # Quoted Heading\n\nText"
        parser = MarkdownParser(content)
        headings = parser.get_headings()

        assert len(headings) == 1
        assert headings[0].title == "Quoted Heading"

    def test_get_paragraphs_strips_blockquote_prefix(self) -> None:
        """Test paragraphs strip blockquote markers."""
        content = "> This is quoted text.\n\nNext paragraph."
        parser = MarkdownParser(content)
        paragraphs = parser.get_paragraphs()

        assert len(paragraphs) == 2
        assert paragraphs[0][2] == "This is quoted text."

    def test_get_paragraphs_skip_setext_headings(self) -> None:
        """Test paragraphs skip setext headings."""
        content = "Title\n----\n\nPara."
        parser = MarkdownParser(content)
        paragraphs = parser.get_paragraphs()

        assert len(paragraphs) == 1
        assert "Para." in paragraphs[0][2]

    def test_get_lines_excludes_code_blocks(self) -> None:
        """Test get_lines omits fenced code lines."""
        content = "Intro\n```\ncode\n```\nOutro"
        parser = MarkdownParser(content)
        lines = parser.get_lines()

        line_numbers = [line_num for line_num, _ in lines]
        assert 2 not in line_numbers
        assert 3 not in line_numbers
        assert 4 not in line_numbers

    def test_iter_non_code_lines_excludes_code(self) -> None:
        """Test iter_non_code_lines omits code blocks."""
        content = "Intro\n```python\ncode\n```\nOutro"
        lines = iter_non_code_lines(content, "test.md")

        line_numbers = [line_num for line_num, _ in lines]
        assert 2 not in line_numbers
        assert 3 not in line_numbers
        assert 4 not in line_numbers

    def test_iter_prose_lines_masks_inline_code_and_links(self) -> None:
        """Test iter_prose_lines masks inline code and link URLs."""
        content = "Use `delve` and [Example](https://example.com) here."
        lines = iter_prose_lines(content, "test.md")

        assert len(lines) == 1
        masked = lines[0][1]
        assert "delve" not in masked
        assert "https://example.com" not in masked
        assert "Example" in masked

    def test_iter_prose_lines_masks_autolink(self) -> None:
        """Test iter_prose_lines masks autolink URLs."""
        content = "See <https://example.com/delve>."
        lines = iter_prose_lines(content, "test.md")

        assert len(lines) == 1
        masked = lines[0][1]
        assert "delve" not in masked

    def test_iter_prose_lines_masks_reference_def(self) -> None:
        """Test iter_prose_lines masks reference definition URLs."""
        content = "[ref]: https://example.com/delve"
        lines = iter_prose_lines(content, "test.md")

        assert len(lines) == 1
        masked = lines[0][1]
        assert "delve" not in masked

    def test_iter_prose_lines_skips_table_text(self) -> None:
        """Test table text is excluded from prose lines."""
        content = "| Word |\n| --- |\n| delve |"
        lines = iter_prose_lines(content, "test.md")

        assert all("delve" not in line for _, line in lines)

    def test_iter_prose_lines_skips_html_block(self) -> None:
        """Test HTML block lines are excluded from prose."""
        content = "<div>\ndelve here\n</div>\n\nText"
        lines = iter_prose_lines(content, "test.md")

        assert all("delve" not in line for _, line in lines)
        assert any("Text" in line for _, line in lines)

    def test_get_links_ignores_html_block(self) -> None:
        """Test links inside HTML blocks are ignored."""
        content = "<div>\n[Site](https://example.com)\n</div>\n\nText"
        parser = MarkdownParser(content)
        links = parser.get_links()

        assert links == []

    def test_iter_prose_lines_non_markdown_pass_through(self) -> None:
        """Test iter_prose_lines returns raw lines for non-Markdown."""
        content = "Use `delve` in code."
        lines = iter_prose_lines(content, "test.txt")

        assert len(lines) == 1
        assert lines[0][1] == content

    def test_extract_inline_suppression_for_next_physical_line(self) -> None:
        """A standalone Markdown directive targets exactly the next line."""
        content = (
            "Intro\n"
            "  <!-- proseprobe-ignore-next-line v001, S010 -->\n"
            "Target\n"
            "<!-- proseprobe-ignore-next-line V002 -->\n"
            "\n"
            "Not targeted\n"
        )

        assert iter_inline_suppressions(content, "test.md") == [
            (2, 3, "v001, S010"),
            (4, 5, "V002"),
        ]

    def test_inline_suppression_examples_are_ignored(self) -> None:
        """Fenced and inline-code examples are not active directives."""
        content = (
            "```markdown\n"
            "<!-- proseprobe-ignore-next-line V001 -->\n"
            "Target\n"
            "```\n"
            "`<!-- proseprobe-ignore-next-line V002 -->`\n"
        )

        assert iter_inline_suppressions(content, "test.md") == []

    def test_malformed_markdown_suppression_reports_source_line(self) -> None:
        """Marker-bearing standalone comments reject malformed token lists."""
        parser = MarkdownParser(
            "Intro\n<!-- proseprobe-ignore-next-line V001, -->\nTarget"
        )

        with pytest.raises(ValueError, match=r"line 2"):
            parser.get_inline_suppressions()

    def test_is_markdown_file_variants(self) -> None:
        """Test markdown file extension detection."""
        assert is_markdown_file("README.md")
        assert is_markdown_file("notes.mdx")
        assert is_markdown_file("doc.MARKDOWN")
        assert not is_markdown_file("script.py")


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
            column=3,
            end_column=13,
        )

        assert section.level == 1
        assert section.title == "Test Title"
        assert section.content == "Some content"
        assert section.start_line == 1
        assert section.end_line == 3
        assert section.column == 3
        assert section.end_column == 13


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


class TestParserCache:
    """Tests for MarkdownParser caching."""

    def test_cache_returns_same_parser(self) -> None:
        """Test that cache returns the same parser for same content."""
        clear_parser_cache()
        content = "# Test\n\nSome content."
        parser1 = _get_cached_parser(content)
        parser2 = _get_cached_parser(content)
        assert parser1 is parser2

    def test_cache_different_content(self) -> None:
        """Test that cache returns different parsers for different content."""
        clear_parser_cache()
        content1 = "# Test 1\n\nContent one."
        content2 = "# Test 2\n\nContent two."
        parser1 = _get_cached_parser(content1)
        parser2 = _get_cached_parser(content2)
        assert parser1 is not parser2

    def test_clear_cache(self) -> None:
        """Test clearing the parser cache."""
        content = "# Cached\n\nContent."
        _get_cached_parser(content)
        assert len(_parser_cache) > 0
        clear_parser_cache()
        assert len(_parser_cache) == 0

    def test_iter_prose_lines_uses_cache(self) -> None:
        """Test that iter_prose_lines uses cached parser."""
        clear_parser_cache()
        content = "# Heading\n\nParagraph text."
        # First call should populate cache
        lines1 = iter_prose_lines(content, "test.md")
        cache_size = len(_parser_cache)
        # Second call should use cache (no new entries)
        lines2 = iter_prose_lines(content, "test.md")
        assert len(_parser_cache) == cache_size
        assert lines1 == lines2

    def test_iter_non_code_lines_uses_cache(self) -> None:
        """Test that iter_non_code_lines uses cached parser."""
        clear_parser_cache()
        content = "# Heading\n\n```python\ncode\n```\n\nText."
        # First call should populate cache
        lines1 = iter_non_code_lines(content, "test.md")
        cache_size = len(_parser_cache)
        # Second call should use cache (no new entries)
        lines2 = iter_non_code_lines(content, "test.md")
        assert len(_parser_cache) == cache_size
        assert lines1 == lines2


def test_prose_sentences_are_cached_on_markdown_parser() -> None:
    parser = MarkdownParser("A wrapped\nsentence.")

    first = parser.get_prose_sentences()

    assert first is parser.get_prose_sentences()
    assert first[0].source_position(first[0].text.index("sentence")) == (2, 1)
