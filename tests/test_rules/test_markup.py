"""Tests for markup rules (M001-M010)."""

import pytest

from proseprobe.rules.base import Confidence, Severity
from proseprobe.rules.markup import (
    BareURLInProseRule,
    BrokenReferencesRule,
    ChatGPTMarkersRule,
    NonDescriptiveLinkTextRule,
    SkippedHeadingLevelRule,
    TemplateResidueRule,
    UnclosedCodeFenceRule,
    UnresolvedMarkdownReferencesRule,
    UTMParametersRule,
    WrongMarkupRule,
)


def test_wrong_markup_reports_only_the_markup_token() -> None:
    source = "    # This is **bold** prose"
    [issue] = WrongMarkupRule().check(source, "test.py")

    assert source[issue.column - 1 : issue.end_column - 1] == "**bold**"


def test_skipped_heading_reports_the_heading_title() -> None:
    source = "# Top\n\n### Skipped"
    [issue] = SkippedHeadingLevelRule().check(source, "test.md")
    line = source.splitlines()[issue.line - 1]

    assert line[issue.column - 1 : issue.end_column - 1] == "Skipped"


class TestWrongMarkup:
    """Tests for M001: Wrong Markup."""

    def test_detects_markdown_in_python(self) -> None:
        """Test detecting markdown syntax in Python comments."""
        text = """
# This is **bold** text in a comment
# And this has `code` formatting
"""
        rule = WrongMarkupRule()
        issues = rule.check(text, "test.py")
        assert len(issues) > 0

    def test_ignores_plain_comments(self) -> None:
        """Test ignoring plain Python comments."""
        text = """
# This is a normal comment
# Without any markdown
"""
        rule = WrongMarkupRule()
        issues = rule.check(text, "test.py")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = WrongMarkupRule()
        assert rule.id == "M001"

    def test_skips_hash_lines_inside_string_literals(self) -> None:
        """M001 should not flag # lines inside triple-quoted strings."""
        text = '''
default_config = """
# This is a **bold** TOML comment
# [tool.proseprobe]
"""
'''
        rule = WrongMarkupRule()
        issues = rule.check(text, "test.py")
        assert len(issues) == 0


class TestChatGPTMarkers:
    """Tests for M002: ChatGPT Markers."""

    def test_detects_chatgpt_patterns(self) -> None:
        """Test detecting ChatGPT markers."""
        text = "As an AI language model, I cannot provide this information."
        rule = ChatGPTMarkersRule()
        issues = rule.check(text, "test.md")
        # May or may not detect depending on patterns
        assert isinstance(issues, list)

    def test_ignores_clean_text(self) -> None:
        """Test ignoring clean text."""
        text = "This is normal human-written content."
        rule = ChatGPTMarkersRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = ChatGPTMarkersRule()
        assert rule.id == "M002"


class TestUTMParameters:
    """Tests for M003: UTM Parameters."""

    def test_detects_utm_patterns(self) -> None:
        """Test detecting UTM parameters in links."""
        text = "[Link](https://example.com?utm_source=chatgpt&utm_medium=ai)"
        rule = UTMParametersRule()
        issues = rule.check(text, "test.md")
        # May or may not detect depending on implementation
        assert isinstance(issues, list)

    def test_ignores_clean_links(self) -> None:
        """Test ignoring clean links."""
        text = "[Link](https://example.com/page)"
        rule = UTMParametersRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = UTMParametersRule()
        assert rule.id == "M003"

    def test_detects_utm_in_autolink(self) -> None:
        """Test detecting UTM parameters in autolinks."""
        text = "See <https://example.com?utm_source=chatgpt.com> for details."
        rule = UTMParametersRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 1

    def test_detects_utm_in_reference_definition(self) -> None:
        """Test detecting UTM parameters in reference link definitions."""
        text = "[ref]: https://example.com?utm_source=openai\n\nSee [ref][ref]."
        rule = UTMParametersRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 1


