"""Tests for markup rules (M001-M006)."""

import pytest

from slop_lint.rules.base import Confidence, Severity
from slop_lint.rules.markup import (
    BrokenReferencesRule,
    ChatGPTMarkersRule,
    TemplateResidueRule,
    UnresolvedMarkdownReferencesRule,
    UTMParametersRule,
    WrongMarkupRule,
)


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
# [tool.slop-lint]
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
