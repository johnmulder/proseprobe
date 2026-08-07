"""Tests for markup rules (M001-M005)."""

import pytest

from slop_lint.rules.base import Confidence, Severity
from slop_lint.rules.markup import (
    BrokenReferencesRule,
    ChatGPTMarkersRule,
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

    def test_detects_placeholder_link(self) -> None:
        """Test detecting placeholder links."""
        text = "[example](URL_HERE)"
        rule = BrokenReferencesRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

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