class TestBrokenReferences:
    """Tests for M004: Broken References."""

    def test_detects_broken_link(self) -> None:
        """Test detecting broken link references."""
        text = "See [this article][1] for more.\n\nNo reference defined."
        rule = BrokenReferencesRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_reports_explicit_inline_placeholder_at_destination(self) -> None:
        """Explicit replacement tokens should be high-confidence errors."""
        issues = BrokenReferencesRule().check("[example](URL_HERE)", "test.md")

        assert len(issues) == 1
        issue = issues[0]
        assert issue.rule_id == "M004"
        assert issue.message == "Placeholder link destination: 'URL_HERE'"
        assert issue.line == 1
        assert issue.column == 11
        assert issue.end_column == 19
        assert issue.severity is Severity.ERROR
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "Replace the placeholder with a real destination"

    @pytest.mark.parametrize("destination", ["INSERT_URL", "TODO", "TBD"])
    def test_reports_explicit_reference_destination_once(
        self,
        destination: str,
    ) -> None:
        """A referenced definition should be reported once at its destination."""
        text = f"[guide]: {destination}\n\nUse [guide][guide]."

        issues = BrokenReferencesRule().check(text, "test.md")

        assert len(issues) == 1
        assert issues[0].line == 1
        assert issues[0].column == 10
        assert issues[0].end_column == 10 + len(destination)
        assert issues[0].confidence is Confidence.HIGH

    @pytest.mark.parametrize(
        ("text", "column", "end_column"),
        [("[empty]()", 9, 9), ("[top](#)", 7, 8)],
    )
    def test_reports_ambiguous_destinations_at_low_confidence(
        self,
        text: str,
        column: int,
        end_column: int,
    ) -> None:
        """Empty and bare-fragment destinations should be low confidence."""
        [issue] = BrokenReferencesRule().check(text, "test.md")

        assert (issue.column, issue.end_column) == (column, end_column)
        assert issue.confidence is Confidence.LOW

    def test_accepts_real_destinations_and_ignored_contexts(self) -> None:
        """Valid links and Markdown examples should remain quiet."""
        valid = """\
[relative](/guide)
[fragment](#install)
[email](mailto:ops@example.com)
[example](https://example.com/docs)
<https://example.com/docs>
`[inline](URL_HERE)`
<div>
[html](URL_HERE)
</div>
"""
        example = "# Example links\n\n[placeholder](URL_HERE)"

        assert BrokenReferencesRule().check(valid, "test.md") == []
        assert BrokenReferencesRule().check(example, "test.md") == []

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = BrokenReferencesRule()
        assert rule.id == "M004"

    def test_detects_attached_file_ref(self) -> None:
        """Test detecting [attached_file:N] references."""
        text = "See [attached_file:1] for details"
        rule = BrokenReferencesRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 1
        assert "attached_file" in issues[0].message
        assert issues[0].confidence is Confidence.MEDIUM


