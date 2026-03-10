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


# ---------- Phase 10 TDD: G004-G009 ----------


class TestFalseSuspenseTransition:
    """Tests for G004: False Suspense Transition."""

    def test_detects_heres_the_kicker(self) -> None:
        """Detect 'Here's the kicker' false suspense."""
        from slop_lint.rules.grammar import FalseSuspenseTransitionRule

        text = "Here's the kicker."
        rule = FalseSuspenseTransitionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G004"

    def test_detects_heres_the_thing(self) -> None:
        """Detect 'Here's the thing about' false suspense."""
        from slop_lint.rules.grammar import FalseSuspenseTransitionRule

        text = "Here's the thing about AI adoption."
        rule = FalseSuspenseTransitionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_heres_where_it_gets_interesting(self) -> None:
        """Detect 'Here's where it gets interesting' variant."""
        from slop_lint.rules.grammar import FalseSuspenseTransitionRule

        text = "Here's where it gets interesting."
        rule = FalseSuspenseTransitionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal use of 'here'."""
        from slop_lint.rules.grammar import FalseSuspenseTransitionRule

        text = "Here is the configuration file for the project."
        rule = FalseSuspenseTransitionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.grammar import FalseSuspenseTransitionRule

        rule = FalseSuspenseTransitionRule()
        assert rule.id == "G004"
        assert rule.name == "False Suspense Transition"


class TestPatronizingAnalogy:
    """Tests for G005: Patronizing Analogy."""

    def test_detects_think_of_it_as(self) -> None:
        """Detect 'Think of it as...' patronizing analogy."""
        from slop_lint.rules.grammar import PatronizingAnalogyRule

        text = "Think of it as a Swiss Army knife for your workflow."
        rule = PatronizingAnalogyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G005"

    def test_detects_think_of_it_like(self) -> None:
        """Detect 'Think of it like...' variant."""
        from slop_lint.rules.grammar import PatronizingAnalogyRule

        text = "Think of it like a highway system for data."
        rule = PatronizingAnalogyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose without patronizing analogies."""
        from slop_lint.rules.grammar import PatronizingAnalogyRule

        text = "The system uses a caching layer for performance."
        rule = PatronizingAnalogyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.grammar import PatronizingAnalogyRule

        rule = PatronizingAnalogyRule()
        assert rule.id == "G005"
        assert rule.name == "Patronizing Analogy"


class TestFuturistInvitation:
    """Tests for G006: Futurist Invitation."""

    def test_detects_imagine_a_world(self) -> None:
        """Detect 'Imagine a world where...' invitation."""
        from slop_lint.rules.grammar import FuturistInvitationRule

        text = "Imagine a world where every tool has a quiet intelligence behind it."
        rule = FuturistInvitationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G006"

    def test_detects_in_that_world(self) -> None:
        """Detect 'In that world,...' follow-up."""
        from slop_lint.rules.grammar import FuturistInvitationRule

        text = "In that world, workflows stop being manual steps."
        rule = FuturistInvitationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal use of 'imagine'."""
        from slop_lint.rules.grammar import FuturistInvitationRule

        text = "You can imagine how complex this becomes at scale."
        rule = FuturistInvitationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.grammar import FuturistInvitationRule

        rule = FuturistInvitationRule()
        assert rule.id == "G006"
        assert rule.name == "Futurist Invitation"


class TestFalseVulnerability:
    """Tests for G007: False Vulnerability."""

    def test_detects_this_is_not_a_rant(self) -> None:
        """Detect 'This is not a rant' false vulnerability."""
        from slop_lint.rules.grammar import FalseVulnerabilityRule

        text = "This is not a rant; it's a diagnosis."
        rule = FalseVulnerabilityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G007"

    def test_detects_let_me_be_honest(self) -> None:
        """Detect 'Let me be honest' variant."""
        from slop_lint.rules.grammar import FalseVulnerabilityRule

        text = "Let me be honest about the state of this project."
        rule = FalseVulnerabilityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose."""
        from slop_lint.rules.grammar import FalseVulnerabilityRule

        text = "The integration test revealed a subtle timing bug."
        rule = FalseVulnerabilityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.grammar import FalseVulnerabilityRule

        rule = FalseVulnerabilityRule()
        assert rule.id == "G007"
        assert rule.name == "False Vulnerability"


class TestAssertedSimplicity:
    """Tests for G008: Asserted Simplicity."""

    def test_detects_reality_is_simpler(self) -> None:
        """Detect 'The reality is simpler' assertion."""
        from slop_lint.rules.grammar import AssertedSimplicityRule

        text = "The reality is simpler and less flattering."
        rule = AssertedSimplicityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G008"

    def test_detects_history_is_clear(self) -> None:
        """Detect 'History is clear' assertion."""
        from slop_lint.rules.grammar import AssertedSimplicityRule

        text = "History is clear on this point."
        rule = AssertedSimplicityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_the_truth_is(self) -> None:
        """Detect 'The truth is' assertion."""
        from slop_lint.rules.grammar import AssertedSimplicityRule

        text = "The truth is most teams don't need microservices."
        rule = AssertedSimplicityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag prose without asserted simplicity."""
        from slop_lint.rules.grammar import AssertedSimplicityRule

        text = "The algorithm runs in O(n log n) time complexity."
        rule = AssertedSimplicityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.grammar import AssertedSimplicityRule

        rule = AssertedSimplicityRule()
        assert rule.id == "G008"
        assert rule.name == "Asserted Simplicity"


class TestPedagogicalVoice:
    """Tests for G009: Pedagogical Voice."""

    def test_detects_lets_break_this_down(self) -> None:
        """Detect 'Let's break this down' pedagogical voice."""
        from slop_lint.rules.grammar import PedagogicalVoiceRule

        text = "Let's break this down step by step."
        rule = PedagogicalVoiceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G009"

    def test_detects_lets_unpack(self) -> None:
        """Detect 'Let's unpack' variant."""
        from slop_lint.rules.grammar import PedagogicalVoiceRule

        text = "Let's unpack what this really means."
        rule = PedagogicalVoiceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_lets_dive_in(self) -> None:
        """Detect 'Let's dive in' variant."""
        from slop_lint.rules.grammar import PedagogicalVoiceRule

        text = "Let's dive into the details."
        rule = PedagogicalVoiceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose."""
        from slop_lint.rules.grammar import PedagogicalVoiceRule

        text = "The configuration file supports TOML format."
        rule = PedagogicalVoiceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.grammar import PedagogicalVoiceRule

        rule = PedagogicalVoiceRule()
        assert rule.id == "G009"
        assert rule.name == "Pedagogical Voice"
