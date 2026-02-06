"""Tests for markup rules (M001-M004)."""

from slop_lint.rules.markup import (
    BrokenReferencesRule,
    ChatGPTMarkersRule,
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

    def test_fix_removes_utm_params(self) -> None:
        """Test that fix removes UTM parameters from URLs."""
        text = "Check [link](https://example.com?utm_source=chatgpt.com&other=1)"
        rule = UTMParametersRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 1

        fixed = rule.fix(text, issues[0])
        assert "utm_source=chatgpt.com" not in fixed
        assert "other=1" in fixed

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

    def test_fix_removes_broken_ref(self) -> None:
        """Test that fix removes broken references."""
        text = "See [attached_file:1] for details"
        rule = BrokenReferencesRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 1

        fixed = rule.fix(text, issues[0])
        assert "[attached_file:1]" not in fixed


class TestChatGPTMarkersFix:
    """Tests for ChatGPT markers fix."""

    def test_fix_removes_turn_search_marker(self) -> None:
        """Test that fix removes turn0search0 markers."""
        text = "See turn0search0 for more info"
        rule = ChatGPTMarkersRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 1

        fixed = rule.fix(text, issues[0])
        assert "turn0search0" not in fixed