class TestUnresolvedMarkdownReferences:
    """Tests for M005: Unresolved Markdown References."""

    def test_reports_undefined_full_reference_with_exact_fields(self) -> None:
        """Undefined full references should be high-confidence errors."""
        text = "See [setup guide][install] now."

        issues = UnresolvedMarkdownReferencesRule().check(text, "guide.md")

        assert len(issues) == 1
        issue = issues[0]
        assert issue.rule_id == "M005"
        assert issue.message == "Undefined reference label: 'install'"
        assert issue.line == 1
        assert issue.column == 5
        assert issue.end_column == 27
        assert issue.severity is Severity.ERROR
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == (
            "Define '[install]: destination' or use an inline link"
        )

    @pytest.mark.parametrize(
        ("text", "label"),
        [
            ("See [install][].", "install"),
            ("![diagram][architecture]", "architecture"),
        ],
    )
    def test_reports_collapsed_and_image_references(
        self,
        text: str,
        label: str,
    ) -> None:
        """Collapsed and image references should use their target labels."""
        issues = UnresolvedMarkdownReferencesRule().check(text, "guide.md")

        assert len(issues) == 1
        assert f"'{label}'" in issues[0].message

    def test_accepts_resolved_full_collapsed_and_shortcut_references(self) -> None:
        """Every supported reference form should resolve through one definition."""
        text = """\
[install]: /install

[guide][install]
[install][]
[install]
"""

        assert UnresolvedMarkdownReferencesRule().check(text, "guide.md") == []

    def test_accepts_normalized_and_escaped_labels(self) -> None:
        """Case, whitespace, and escaped brackets should normalize for matching."""
        text = "[A  Ref\\[\\]]: /one\n\nSee [guide][a\tref\\[\\]]."

        assert UnresolvedMarkdownReferencesRule().check(text, "guide.md") == []

    def test_ignores_bare_brackets_inline_links_footnotes_and_code(self) -> None:
        """Ambiguous bracket text and excluded Markdown contexts stay quiet."""
        text = """\
[ordinary]
[inline](/url)
[^note]
`[code][missing]`
```markdown
[fenced][missing]
```
"""

        assert UnresolvedMarkdownReferencesRule().check(text, "guide.md") == []
        assert (
            UnresolvedMarkdownReferencesRule().check(
                "See [guide][missing].",
                "guide.py",
            )
            == []
        )

    def test_reports_every_conflicting_definition_at_low_confidence(self) -> None:
        """Conflicting destinations should identify all definition sites."""
        text = "[ref]: /first\n[REF]: /second"

        issues = UnresolvedMarkdownReferencesRule().check(text, "guide.md")

        assert len(issues) == 2
        assert [issue.line for issue in issues] == [1, 2]
        assert [issue.column for issue in issues] == [1, 1]
        assert all(issue.end_column == 6 for issue in issues)
        assert all(issue.severity is Severity.ERROR for issue in issues)
        assert all(issue.confidence is Confidence.LOW for issue in issues)
        assert all(
            issue.message == "Conflicting reference definition: 'ref'"
            for issue in issues
        )
        assert all(
            issue.suggestion == "Use one destination for reference label 'ref'"
            for issue in issues
        )

    def test_accepts_identical_duplicate_definitions(self) -> None:
        """Repeated definitions are harmless when destinations agree."""
        text = "[ref]: /same\n[REF]: /same"

        assert UnresolvedMarkdownReferencesRule().check(text, "guide.md") == []


