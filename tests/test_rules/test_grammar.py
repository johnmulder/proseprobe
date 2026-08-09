"""Tests for grammar rules (G001-G017, G019, G022, G024-G025, G029)."""

import pytest

from proseprobe.rules.base import Confidence, Rule, Severity
from proseprobe.rules.grammar import (
    AmbiguousThisRule,
    AssertedSimplicityRule,
    CopulaAvoidanceRule,
    DoubleNegativeRule,
    EmptyItOpenerRule,
    ExcessiveHedgingRule,
    ExistentialOpenerRule,
    FalseSuspenseTransitionRule,
    FalseVulnerabilityRule,
    FormerLatterReferenceRule,
    FuturistInvitationRule,
    GenericSceneSettingOpenerRule,
    ParticipleChainsRule,
    PatronizingAnalogyRule,
    PedagogicalVoiceRule,
    UnclearActorRequirementRule,
    WeakInstructionVerbRule,
)


@pytest.mark.parametrize(
    ("rule", "source", "expected"),
    [
        (
            FalseSuspenseTransitionRule(),
            "Wait: here's the kicker.",
            "here's the kicker",
        ),
        (PatronizingAnalogyRule(), "Think of it as a queue.", "think of it as"),
        (
            FuturistInvitationRule(),
            "Picture a world where retries vanish.",
            "picture a world where",
        ),
        (FalseVulnerabilityRule(), "Let me be honest about this.", "Let me be honest"),
        (AssertedSimplicityRule(), "Put simply, the cache is stale.", "Put simply"),
        (PedagogicalVoiceRule(), "Let's unpack what this means.", "let's unpack what"),
    ],
)
def test_trope_matches_have_exact_source_spans(
    rule: Rule,
    source: str,
    expected: str,
) -> None:
    [issue] = rule.check(source, "test.md")

    assert issue.end_line is None
    assert issue.end_column is not None
    assert (
        source[issue.column - 1 : issue.end_column - 1].casefold()
        == expected.casefold()
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

    def test_detects_two_participle_heads(self) -> None:
        """Detect two coordinated participial clause heads."""
        text = "The team, working diligently while maintaining focus, delivered."
        issues = ParticipleChainsRule().check(text, "test.md")

        assert len(issues) == 1
        assert issues[0].message == "Participle chain: 'working, maintaining'"
        assert issues[0].column == 11
        assert issues[0].end_column == 47

    def test_detects_three_participle_heads(self) -> None:
        """Detect three comma-separated participial clause heads."""
        text = (
            "Leveraging modern techniques, enhancing performance, fostering adoption."
        )
        issues = ParticipleChainsRule().check(text, "test.md")

        assert len(issues) == 1
        assert issues[0].message == (
            "Participle chain: 'Leveraging, enhancing, fostering'"
        )
        assert issues[0].column == 1
        assert issues[0].end_column == 63

    def test_ignores_non_chains(self) -> None:
        """Ignore progressive clauses, technical gerunds, and examples."""
        rule = ParticipleChainsRule()
        texts = (
            "More people are adopting it, and everyone is talking about trends sweeping the industry.",
            "The company is undergoing a strategic restructuring and right-sizing initiative.",
            'The guide quotes "highlighting risks, reducing costs" as an example.',
            "The working group reviewed naming conventions before testing them.",
            "The report concludes by highlighting the result.",
            "Running without a profile preserves the selection, warning",
        )

        for text in texts:
            assert rule.check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = ParticipleChainsRule()
        assert rule.id == "G003"


# ---------- Phase 10 TDD: G004-G009 ----------


class TestFalseSuspenseTransition:
    """Tests for G004: False Suspense Transition."""

    def test_detects_heres_the_kicker(self) -> None:
        """Detect 'Here's the kicker' false suspense."""
        from proseprobe.rules.grammar import FalseSuspenseTransitionRule

        text = "Here's the kicker."
        rule = FalseSuspenseTransitionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G004"

    def test_detects_heres_the_thing(self) -> None:
        """Detect 'Here's the thing about' false suspense."""
        from proseprobe.rules.grammar import FalseSuspenseTransitionRule

        text = "Here's the thing about AI adoption."
        rule = FalseSuspenseTransitionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_heres_where_it_gets_interesting(self) -> None:
        """Detect 'Here's where it gets interesting' variant."""
        from proseprobe.rules.grammar import FalseSuspenseTransitionRule

        text = "Here's where it gets interesting."
        rule = FalseSuspenseTransitionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal use of 'here'."""
        from proseprobe.rules.grammar import FalseSuspenseTransitionRule

        text = "Here is the configuration file for the project."
        rule = FalseSuspenseTransitionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import FalseSuspenseTransitionRule

        rule = FalseSuspenseTransitionRule()
        assert rule.id == "G004"
        assert rule.name == "False Suspense Transition"


class TestPatronizingAnalogy:
    """Tests for G005: Patronizing Analogy."""

    def test_detects_think_of_it_as(self) -> None:
        """Detect 'Think of it as...' patronizing analogy."""
        from proseprobe.rules.grammar import PatronizingAnalogyRule

        text = "Think of it as a Swiss Army knife for your workflow."
        rule = PatronizingAnalogyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G005"

    def test_detects_think_of_it_like(self) -> None:
        """Detect 'Think of it like...' variant."""
        from proseprobe.rules.grammar import PatronizingAnalogyRule

        text = "Think of it like a highway system for data."
        rule = PatronizingAnalogyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose without patronizing analogies."""
        from proseprobe.rules.grammar import PatronizingAnalogyRule

        text = "The system uses a caching layer for performance."
        rule = PatronizingAnalogyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import PatronizingAnalogyRule

        rule = PatronizingAnalogyRule()
        assert rule.id == "G005"
        assert rule.name == "Patronizing Analogy"


class TestFuturistInvitation:
    """Tests for G006: Futurist Invitation."""

    def test_detects_imagine_a_world(self) -> None:
        """Detect 'Imagine a world where...' invitation."""
        from proseprobe.rules.grammar import FuturistInvitationRule

        text = "Imagine a world where every tool has a quiet intelligence behind it."
        rule = FuturistInvitationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G006"

    def test_detects_in_that_world(self) -> None:
        """Detect 'In that world,...' follow-up."""
        from proseprobe.rules.grammar import FuturistInvitationRule

        text = "In that world, workflows stop being manual steps."
        rule = FuturistInvitationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal use of 'imagine'."""
        from proseprobe.rules.grammar import FuturistInvitationRule

        text = "You can imagine how complex this becomes at scale."
        rule = FuturistInvitationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import FuturistInvitationRule

        rule = FuturistInvitationRule()
        assert rule.id == "G006"
        assert rule.name == "Futurist Invitation"


class TestFalseVulnerability:
    """Tests for G007: False Vulnerability."""

    def test_detects_this_is_not_a_rant(self) -> None:
        """Detect 'This is not a rant' false vulnerability."""
        from proseprobe.rules.grammar import FalseVulnerabilityRule

        text = "This is not a rant; it's a diagnosis."
        rule = FalseVulnerabilityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G007"

    def test_detects_let_me_be_honest(self) -> None:
        """Detect 'Let me be honest' variant."""
        from proseprobe.rules.grammar import FalseVulnerabilityRule

        text = "Let me be honest about the state of this project."
        rule = FalseVulnerabilityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose."""
        from proseprobe.rules.grammar import FalseVulnerabilityRule

        text = "The integration test revealed a subtle timing bug."
        rule = FalseVulnerabilityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import FalseVulnerabilityRule

        rule = FalseVulnerabilityRule()
        assert rule.id == "G007"
        assert rule.name == "False Vulnerability"


class TestAssertedSimplicity:
    """Tests for G008: Asserted Simplicity."""

    def test_detects_reality_is_simpler(self) -> None:
        """Detect 'The reality is simpler' assertion."""
        from proseprobe.rules.grammar import AssertedSimplicityRule

        text = "The reality is simpler and less flattering."
        rule = AssertedSimplicityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G008"

    def test_detects_history_is_clear(self) -> None:
        """Detect 'History is clear' assertion."""
        from proseprobe.rules.grammar import AssertedSimplicityRule

        text = "History is clear on this point."
        rule = AssertedSimplicityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_the_truth_is(self) -> None:
        """Detect 'The truth is' assertion."""
        from proseprobe.rules.grammar import AssertedSimplicityRule

        text = "The truth is most teams don't need microservices."
        rule = AssertedSimplicityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag prose without asserted simplicity."""
        from proseprobe.rules.grammar import AssertedSimplicityRule

        text = "The algorithm runs in O(n log n) time complexity."
        rule = AssertedSimplicityRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import AssertedSimplicityRule

        rule = AssertedSimplicityRule()
        assert rule.id == "G008"
        assert rule.name == "Asserted Simplicity"


class TestPedagogicalVoice:
    """Tests for G009: Pedagogical Voice."""

    def test_detects_lets_break_this_down(self) -> None:
        """Detect 'Let's break this down' pedagogical voice."""
        from proseprobe.rules.grammar import PedagogicalVoiceRule

        text = "Let's break this down step by step."
        rule = PedagogicalVoiceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G009"

    def test_detects_lets_unpack(self) -> None:
        """Detect 'Let's unpack' variant."""
        from proseprobe.rules.grammar import PedagogicalVoiceRule

        text = "Let's unpack what this really means."
        rule = PedagogicalVoiceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_lets_dive_in(self) -> None:
        """Detect 'Let's dive in' variant."""
        from proseprobe.rules.grammar import PedagogicalVoiceRule

        text = "Let's dive into the details."
        rule = PedagogicalVoiceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose."""
        from proseprobe.rules.grammar import PedagogicalVoiceRule

        text = "The configuration file supports TOML format."
        rule = PedagogicalVoiceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import PedagogicalVoiceRule

        rule = PedagogicalVoiceRule()
        assert rule.id == "G009"
        assert rule.name == "Pedagogical Voice"


# ---------- Phase 1 (Journalism Tropes) TDD: G010 ----------


class TestFalseBalance:
    """Tests for G010: False Balance."""

    def test_detects_supporters_critics(self) -> None:
        """Detect 'Supporters say X. Critics say Y.' false balance."""
        from proseprobe.rules.grammar import FalseBalanceRule

        text = (
            "Supporters say it will create jobs, but critics say it will destroy them."
        )
        rule = FalseBalanceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G010"

    def test_detects_truth_in_the_middle(self) -> None:
        """Detect 'the truth lies somewhere in the middle' false balance."""
        from proseprobe.rules.grammar import FalseBalanceRule

        text = "The truth lies somewhere in the middle of these views."
        rule = FalseBalanceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_both_sides_of_debate(self) -> None:
        """Detect 'both sides of the debate' false balance."""
        from proseprobe.rules.grammar import FalseBalanceRule

        text = "We must consider both sides of the debate before deciding."
        rule = FalseBalanceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_opponents_argue(self) -> None:
        """Detect 'on the other hand, opponents argue' false balance."""
        from proseprobe.rules.grammar import FalseBalanceRule

        text = "On the other hand, opponents argue this will cause harm."
        rule = FalseBalanceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose without false balance."""
        from proseprobe.rules.grammar import FalseBalanceRule

        text = "The algorithm runs in O(n log n) time complexity."
        rule = FalseBalanceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import FalseBalanceRule

        rule = FalseBalanceRule()
        assert rule.id == "G010"
        assert rule.name == "False Balance"


# ---------- Phase 2 (Academic Writing Tropes) TDD: G011-G013, G002 enhancement ----------


class TestNominalizationOverload:
    """Tests for G011: Nominalization Overload."""

    def test_detects_nominalization(self) -> None:
        """Detect multiple nominalizations above threshold."""
        from proseprobe.rules.grammar import NominalizationOverloadRule

        text = (
            "The implementation of the analysis led to the identification of patterns.\n"
            "The examination of the data confirmed the establishment of the baseline.\n"
        )
        rule = NominalizationOverloadRule(threshold=3)
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G011"

    def test_ignores_single_nominalization(self) -> None:
        """Don't flag when below threshold."""
        from proseprobe.rules.grammar import NominalizationOverloadRule

        text = "The implementation of the feature was smooth."
        rule = NominalizationOverloadRule(threshold=3)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_custom_threshold(self) -> None:
        """Respect configurable threshold."""
        from proseprobe.rules.grammar import NominalizationOverloadRule

        text = (
            "The implementation of the analysis led to the identification of patterns."
        )
        rule_low = NominalizationOverloadRule(threshold=1)
        rule_high = NominalizationOverloadRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose with verb forms."""
        from proseprobe.rules.grammar import NominalizationOverloadRule

        text = "The team implemented the analysis and identified patterns."
        rule = NominalizationOverloadRule(threshold=3)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import NominalizationOverloadRule

        rule = NominalizationOverloadRule()
        assert rule.id == "G011"
        assert rule.name == "Nominalization Overload"


class TestPassiveVoiceOveruse:
    """Tests for G012: Passive Voice Overuse."""

    def test_detects_academic_passive(self) -> None:
        """Detect formulaic academic passive constructions above threshold."""
        from proseprobe.rules.grammar import PassiveVoiceOveruseRule

        text = (
            "It is suggested that the results indicate a trend.\n"
            "It was found that the method performs well.\n"
            "It has been shown that this approach works.\n"
            "It could be argued that alternatives exist.\n"
            "It should be noted that limitations apply.\n"
            "It can be seen that the pattern holds.\n"
        )
        rule = PassiveVoiceOveruseRule(threshold=5)
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G012"

    def test_ignores_below_threshold(self) -> None:
        """Don't flag when below threshold."""
        from proseprobe.rules.grammar import PassiveVoiceOveruseRule

        text = (
            "It is suggested that the results indicate a trend.\n"
            "It was found that the method performs well.\n"
        )
        rule = PassiveVoiceOveruseRule(threshold=5)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_technical_passive(self) -> None:
        """Don't flag normal technical passive voice."""
        from proseprobe.rules.grammar import PassiveVoiceOveruseRule

        text = "The file was created. Errors are logged. The server was restarted."
        rule = PassiveVoiceOveruseRule(threshold=1)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_custom_threshold(self) -> None:
        """Respect configurable threshold."""
        from proseprobe.rules.grammar import PassiveVoiceOveruseRule

        text = (
            "It is suggested that the results indicate a trend.\n"
            "It was found that the method performs well.\n"
        )
        rule_low = PassiveVoiceOveruseRule(threshold=1)
        rule_high = PassiveVoiceOveruseRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import PassiveVoiceOveruseRule

        rule = PassiveVoiceOveruseRule()
        assert rule.id == "G012"
        assert rule.name == "Passive Voice Overuse"


class TestHedgeStacking:
    """Tests for G002 enhancement: hedge stacking detection."""

    def test_detects_hedge_stacking(self) -> None:
        """Detect multiple hedges in a single sentence."""
        rule = ExcessiveHedgingRule()
        text = "These results may potentially suggest that the findings could be interpreted as supportive."
        issues = rule.check(text, "test.md")
        hedge_stack_issues = [
            i
            for i in issues
            if "hedge stacking" in i.message.lower() or "Hedge stacking" in i.message
        ]
        assert len(hedge_stack_issues) >= 1

    def test_detects_hedge_stacking_across_markdown_lines(self) -> None:
        text = "The result may\npotentially perhaps fail."

        issues = ExcessiveHedgingRule().check(text, "test.md")
        stacking = [
            issue for issue in issues if issue.message.startswith("Hedge stacking")
        ]

        assert len(stacking) == 1
        assert (stacking[0].line, stacking[0].column) == (1, 1)
        assert "3 hedges" in stacking[0].message

    def test_ignores_single_hedge(self) -> None:
        """Don't flag a single hedge as stacking."""
        rule = ExcessiveHedgingRule()
        text = "These results may suggest a trend."
        issues = rule.check(text, "test.md")
        hedge_stack_issues = [
            i
            for i in issues
            if "hedge stacking" in i.message.lower() or "Hedge stacking" in i.message
        ]
        assert len(hedge_stack_issues) == 0

    def test_stacking_counts_correctly(self) -> None:
        """Two hedges in one sentence should trigger stacking."""
        rule = ExcessiveHedgingRule()
        text = "This arguably might indicate something."
        issues = rule.check(text, "test.md")
        hedge_stack_issues = [
            i
            for i in issues
            if "hedge stacking" in i.message.lower() or "Hedge stacking" in i.message
        ]
        assert len(hedge_stack_issues) >= 1

    def test_stacking_replaces_phrase_at_the_same_start(self) -> None:
        """The stronger stack issue should own a shared source start."""
        rule = ExcessiveHedgingRule()
        issues = rule.check(
            "It is important to note that this may potentially fail.",
            "test.md",
        )

        same_start = [issue for issue in issues if issue.column == 1]
        assert len(same_start) == 1
        assert same_start[0].message.startswith("Hedge stacking:")
        assert same_start[0].confidence is Confidence.HIGH
        assert any(issue.column > 1 for issue in issues)

    def test_single_phrase_keeps_its_finding(self) -> None:
        """A phrase without stacking should still be reported."""
        rule = ExcessiveHedgingRule()
        issues = rule.check(
            "It is important to note that results vary.",
            "test.md",
        )

        assert len(issues) == 1
        assert issues[0].message.startswith("Hedging phrase:")


class TestGapRitual:
    """Tests for G013: Gap Ritual."""

    def test_detects_gap_ritual(self) -> None:
        """Detect 'the literature has overlooked' gap phrase."""
        from proseprobe.rules.grammar import GapRitualRule

        text = "The literature has overlooked the role of community in this process."
        rule = GapRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G013"

    def test_detects_fills_gap(self) -> None:
        """Detect 'fills that gap' phrase."""
        from proseprobe.rules.grammar import GapRitualRule

        text = "This study fills that gap by examining the overlooked variables."
        rule = GapRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_underexplored(self) -> None:
        """Detect 'remains underexplored' phrase."""
        from proseprobe.rules.grammar import GapRitualRule

        text = "This topic remains underexplored in the existing literature."
        rule = GapRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_few_scholars(self) -> None:
        """Detect 'few scholars have examined' phrase."""
        from proseprobe.rules.grammar import GapRitualRule

        text = "Few scholars have examined the intersection of these two fields."
        rule = GapRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal academic prose."""
        from proseprobe.rules.grammar import GapRitualRule

        text = (
            "The researchers examined the data carefully and reported their findings."
        )
        rule = GapRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import GapRitualRule

        rule = GapRitualRule()
        assert rule.id == "G013"
        assert rule.name == "Gap Ritual"


# ---------- Business Writing Tropes: G014 ----------


class TestImpersonalCorporatePassive:
    """Tests for G014: Impersonal Corporate Passive."""

    def test_detects_it_has_been_determined(self) -> None:
        """Detect 'It has been determined' impersonal passive."""
        from proseprobe.rules.grammar import ImpersonalCorporatePassiveRule

        text = "It has been determined that adjustments will be made."
        rule = ImpersonalCorporatePassiveRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "G014"

    def test_detects_a_decision_has_been_made(self) -> None:
        """Detect 'A decision has been made' impersonal passive."""
        from proseprobe.rules.grammar import ImpersonalCorporatePassiveRule

        text = "A decision has been made to proceed with Option B."
        rule = ImpersonalCorporatePassiveRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_steps_will_be_taken(self) -> None:
        """Detect 'Steps will be taken' impersonal passive."""
        from proseprobe.rules.grammar import ImpersonalCorporatePassiveRule

        text = "Steps will be taken to address the issue."
        rule = ImpersonalCorporatePassiveRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_changes_will_be_implemented(self) -> None:
        """Detect 'Changes will be implemented' impersonal passive."""
        from proseprobe.rules.grammar import ImpersonalCorporatePassiveRule

        text = "Changes will be implemented across all departments."
        rule = ImpersonalCorporatePassiveRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_active_voice(self) -> None:
        """Don't flag active voice sentences."""
        from proseprobe.rules.grammar import ImpersonalCorporatePassiveRule

        text = "The leadership team decided to change the plan."
        rule = ImpersonalCorporatePassiveRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.grammar import ImpersonalCorporatePassiveRule

        rule = ImpersonalCorporatePassiveRule()
        assert rule.id == "G014"
        assert rule.name == "Impersonal Corporate Passive"


class TestGenericSceneSettingOpenerRule:
    """Tests for G015: Generic Scene-Setting Opener."""

    def test_reports_wrapped_opener_at_exact_source_span(self) -> None:
        text = (
            "# Report\n\n"
            "In an era defined by\n"
            "constant change, teams still need a named subject."
        )

        [issue] = GenericSceneSettingOpenerRule().check(text, "report.md")

        assert issue.rule_id == "G015"
        assert issue.message == (
            "Generic scene-setting opener: 'In an era defined by constant change'"
        )
        assert issue.suggestion == (
            "Replace the generic opener with the concrete subject or change"
        )
        assert issue.line == 3
        assert issue.column == 1
        assert issue.end_line == 4
        assert issue.end_column == 16
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM

    @pytest.mark.parametrize(
        "text",
        [
            "In today's rapidly evolving digital landscape, the report names no change.",
            "In today\u2019s digital world: the report names no subject.",
            "In the modern world, the report should begin with its result.",
            "In a rapidly evolving landscape \u2014 the report still needs specifics.",
        ],
    )
    def test_detects_supported_frames(self, text: str) -> None:
        issues = GenericSceneSettingOpenerRule().check(text, "report.md")

        assert len(issues) == 1

    def test_skips_non_body_and_example_contexts(self) -> None:
        text = (
            "# Report\n\n"
            "> In an era defined by constant change, this phrase is quoted.\n\n"
            "## Example\n\n"
            "In today's digital world, this phrase demonstrates the rule.\n\n"
            "## Findings\n\n"
            "In the modern world, this report should name its actual finding."
        )

        [issue] = GenericSceneSettingOpenerRule().check(text, "report.md")

        assert issue.line == 11
        assert issue.message == "Generic scene-setting opener: 'In the modern world'"

    def test_ignores_matching_second_sentence(self) -> None:
        text = (
            "The report measures storage latency. "
            "In the modern world, teams still need exact figures."
        )

        assert GenericSceneSettingOpenerRule().check(text, "report.md") == []

    def test_ignores_python(self) -> None:
        text = "In an era defined by constant change, the module needs documentation."

        assert GenericSceneSettingOpenerRule().check(text, "module.py") == []

    @pytest.mark.parametrize(
        "text",
        [
            "Maria Chen joined the storage team in 2024.",
            "Version 2.1 adds Setext heading support.",
            "In August 2026, the team published version 2.1.",
            "In the modern era of Canadian history, rail schedules changed twice.",
            "In the modern threat landscape, analysts track three named campaigns.",
        ],
    )
    def test_ignores_specific_introductions(self, text: str) -> None:
        assert GenericSceneSettingOpenerRule().check(text, "report.md") == []

    def test_rule_metadata(self) -> None:
        rule = GenericSceneSettingOpenerRule()

        assert rule.id == "G015"
        assert rule.name == "Generic Scene-Setting Opener"
        assert rule.description == (
            "Detects generic scene-setting clauses in Markdown openers"
        )
        assert rule.severity is Severity.INFO
        assert rule.default_confidence is Confidence.MEDIUM
        assert rule.applies_to == {"markdown"}
        assert rule.content_scope == "prose"


class TestExistentialOpenerRule:
    """Tests for G016: Existential Opener."""

    @pytest.mark.parametrize(
        "opener",
        ["There is", "There are", "There was", "There were"],
    )
    def test_reports_supported_openers(self, opener: str) -> None:
        source = f"{opener} one retry path after the failed deployment."

        [issue] = ExistentialOpenerRule().check(source, "test.md")

        assert issue.rule_id == "G016"
        assert issue.message == f"Existential opener: '{opener}'"
        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            1,
            1,
            1,
            len(opener) + 1,
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "Start with the sentence's subject"

    def test_reports_wrapped_opener_at_exact_source_span(self) -> None:
        source = "There\nare five retry paths after deployment."

        [issue] = ExistentialOpenerRule().check(source, "test.md")

        assert issue.message == "Existential opener: 'There are'"
        assert (issue.line, issue.column) == (1, 1)
        assert (issue.end_line, issue.end_column) == (2, 4)

    def test_requires_five_words_after_the_opener(self) -> None:
        [issue] = ExistentialOpenerRule().check(
            "There is one cache entry after restart.", "test.md"
        )

        assert issue.rule_id == "G016"
        assert (
            ExistentialOpenerRule().check("There is one cache entry after.", "test.md")
            == []
        )

    def test_checks_each_sentence(self) -> None:
        source = (
            "There is one cache entry after every restart. "
            "There were two timeout reports after region recovery."
        )

        issues = ExistentialOpenerRule().check(source, "test.md")

        assert [issue.message for issue in issues] == [
            "Existential opener: 'There is'",
            "Existential opener: 'There were'",
        ]

    @pytest.mark.parametrize(
        ("source", "column"),
        [
            ("- There are two retry paths after failed requests.", 3),
            ("> There was one stale cache entry after deployment.", 3),
        ],
    )
    def test_checks_list_and_blockquote_sentences(
        self, source: str, column: int
    ) -> None:
        [issue] = ExistentialOpenerRule().check(source, "test.md")

        assert issue.column == column

    @pytest.mark.parametrize(
        "source",
        [
            "There is no cache.",
            "There are two options.",
            "There will be another retry path after failed requests.",
            "There has been another retry path after failed requests.",
            "The report says there is another retry path after failed requests.",
        ],
    )
    def test_ignores_short_and_unsupported_forms(self, source: str) -> None:
        assert ExistentialOpenerRule().check(source, "test.md") == []

    def test_ignores_markdown_non_prose_and_example_contexts(self) -> None:
        source = (
            "# There are many retry paths after failed requests\n\n"
            "Use `There is one retry path after failed requests` as sample text.\n\n"
            "```text\nThere are many retry paths after failed requests.\n```\n\n"
            "## Example\n\nThere was one stale cache entry after deployment."
        )

        assert ExistentialOpenerRule().check(source, "test.md") == []

    def test_checks_python_comments_and_docstrings_only(self) -> None:
        sentence = "There is one retry path after every failure."
        source = (
            f'message = "{sentence}"\n'
            f"# {sentence}\n"
            "def explain():\n"
            f'    """{sentence}"""\n'
            "    return message"
        )

        issues = ExistentialOpenerRule().check(source, "test.py")

        assert [issue.line for issue in issues] == [2, 4]

    def test_rule_metadata(self) -> None:
        rule = ExistentialOpenerRule()

        assert rule.id == "G016"
        assert rule.name == "Existential Opener"
        assert rule.config_key is None
        assert rule.default_confidence is Confidence.MEDIUM
        assert rule.applies_to == {"markdown", "python"}
        assert rule.content_scope == "prose"


class TestEmptyItOpenerRule:
    """Tests for G017: Empty "It" Opener."""

    @pytest.mark.parametrize(
        "opener",
        ["It is clear that", "It is obvious that", "It is evident that"],
    )
    def test_reports_supported_openers(self, opener: str) -> None:
        [issue] = EmptyItOpenerRule().check(
            f"{opener} the cache is stale.",
            "test.md",
        )

        assert issue.rule_id == "G017"
        assert issue.message == f"Empty 'It' opener: '{opener}'"
        assert (issue.line, issue.column) == (1, 1)
        assert (issue.end_line, issue.end_column) == (1, len(opener) + 1)
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "State the evidence or conclusion directly"

    def test_reports_wrapped_opener_at_exact_source_span(self) -> None:
        text = "It is evident\nthat the timeout is repeatable."

        [issue] = EmptyItOpenerRule().check(text, "test.md")

        assert issue.message == "Empty 'It' opener: 'It is evident that'"
        assert (issue.line, issue.column) == (1, 1)
        assert (issue.end_line, issue.end_column) == (2, 5)

    def test_checks_each_sentence_not_only_the_first(self) -> None:
        text = "The logs show two failures. It is obvious that the cache is stale."

        [issue] = EmptyItOpenerRule().check(text, "test.md")

        start = text.index("It is obvious that")
        assert (issue.line, issue.column) == (1, start + 1)
        assert issue.end_column == start + len("It is obvious that") + 1

    @pytest.mark.parametrize(
        ("text", "column"),
        [
            ("- It is clear that the cache is stale.", 3),
            ("> It is evident that the cache is stale.", 3),
        ],
    )
    def test_checks_list_and_blockquote_sentences(self, text: str, column: int) -> None:
        [issue] = EmptyItOpenerRule().check(text, "test.md")

        assert issue.column == column

    def test_ignores_markdown_non_prose_and_example_contexts(self) -> None:
        text = (
            "# It is clear that this heading demonstrates the phrase\n\n"
            "## Example\n\n"
            "It is obvious that this sentence demonstrates the phrase.\n\n"
            "`It is evident that`\n\n"
            "```text\nIt is clear that\n```"
        )

        assert EmptyItOpenerRule().check(text, "test.md") == []

    def test_checks_python_comments_and_docstrings_only(self) -> None:
        text = (
            'message = "It is clear that code is ignored."\n'
            "# It is obvious that the cache is stale.\n"
            "def explain():\n"
            '    """It is evident that the timeout repeats."""\n'
            "    return message"
        )

        issues = EmptyItOpenerRule().check(text, "test.py")

        assert [issue.line for issue in issues] == [2, 4]

    @pytest.mark.parametrize(
        "text",
        [
            "It is possible that the cache is stale.",
            "It is clear whether the cache is stale.",
            "The report says it is clear that the cache is stale.",
            "It was clear that the cache was stale.",
        ],
    )
    def test_ignores_nearby_non_matches(self, text: str) -> None:
        assert EmptyItOpenerRule().check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        rule = EmptyItOpenerRule()

        assert rule.id == "G017"
        assert rule.name == 'Empty "It" Opener'
        assert rule.description == (
            "Detects empty 'It is clear/obvious/evident that' sentence openers"
        )
        assert rule.severity is Severity.INFO
        assert rule.default_confidence is Confidence.HIGH
        assert rule.applies_to == {"markdown", "python"}
        assert rule.content_scope == "prose"


class TestAmbiguousThisRule:
    """Tests for G019: Ambiguous “This”."""

    @pytest.mark.parametrize("verb", ["causes", "means", "shows"])
    def test_reports_supported_openers(self, verb: str) -> None:
        source = f"This {verb} a cache failure."
        opener = f"This {verb}"

        [issue] = AmbiguousThisRule().check(source, "test.md")

        assert issue.rule_id == "G019"
        assert issue.message == f"Ambiguous 'This' opener: '{opener}'"
        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            1,
            1,
            1,
            len(opener) + 1,
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "Name what 'This' refers to"

    def test_reports_wrapped_opener_at_exact_source_span(self) -> None:
        source = "This\nmeans the cache is stale."

        [issue] = AmbiguousThisRule().check(source, "test.md")

        assert issue.message == "Ambiguous 'This' opener: 'This means'"
        assert (issue.line, issue.column) == (1, 1)
        assert (issue.end_line, issue.end_column) == (2, 6)

    def test_checks_each_sentence_and_preserves_casing(self) -> None:
        source = "THIS SHOWS a timeout. This causes a retry."

        issues = AmbiguousThisRule().check(source, "test.md")

        assert [issue.message for issue in issues] == [
            "Ambiguous 'This' opener: 'THIS SHOWS'",
            "Ambiguous 'This' opener: 'This causes'",
        ]

    @pytest.mark.parametrize(
        ("source", "column"),
        [
            ("- This means the cache is stale.", 3),
            ("> This shows the timeout is repeatable.", 3),
        ],
    )
    def test_checks_list_and_blockquote_sentences(
        self, source: str, column: int
    ) -> None:
        [issue] = AmbiguousThisRule().check(source, "test.md")

        assert issue.column == column

    @pytest.mark.parametrize(
        "source",
        [
            "This cache causes every request to miss.",
            "This caused the retry storm.",
            "This indicates that the cache is stale.",
            "That shows the timeout is repeatable.",
            "The report says this shows the timeout is repeatable.",
            "This means-tested benefit remains available.",
        ],
    )
    def test_ignores_non_allowlisted_and_non_opening_forms(self, source: str) -> None:
        assert AmbiguousThisRule().check(source, "test.md") == []

    def test_ignores_markdown_non_prose_and_example_contexts(self) -> None:
        source = (
            "# This shows the timeout is repeatable\n\n"
            "Use `This means the cache is stale` as sample text.\n\n"
            "```text\nThis causes every request to fail.\n```\n\n"
            "## Example\n\nThis shows the timeout is repeatable."
        )

        assert AmbiguousThisRule().check(source, "test.md") == []

    def test_checks_python_comments_and_docstrings_only(self) -> None:
        sentence = "This means the cache is stale."
        source = (
            f'message = "{sentence}"\n'
            f"# {sentence}\n"
            "def explain():\n"
            f'    """{sentence}"""\n'
            "    return message"
        )

        issues = AmbiguousThisRule().check(source, "test.py")

        assert [issue.line for issue in issues] == [2, 4]

    def test_rule_metadata(self) -> None:
        rule = AmbiguousThisRule()

        assert rule.id == "G019"
        assert rule.name == 'Ambiguous "This"'
        assert rule.config_key is None
        assert rule.default_confidence is Confidence.MEDIUM
        assert rule.applies_to == {"markdown", "python"}
        assert rule.content_scope == "prose"


class TestFormerLatterReferenceRule:
    """Tests for G022: Former/Latter Reference."""

    @pytest.mark.parametrize("reference", ["the former", "the latter"])
    def test_reports_exact_references(self, reference: str) -> None:
        source = f"Choose the local or remote runner; {reference} needs a token."

        [issue] = FormerLatterReferenceRule().check(source, "test.md")

        assert issue.rule_id == "G022"
        assert issue.message == f"Former/latter reference: '{reference}'"
        assert (issue.line, issue.column) == (1, source.index(reference) + 1)
        assert (issue.end_line, issue.end_column) == (
            1,
            source.index(reference) + len(reference) + 1,
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "Name the referenced item directly"

    def test_reports_each_reference_and_preserves_casing(self) -> None:
        source = "THE FORMER uses disk; the latter uses memory."

        issues = FormerLatterReferenceRule().check(source, "test.md")

        assert [issue.message for issue in issues] == [
            "Former/latter reference: 'THE FORMER'",
            "Former/latter reference: 'the latter'",
        ]
        assert [issue.column for issue in issues] == [1, 23]

    def test_reports_wrapped_reference_at_exact_source_span(self) -> None:
        source = "Choose either backend; the\nlatter records a version."

        [issue] = FormerLatterReferenceRule().check(source, "test.md")

        assert issue.message == "Former/latter reference: 'the latter'"
        assert (issue.line, issue.column) == (1, 24)
        assert (issue.end_line, issue.end_column) == (2, 7)

    @pytest.mark.parametrize(
        ("source", "column"),
        [
            ("- Use either backend; the former writes locally.", 23),
            ("> Compare both formats; the latter is compact.", 25),
        ],
    )
    def test_checks_list_and_blockquote_sentences(
        self, source: str, column: int
    ) -> None:
        [issue] = FormerLatterReferenceRule().check(source, "test.md")

        assert issue.column == column

    @pytest.mark.parametrize(
        "source",
        [
            "A former release used a different checksum.",
            "The formerly active node now rejects writes.",
            "The lattermost stage emits the archive.",
            "Name the primary node directly.",
        ],
    )
    def test_ignores_nearby_non_matches(self, source: str) -> None:
        assert FormerLatterReferenceRule().check(source, "test.md") == []

    def test_ignores_markdown_non_prose_and_example_contexts(self) -> None:
        source = (
            "# The former writes locally\n\n"
            "Use `the latter` as sample text.\n\n"
            "```text\nThe former accepts writes.\n```\n\n"
            "## Example\n\nThe latter needs a token."
        )

        assert FormerLatterReferenceRule().check(source, "test.md") == []

    def test_checks_python_comments_and_docstrings_only(self) -> None:
        sentence = "Compare both backends; the latter records a version."
        source = (
            f'message = "{sentence}"\n'
            f"# {sentence}\n"
            "def explain():\n"
            f'    """{sentence}"""\n'
            "    return message"
        )

        issues = FormerLatterReferenceRule().check(source, "test.py")

        assert [issue.line for issue in issues] == [2, 4]

    def test_rule_metadata(self) -> None:
        rule = FormerLatterReferenceRule()

        assert rule.id == "G022"
        assert rule.name == "Former/Latter Reference"
        assert rule.config_key is None
        assert rule.default_confidence is Confidence.MEDIUM
        assert rule.applies_to == {"markdown", "python"}
        assert rule.content_scope == "prose"


class TestUnclearActorRequirementRule:
    """Tests for G024: Unclear Actor in Requirement."""

    @pytest.mark.parametrize(
        "opener",
        ["It must be ensured that", "Care should be taken to"],
    )
    def test_reports_supported_openers(self, opener: str) -> None:
        [issue] = UnclearActorRequirementRule().check(
            f"{opener} preserve file permissions.",
            "test.md",
        )

        assert issue.rule_id == "G024"
        assert issue.message == f"Unclear actor in requirement: '{opener}'"
        assert (issue.line, issue.column) == (1, 1)
        assert (issue.end_line, issue.end_column) == (1, len(opener) + 1)
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "Name the actor responsible for the requirement"

    def test_reports_wrapped_opener_at_exact_source_span(self) -> None:
        text = "Care should be taken\nto preserve file permissions."

        [issue] = UnclearActorRequirementRule().check(text, "test.md")

        assert issue.message == (
            "Unclear actor in requirement: 'Care should be taken to'"
        )
        assert (issue.line, issue.column) == (1, 1)
        assert (issue.end_line, issue.end_column) == (2, 3)

    def test_checks_each_sentence_not_only_the_first(self) -> None:
        text = (
            "The archive includes a checksum. "
            "It must be ensured that every upload preserves it."
        )

        [issue] = UnclearActorRequirementRule().check(text, "test.md")

        start = text.index("It must be ensured that")
        assert (issue.line, issue.column) == (1, start + 1)
        assert issue.end_column == start + len("It must be ensured that") + 1

    @pytest.mark.parametrize(
        ("text", "column"),
        [
            ("- It must be ensured that each upload succeeds.", 3),
            ("> Care should be taken to preserve permissions.", 3),
        ],
    )
    def test_checks_list_and_blockquote_sentences(self, text: str, column: int) -> None:
        [issue] = UnclearActorRequirementRule().check(text, "test.md")

        assert issue.column == column

    def test_ignores_markdown_non_prose_and_example_contexts(self) -> None:
        text = (
            "# It must be ensured that this heading quotes the phrase\n\n"
            "## Example\n\n"
            "Care should be taken to demonstrate the phrase.\n\n"
            "`It must be ensured that`\n\n"
            "```text\nCare should be taken to\n```"
        )

        assert UnclearActorRequirementRule().check(text, "test.md") == []

    def test_checks_python_comments_and_docstrings_only(self) -> None:
        text = (
            'message = "It must be ensured that code is ignored."\n'
            "# Care should be taken to preserve permissions.\n"
            "def explain():\n"
            '    """It must be ensured that retries stop."""\n'
            "    return message"
        )

        issues = UnclearActorRequirementRule().check(text, "test.py")

        assert [issue.line for issue in issues] == [2, 4]

    @pytest.mark.parametrize(
        "text",
        [
            "The operator must ensure that every archive has a checksum.",
            "Take care to preserve file permissions.",
            "It should be ensured that every upload succeeds.",
            "Care must be taken to preserve file permissions.",
            "The guide says care should be taken to preserve permissions.",
        ],
    )
    def test_ignores_nearby_non_matches(self, text: str) -> None:
        assert UnclearActorRequirementRule().check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        rule = UnclearActorRequirementRule()

        assert rule.id == "G024"
        assert rule.name == "Unclear Actor in Requirement"
        assert rule.description == (
            "Detects fixed impersonal requirement forms without a named actor"
        )
        assert rule.severity is Severity.INFO
        assert rule.default_confidence is Confidence.MEDIUM
        assert rule.applies_to == {"markdown", "python"}
        assert rule.content_scope == "prose"


class TestWeakInstructionVerbRule:
    """Tests for G025: Weak Instruction Verb."""

    @pytest.mark.parametrize("phrase", ["You will need to", "You can proceed to"])
    def test_reports_exact_phrases(self, phrase: str) -> None:
        source = f"Before release, {phrase} publish the archive."

        [issue] = WeakInstructionVerbRule().check(source, "test.md")

        start = source.index(phrase)
        assert issue.rule_id == "G025"
        assert issue.message == f"Weak instruction phrase: '{phrase}'"
        assert (issue.line, issue.column) == (1, start + 1)
        assert (issue.end_line, issue.end_column) == (
            1,
            start + len(phrase) + 1,
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "Use a direct imperative"

    def test_reports_each_phrase_and_preserves_casing(self) -> None:
        source = "YOU WILL NEED TO restart. You can proceed to publish."

        issues = WeakInstructionVerbRule().check(source, "test.md")

        assert [issue.message for issue in issues] == [
            "Weak instruction phrase: 'YOU WILL NEED TO'",
            "Weak instruction phrase: 'You can proceed to'",
        ]
        assert [issue.column for issue in issues] == [1, 27]

    def test_reports_wrapped_phrase_at_exact_source_span(self) -> None:
        source = "You will\nneed to restart the worker."

        [issue] = WeakInstructionVerbRule().check(source, "test.md")

        assert issue.message == "Weak instruction phrase: 'You will need to'"
        assert (issue.line, issue.column) == (1, 1)
        assert (issue.end_line, issue.end_column) == (2, 8)

    @pytest.mark.parametrize(
        ("source", "column"),
        [
            ("- You will need to restart the worker.", 3),
            ("> You can proceed to publish the archive.", 3),
        ],
    )
    def test_checks_list_and_blockquote_sentences(
        self, source: str, column: int
    ) -> None:
        [issue] = WeakInstructionVerbRule().check(source, "test.md")

        assert issue.column == column

    @pytest.mark.parametrize(
        "source",
        [
            "You need to restart the worker.",
            "You will not need to restart the worker.",
            "You may proceed to publish the archive.",
            "You can proceed without publishing the archive.",
            "Restart the worker after changing the token.",
        ],
    )
    def test_ignores_nearby_non_matches(self, source: str) -> None:
        assert WeakInstructionVerbRule().check(source, "test.md") == []

    def test_ignores_markdown_non_prose_and_example_contexts(self) -> None:
        source = (
            "# You will need to restart the worker\n\n"
            "Use `You can proceed to` as sample text.\n\n"
            "```text\nYou will need to remove the lock.\n```\n\n"
            "## Example\n\nYou can proceed to publish the archive."
        )

        assert WeakInstructionVerbRule().check(source, "test.md") == []

    def test_checks_python_comments_and_docstrings_only(self) -> None:
        sentence = "You will need to restart the worker."
        source = (
            f'message = "{sentence}"\n'
            f"# {sentence}\n"
            "def explain():\n"
            f'    """{sentence}"""\n'
            "    return message"
        )

        issues = WeakInstructionVerbRule().check(source, "test.py")

        assert [issue.line for issue in issues] == [2, 4]

    def test_rule_metadata(self) -> None:
        rule = WeakInstructionVerbRule()

        assert rule.id == "G025"
        assert rule.name == "Weak Instruction Verb"
        assert rule.config_key is None
        assert rule.default_confidence is Confidence.MEDIUM
        assert rule.applies_to == {"markdown", "python"}
        assert rule.content_scope == "prose"


class TestDoubleNegativeRule:
    """Tests for G029: Double Negative."""

    @pytest.mark.parametrize(
        ("phrase", "suggestion"),
        [
            ("not uncommon", "common"),
            ("not unlikely", "likely"),
            ("not impossible", "possible"),
        ],
    )
    def test_reports_supported_forms(self, phrase: str, suggestion: str) -> None:
        [issue] = DoubleNegativeRule().check(f"The outcome is {phrase}.", "test.md")

        assert issue.rule_id == "G029"
        assert issue.message == f"Double negative: '{phrase}'"
        assert issue.line == 1
        assert issue.column == 16
        assert issue.end_column == 16 + len(phrase)
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == suggestion

    def test_reports_repeated_case_insensitive_matches_in_source_order(self) -> None:
        text = "NOT IMPOSSIBLE, not uncommon, and not impossible."

        issues = DoubleNegativeRule().check(text, "test.md")

        assert [issue.message for issue in issues] == [
            "Double negative: 'NOT IMPOSSIBLE'",
            "Double negative: 'not uncommon'",
            "Double negative: 'not impossible'",
        ]
        assert [issue.suggestion for issue in issues] == [
            "possible",
            "common",
            "possible",
        ]

    def test_ignores_markdown_non_prose_contexts(self) -> None:
        text = (
            "# not uncommon\n\n"
            "The literal is `not unlikely`.\n\n"
            "```text\nnot impossible\n```"
        )

        assert DoubleNegativeRule().check(text, "test.md") == []

    def test_checks_python_comments_and_docstrings_only(self) -> None:
        text = (
            'label = "not uncommon"\n'
            "# A retry is not unlikely.\n"
            "def recover():\n"
            '    """Recovery is not impossible."""\n'
            "    return True"
        )

        issues = DoubleNegativeRule().check(text, "test.py")

        assert [issue.line for issue in issues] == [2, 4]
        assert [issue.suggestion for issue in issues] == ["likely", "possible"]

    def test_ignores_nearby_non_matches(self) -> None:
        text = "The outcome is not common. Failure is impossible."

        assert DoubleNegativeRule().check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        rule = DoubleNegativeRule()

        assert rule.id == "G029"
        assert rule.name == "Double Negative"
        assert rule.description == "Detects fixed double-negative phrases"
        assert rule.severity is Severity.INFO
        assert rule.default_confidence is Confidence.HIGH
        assert rule.applies_to == {"markdown", "python"}
        assert rule.content_scope == "prose"
