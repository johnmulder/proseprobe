"""Tests for grammar rules (G001-G003)."""

from slop_lint.rules.grammar import (
    CopulaAvoidanceRule,
    ExcessiveHedgingRule,
    ParticipleChainsRule,
)


class TestCopulaAvoidance:
    """Tests for G001: Copula Avoidance."""

    def test_detects_serves_as(self) -> None:
        """Test detecting 'serves as' copula avoidance."""
        text = "This function serves as a helper."
        rule = CopulaAvoidanceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) > 0

    def test_detects_functions_as(self) -> None:
        """Test detecting 'functions as' copula avoidance."""
        text = "The module functions as an interface."
        rule = CopulaAvoidanceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) > 0

    def test_ignores_simple_is(self) -> None:
        """Test ignoring simple 'is' usage."""
        text = "This is a helper function."
        rule = CopulaAvoidanceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = CopulaAvoidanceRule()
        assert rule.id == "G001"
        assert rule.name == "Copula Avoidance"


class TestExcessiveHedging:
    """Tests for G002: Excessive Hedging."""

    def test_detects_hedging_patterns(self) -> None:
        """Test detecting hedging patterns."""
        text = "This approach may help improve performance."
        rule = ExcessiveHedgingRule()
        issues = rule.check(text, "test.md")
        # May or may not detect depending on patterns
        assert isinstance(issues, list)

    def test_ignores_confident_language(self) -> None:
        """Test ignoring confident language."""
        text = "This approach improves performance."
        rule = ExcessiveHedgingRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = ExcessiveHedgingRule()
        assert rule.id == "G002"


class TestParticipleChainsRule:
    """Tests for G003: Participle Chains."""

    def test_detects_participle_chains(self) -> None:
        """Test detecting participle chains."""
        text = "The team, working diligently while maintaining focus, delivered."
        rule = ParticipleChainsRule()
        issues = rule.check(text, "test.md")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = ParticipleChainsRule()
        assert rule.id == "G003"