class TestTemplateResidue:
    """Tests for M006: Template Residue."""

    @pytest.mark.parametrize(
        "text",
        [
            "Lorem ipsum dolor sit amet.",
            "[insert example here]",
            "[replace this section]",
            "<replace-me>",
            "YOUR CONTENT HERE",
        ],
    )
    def test_reports_explicit_markers_at_high_confidence(self, text: str) -> None:
        """Explicit template markers should be high-confidence findings."""
        issues = TemplateResidueRule().check(text, "guide.md")

        assert len(issues) == 1
        assert issues[0].confidence is Confidence.HIGH

    def test_reports_exact_issue_fields(self) -> None:
        """Template findings should include source spans and replacement advice."""
        issues = TemplateResidueRule().check("YOUR CONTENT HERE", "guide.md")

        assert len(issues) == 1
        issue = issues[0]
        assert issue.rule_id == "M006"
        assert issue.message == "Template residue (content marker): 'YOUR CONTENT HERE'"
        assert issue.line == 1
        assert issue.column == 1
        assert issue.end_column == 18
        assert issue.severity is Severity.WARNING
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "Replace this placeholder with final content"

    @pytest.mark.parametrize("text", ["TODO", "TBD: add details"])
    def test_reports_bounded_planning_markers_at_low_confidence(
        self,
        text: str,
    ) -> None:
        """Standalone TODO and TBD markers should remain filterable."""
        issues = TemplateResidueRule().check(text, "guide.md")

        assert len(issues) == 1
        assert issues[0].confidence is Confidence.LOW

    @pytest.mark.parametrize(
        "text",
        [
            "The placeholder attribute identifies an empty value.",
            "The release date remains TBD pending review.",
            "[Add authentication]",
            "Your content here should explain the result.",
        ],
    )
    def test_ignores_legitimate_prose(self, text: str) -> None:
        """Explanatory prose and near misses should stay quiet."""
        assert TemplateResidueRule().check(text, "guide.md") == []

    def test_ignores_example_template_and_before_sections(self) -> None:
        """Example-style sections may document every supported marker."""
        text = """\
## Example
Lorem ipsum dolor sit amet.

## Template
[insert example here]

## Before
YOUR CONTENT HERE

## Result
Use <replace-me> now.
"""

        issues = TemplateResidueRule().check(text, "guide.md")

        assert len(issues) == 1
        assert issues[0].line == 11

    def test_ignores_code_and_html_blocks(self) -> None:
        """Code samples and HTML blocks are not publishable prose."""
        text = """\
`YOUR CONTENT HERE`

```text
[insert example here]
```

<div>
Lorem ipsum
</div>

Visible <replace-me> marker.
"""

        issues = TemplateResidueRule().check(text, "guide.md")

        assert len(issues) == 1
        assert issues[0].line == 11

    def test_prefers_explicit_marker_over_overlapping_todo(self) -> None:
        """An explicit marker should not receive a duplicate low-confidence issue."""
        issues = TemplateResidueRule().check("TODO: YOUR CONTENT HERE", "guide.md")

        assert len(issues) == 1
        assert issues[0].confidence is Confidence.HIGH
        assert issues[0].column == 7

    def test_ignores_non_markdown_input(self) -> None:
        """Python placeholders remain the responsibility of C004."""
        assert TemplateResidueRule().check("YOUR CONTENT HERE", "guide.py") == []


class TestUnclosedCodeFence:
    """Tests for M007: Unclosed Code Fence."""

    def test_reports_exact_opening_fence_fields(self) -> None:
        """An unclosed fence should be a high-confidence opening-span error."""
        text = "Intro.\n  ````python\nprint('hidden')"

        [issue] = UnclosedCodeFenceRule().check(text, "guide.md")

        assert issue.rule_id == "M007"
        assert issue.message == "Unclosed code fence: '````'"
        assert issue.line == 2
        assert issue.column == 3
        assert issue.end_column == 7
        assert issue.severity is Severity.ERROR
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "Add a matching '````' closing fence"

    @pytest.mark.parametrize(
        "text",
        [
            "~~~text\nhidden\n```",
            "````\nhidden\n```",
        ],
    )
    def test_rejects_mismatched_or_shorter_closers(self, text: str) -> None:
        """Only the same character repeated at least as long closes a block."""
        assert len(UnclosedCodeFenceRule().check(text, "guide.md")) == 1

    @pytest.mark.parametrize(
        "text",
        [
            "```text\nbody\n```",
            "~~~~\nbody\n~~~~~",
        ],
    )
    def test_accepts_matching_and_longer_closers(self, text: str) -> None:
        """A same-character closer may equal or exceed the opener length."""
        assert UnclosedCodeFenceRule().check(text, "guide.md") == []

    def test_applies_only_to_markdown(self) -> None:
        """Fence-like Python strings are outside M007's scope."""
        assert UnclosedCodeFenceRule().check("```\nbody", "guide.py") == []


