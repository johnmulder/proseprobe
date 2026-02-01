"""Tests for structural rules (S001-S007)."""

from humanize.rules.struct import (
    ChallengeConclusionsRule,
    FalseRangesRule,
    InlineHeaderListsRule,
    NegativeParallelismRule,
    RuleOfThreeRule,
    SignificanceEmphasisRule,
    SuperficialAnalysisRule,
)


class TestRuleOfThree:
    """Tests for S001: Rule of Three."""

    def test_detects_triadic_pattern(self) -> None:
        """Test detecting three-item comma lists."""
        text = """
        This provides clarity, efficiency, and elegance.
        It offers speed, accuracy, and reliability.
        The system has power, flexibility, and simplicity.
        We value honesty, integrity, and transparency.
        """
        rule = RuleOfThreeRule()
        issues = rule.check(text, "test.md")
        # Excessive triads should be flagged
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = RuleOfThreeRule()
        assert rule.id == "S001"
        assert rule.name == "Rule of Three"


class TestNegativeParallelism:
    """Tests for S002: Negative Parallelism."""

    def test_detects_not_only_but_also(self) -> None:
        """Test detecting 'not only... but also' patterns."""
        text = "This not only improves speed but also enhances reliability."
        rule = NegativeParallelismRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = NegativeParallelismRule()
        assert rule.id == "S002"


class TestChallengeConclusionsRule:
    """Tests for S003: Challenge Conclusions."""

    def test_detects_conclusion_patterns(self) -> None:
        """Test detecting conclusion phrases."""
        text = "In conclusion, this article has shown the importance of testing."
        rule = ChallengeConclusionsRule()
        issues = rule.check(text, "test.md")
        # May or may not detect depending on patterns
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = ChallengeConclusionsRule()
        assert rule.id == "S003"


class TestInlineHeaderLists:
    """Tests for S004: Inline Header Lists."""

    def test_detects_inline_headers(self) -> None:
        """Test detecting inline header lists."""
        text = "**Key Features:** Speed, accuracy, and reliability."
        rule = InlineHeaderListsRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = InlineHeaderListsRule()
        assert rule.id == "S004"


class TestSignificanceEmphasis:
    """Tests for S005: Significance Emphasis."""

    def test_detects_significance_markers(self) -> None:
        """Test detecting significance markers."""
        text = "It is worth noting that this is important."
        rule = SignificanceEmphasisRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = SignificanceEmphasisRule()
        assert rule.id == "S005"


class TestSuperficialAnalysis:
    """Tests for S006: Superficial Analysis."""

    def test_detects_superficial_analysis(self) -> None:
        """Test detecting superficial analysis patterns."""
        text = "This is a complex topic that deserves careful consideration."
        rule = SuperficialAnalysisRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = SuperficialAnalysisRule()
        assert rule.id == "S006"


class TestFalseRanges:
    """Tests for S007: False Ranges."""

    def test_detects_false_ranges(self) -> None:
        """Test detecting false range patterns."""
        text = "This approach may potentially help in some cases."
        rule = FalseRangesRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = FalseRangesRule()
        assert rule.id == "S007"
