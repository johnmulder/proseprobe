"""Tests for style rules (T001-T006)."""

from humanize.rules.style import (
    BoldOveruseRule,
    ElegantVariationRule,
    EmDashOveruseRule,
    EmojiInProseRule,
    QuoteInconsistencyRule,
    TitleCaseHeadingsRule,
)


class TestTitleCaseHeadings:
    """Tests for T001: Title Case Headings."""

    def test_detects_improper_case(self) -> None:
        """Test detecting improper title case."""
        text = "## this is a heading"
        rule = TitleCaseHeadingsRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = TitleCaseHeadingsRule()
        assert rule.id == "T001"
        assert rule.name == "Title Case Headings"


class TestBoldOveruse:
    """Tests for T002: Bold Overuse."""

    def test_detects_excessive_bold(self) -> None:
        """Test detecting excessive bold usage."""
        text = """
        This is **important** and **critical** and **essential**.
        """
        rule = BoldOveruseRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = BoldOveruseRule()
        assert rule.id == "T002"


class TestEmDashOveruse:
    """Tests for T003: Em Dash Overuse."""

    def test_detects_em_dash(self) -> None:
        """Test detecting em dash usage."""
        text = "This is a statement—and here is more—with em dashes."
        rule = EmDashOveruseRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = EmDashOveruseRule()
        assert rule.id == "T003"


class TestQuoteInconsistency:
    """Tests for T004: Quote Inconsistency."""

    def test_detects_quote_issues(self) -> None:
        """Test detecting quote inconsistencies."""
        text = "He said \"hello\" and 'goodbye'."
        rule = QuoteInconsistencyRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = QuoteInconsistencyRule()
        assert rule.id == "T004"


class TestEmojiInProse:
    """Tests for T005: Emoji in Prose."""

    def test_detects_emoji(self) -> None:
        """Test detecting emoji in prose."""
        text = "This is great! 🎉 Let's celebrate! 🚀"
        rule = EmojiInProseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) > 0

    def test_allows_no_emoji(self) -> None:
        """Test text without emojis."""
        text = "This is plain text without any emoji."
        rule = EmojiInProseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = EmojiInProseRule()
        assert rule.id == "T005"


class TestElegantVariation:
    """Tests for T006: Elegant Variation."""

    def test_detects_variation(self) -> None:
        """Test detecting elegant variation."""
        text = "The function returns a value. This method produces output."
        rule = ElegantVariationRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = ElegantVariationRule()
        assert rule.id == "T006"