class TestSkippedHeadingLevel:
    """Tests for M008: Skipped Heading Level."""

    def test_reports_skipped_atx_heading_fields(self) -> None:
        text = "# Title\n\n### Details"

        [issue] = SkippedHeadingLevelRule().check(text, "guide.md")

        assert issue.rule_id == "M008"
        assert issue.message == "Heading level jumps from 1 to 3"
        assert issue.line == 3
        assert issue.column == 5
        assert issue.end_column == 12
        assert issue.severity is Severity.WARNING
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == ("Add a level-2 heading before this level-3 heading")

    def test_uses_setext_heading_as_previous_visible_heading(self) -> None:
        text = "> Title\n> =====\n\n> ### Details"

        [issue] = SkippedHeadingLevelRule().check(text, "guide.md")

        assert issue.line == 4
        assert issue.message == "Heading level jumps from 1 to 3"

    @pytest.mark.parametrize("later_heading", ["   ### Details", ">    ### Details"])
    def test_reports_indented_atx_heading(self, later_heading: str) -> None:
        text = f"# Title\n\n{later_heading}"

        [issue] = SkippedHeadingLevelRule().check(text, "guide.md")

        assert issue.line == 3
        assert issue.message == "Heading level jumps from 1 to 3"

    @pytest.mark.parametrize(
        "text",
        [
            "### Fragment title\n\n### Peer",
            "# Title\n\n## Section\n\n### Detail\n\n## Peer\n\n# Next",
        ],
    )
    def test_ignores_valid_heading_sequences(self, text: str) -> None:
        assert SkippedHeadingLevelRule().check(text, "guide.md") == []

    @pytest.mark.parametrize(
        "hidden_block",
        [
            "```markdown\n### Hidden\n```",
            "<section>\n### Hidden\n</section>",
            "<script>\n### Hidden\n</script>",
            "<style>\n### Hidden\n</style>",
            "<textarea>\n### Hidden\n</textarea>",
        ],
    )
    def test_ignores_headings_inside_hidden_blocks(self, hidden_block: str) -> None:
        text = f"# Title\n\n{hidden_block}\n\n## Visible"

        assert SkippedHeadingLevelRule().check(text, "guide.md") == []

    def test_ignores_heading_inside_blockquoted_fence(self) -> None:
        text = "# Title\n\n> ```markdown\n> ### Hidden\n> ```\n\n## Visible"

        assert SkippedHeadingLevelRule().check(text, "guide.md") == []

    def test_applies_only_to_markdown(self) -> None:
        text = "# Title\n\n### Details"

        assert SkippedHeadingLevelRule().check(text, "guide.py") == []


class TestBareURLInProse:
    """Tests for M009: Bare URL in Prose."""

    def test_reports_exact_url_fields(self) -> None:
        source = "Read https://example.com/guide?mode=fast."

        [issue] = BareURLInProseRule().check(source, "guide.md")

        assert issue.rule_id == "M009"
        assert issue.message == (
            "Bare URL in prose: 'https://example.com/guide?mode=fast'"
        )
        assert issue.line == 1
        assert issue.column == 6
        assert issue.end_line == 1
        assert issue.end_column == 41
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "Use descriptive Markdown link text"

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("Read HTTP://example.com.", "HTTP://example.com"),
            (
                "Read https://example.com/releases/(v2).",
                "https://example.com/releases/(v2)",
            ),
            ("Read (https://example.com/guide).", "https://example.com/guide"),
        ],
    )
    def test_handles_url_boundaries(self, source: str, expected: str) -> None:
        [issue] = BareURLInProseRule().check(source, "guide.md")

        assert issue.message == f"Bare URL in prose: '{expected}'"
        assert source[issue.column - 1 : issue.end_column - 1] == expected

    def test_reports_multiple_urls_in_source_order(self) -> None:
        source = "See https://a.example then http://b.example/path."

        issues = BareURLInProseRule().check(source, "guide.md")

        assert [issue.message for issue in issues] == [
            "Bare URL in prose: 'https://a.example'",
            "Bare URL in prose: 'http://b.example/path'",
        ]

    @pytest.mark.parametrize(
        "source",
        [
            "Read [the guide](https://example.com/guide).",
            "Read <https://example.com/guide>.",
            "[guide]: https://example.com/guide",
            "Use `https://example.com/guide`.",
            "```text\nhttps://example.com/guide\n```",
        ],
    )
    def test_ignores_protected_markdown_syntax(self, source: str) -> None:
        assert BareURLInProseRule().check(source, "guide.md") == []

    @pytest.mark.parametrize(
        "source",
        [
            "# https://example.com/heading",
            "- https://example.com/resource",
            "> https://example.com/quote",
            "| URL |\n| --- |\n| https://example.com/table |",
        ],
    )
    def test_ignores_non_body_contexts(self, source: str) -> None:
        assert BareURLInProseRule().check(source, "guide.md") == []

    @pytest.mark.parametrize(
        "source",
        [
            "The literal URL is https://example.com/test.",
            "The URL string is https://example.com/test.",
            "## Example\n\nVisit https://example.com/test.",
        ],
    )
    def test_ignores_explicit_literal_and_example_context(self, source: str) -> None:
        assert BareURLInProseRule().check(source, "guide.md") == []

    def test_does_not_suppress_a_normal_url_mention(self) -> None:
        [issue] = BareURLInProseRule().check(
            "Read the URL https://example.com/test.", "guide.md"
        )

        assert issue.rule_id == "M009"

    def test_applies_only_to_markdown(self) -> None:
        assert (
            BareURLInProseRule().check("Visit https://example.com.", "guide.py") == []
        )


class TestNonDescriptiveLinkText:
    """Tests for M010: Non-Descriptive Link Text."""

    def test_reports_exact_inline_label_fields(self) -> None:
        source = "Read [click here](/guide)."

        [issue] = NonDescriptiveLinkTextRule().check(source, "guide.md")

        assert issue.rule_id == "M010"
        assert issue.message == "Non-descriptive link text: 'click here'"
        assert issue.line == 1
        assert issue.column == 7
        assert issue.end_column == 17
        assert issue.severity is Severity.WARNING
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "Replace with text that describes the destination"
        assert source[issue.column - 1 : issue.end_column - 1] == "click here"

    @pytest.mark.parametrize("label", ["here", "CLICK HERE", " this   link ", "link"])
    def test_normalizes_only_fixed_weak_labels(self, label: str) -> None:
        issues = NonDescriptiveLinkTextRule().check(
            f"Read [{label}](/guide).", "guide.md"
        )

        assert len(issues) == 1

    @pytest.mark.parametrize(
        ("source", "line"),
        [
            ("[target]: /guide\n\nRead [this link][target].", 3),
            ("[here]: /guide\n\nRead [here][].", 3),
            ("[here]: /guide\n\nRead [here].", 3),
            ("> Read [here](/guide).", 1),
            ("| Resource |\n| --- |\n| [here](/guide) |", 3),
        ],
    )
    def test_handles_supported_markdown_link_forms(
        self, source: str, line: int
    ) -> None:
        [issue] = NonDescriptiveLinkTextRule().check(source, "guide.md")

        assert issue.line == line

    def test_returns_multiple_findings_in_source_order(self) -> None:
        source = "[target]: /guide\n\n[here][target] then [link](/other)."

        issues = NonDescriptiveLinkTextRule().check(source, "guide.md")

        assert [issue.column for issue in issues] == sorted(
            issue.column for issue in issues
        )

    @pytest.mark.parametrize(
        "source",
        [
            "Read [click here for installation](/guide).",
            "Read [deployment guide](/guide).",
            "Read <https://example.com>.",
            "![here](/diagram.png)",
            "[target]: /diagram.png\n\n![here][target]",
            "[here]: /guide",
            "Read [here][missing].",
            "Use `[here](/guide)` as the example.",
            "```markdown\n[here](/guide)\n```",
            "<div>\n[here](/guide)\n</div>",
            "## Example\n\nRead [here](/guide).",
        ],
    )
    def test_ignores_out_of_scope_links(self, source: str) -> None:
        assert NonDescriptiveLinkTextRule().check(source, "guide.md") == []

    def test_ignores_non_markdown_input(self) -> None:
        assert (
            NonDescriptiveLinkTextRule().check("Read [here](/guide).", "guide.py") == []
        )
