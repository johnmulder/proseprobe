"""Tests for vocabulary rules (V001-V005)."""

import pytest

from slop_lint.config import Config
from slop_lint.rules import get_all_rules
from slop_lint.rules.base import Confidence, Rule, Severity
from slop_lint.rules.vocab import (
    AIVocabularyRule,
    CollaborativePhrasesRule,
    KnowledgeCutoffRule,
    PromotionalLanguageRule,
    TrendOverclaimRule,
    WeaselWordsRule,
)


@pytest.mark.parametrize(
    ("rule", "supported", "unsupported"),
    [
        (
            WeaselWordsRule(),
            (
                "Experts say repairs are needed. Engineers Mina Ortiz and "
                "Paul Chen signed the report on July 18."
            ),
            "Experts say repairs are needed.",
        ),
        (
            TrendOverclaimRule(),
            (
                "A growing number of trips use the line: the share rose "
                "from 31.2% to 34.8%."
            ),
            "A growing number of trips use the line.",
        ),
    ],
)
def test_claim_evidence_downgrades_confidence(
    rule: Rule,
    supported: str,
    unsupported: str,
) -> None:
    [supported_issue] = rule.check(supported, "report.md")
    [unsupported_issue] = rule.check(unsupported, "report.md")

    assert supported_issue.confidence is Confidence.LOW
    assert unsupported_issue.confidence is Confidence.MEDIUM


class TestAIVocabularyRule:
    """Tests for V001: Overused Vocabulary."""

    @pytest.fixture
    def rule(self) -> AIVocabularyRule:
        return AIVocabularyRule()

    def test_detects_delve(self, rule: AIVocabularyRule) -> None:
        content = "This article delves into the topic."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert issues[0].rule_id == "V001"
        assert "delves" in issues[0].message.lower()
        assert issues[0].suggestion == "explore"

    def test_detects_multiple_words(self, rule: AIVocabularyRule) -> None:
        content = "The tapestry of modern development is multifaceted."
        issues = rule.check(content, "test.md")

        assert len(issues) >= 2
        words_found = {i.message.split("'")[1].lower() for i in issues}
        assert "tapestry" in words_found
        assert "multifaceted" in words_found

    def test_ignores_clean_content(self, rule: AIVocabularyRule) -> None:
        content = "This is a simple document about programming."
        issues = rule.check(content, "test.md")

        assert len(issues) == 0

    def test_respects_allowed_vocabulary(self) -> None:
        rule = AIVocabularyRule(allowed={"delve"})
        content = "This article delves into the topic."
        issues = rule.check(content, "test.md")

        assert len(issues) == 0

    def test_flags_additional_vocabulary(self) -> None:
        rule = AIVocabularyRule(additional={"foobar"})
        content = "The foobar feature is enabled."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert "foobar" in issues[0].message.lower()

    def test_ignores_code_fences_in_markdown(self) -> None:
        rule = AIVocabularyRule()
        content = "```python\n# delve\n```\nThis delves into topics."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1

    def test_ignores_inline_code_in_markdown(self) -> None:
        rule = AIVocabularyRule()
        content = "Use `delve` sparingly in docs."
        issues = rule.check(content, "test.md")

        assert len(issues) == 0

    def test_severity_override_from_config(self) -> None:
        config = Config(severity_overrides={"V001": "error"})
        rules = get_all_rules(config)
        rule = next(r for r in rules if r.id == "V001")
        assert rule.severity == Severity.ERROR

    def test_tier1_word_has_high_confidence(self, rule: AIVocabularyRule) -> None:
        content = "Let's delve into this topic."
        issues = rule.check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.HIGH

    @pytest.mark.parametrize(
        ("text", "confidence", "suggestion"),
        [
            ("leveraging", Confidence.HIGH, "using"),
            ("leverage", Confidence.MEDIUM, "use"),
            ("leverages", Confidence.MEDIUM, "use"),
            ("leveraged", Confidence.MEDIUM, "use"),
        ],
    )
    def test_leverage_forms_have_one_canonical_finding(
        self,
        rule: AIVocabularyRule,
        text: str,
        confidence: Confidence,
        suggestion: str,
    ) -> None:
        """Each leverage form should have one confidence and suggestion owner."""
        issues = rule.check(text, "test.md")

        assert len(issues) == 1
        assert issues[0].confidence is confidence
        assert issues[0].suggestion == suggestion

    def test_tier2_word_has_medium_confidence(self, rule: AIVocabularyRule) -> None:
        content = "This is a crucial decision."
        issues = rule.check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.MEDIUM

    def test_tier3_word_has_low_confidence(self, rule: AIVocabularyRule) -> None:
        content = "This is a notable achievement."
        issues = rule.check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.LOW

    def test_example_heading_downgrades_confidence(self) -> None:
        rule = AIVocabularyRule()
        content = "## Example (bad)\n\nThis article delves into the topic."
        issues = rule.check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.LOW

    def test_allowed_phrases_skip_matching_line(self) -> None:
        rule = AIVocabularyRule(allowed_phrases={"all notable changes"})
        content = "All notable changes to this project."
        issues = rule.check(content, "test.md")
        assert len(issues) == 0


class TestCollaborativePhrasesRule:
    """Tests for V002: Collaborative Phrases."""

    @pytest.fixture
    def rule(self) -> CollaborativePhrasesRule:
        return CollaborativePhrasesRule()

    def test_detects_i_hope_this_helps(self, rule: CollaborativePhrasesRule) -> None:
        content = "Here's the solution. I hope this helps!"
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert "I hope this helps" in issues[0].message

    def test_detects_let_me_know(self, rule: CollaborativePhrasesRule) -> None:
        content = "Let me know if you need more information."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1


class TestKnowledgeCutoffRule:
    """Tests for V003: Knowledge Cutoff."""

    @pytest.fixture
    def rule(self) -> KnowledgeCutoffRule:
        return KnowledgeCutoffRule()

    def test_detects_knowledge_cutoff(self, rule: KnowledgeCutoffRule) -> None:
        content = "As of my last update, this information is accurate."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert issues[0].rule_id == "V003"


class TestPromotionalLanguageRule:
    """Tests for V004: Promotional Language."""

    @pytest.fixture
    def rule(self) -> PromotionalLanguageRule:
        return PromotionalLanguageRule()

    def test_detects_promotional_phrases(self, rule: PromotionalLanguageRule) -> None:
        content = "This world-class solution boasts cutting-edge features."
        issues = rule.check(content, "test.md")

        assert len(issues) >= 1


class TestWeaselWordsRule:
    """Tests for V005: Weasel Words."""

    @pytest.fixture
    def rule(self) -> WeaselWordsRule:
        return WeaselWordsRule()

    def test_detects_weasel_phrases(self, rule: WeaselWordsRule) -> None:
        content = "Experts say this approach is effective."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert issues[0].rule_id == "V005"


# ---------- Phase 10 TDD: V006-V007 ----------


class TestGrandioseStakes:
    """Tests for V006: Grandiose Stakes."""

    def test_detects_fundamentally_reshape(self) -> None:
        """Detect 'fundamentally reshape' grandiose claim."""
        from slop_lint.rules.vocab import GrandioseStakesRule

        content = "This will fundamentally reshape how we think about everything."
        issues = GrandioseStakesRule().check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "V006"

    def test_detects_define_the_next_era(self) -> None:
        """Detect 'define the next era' inflation."""
        from slop_lint.rules.vocab import GrandioseStakesRule

        content = "This technology will define the next era of computing."
        issues = GrandioseStakesRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_detects_change_everything(self) -> None:
        """Detect 'will change everything' inflation."""
        from slop_lint.rules.vocab import GrandioseStakesRule

        content = "AI will change everything about how we work."
        issues = GrandioseStakesRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal technical prose."""
        from slop_lint.rules.vocab import GrandioseStakesRule

        content = "The library provides a simple API for HTTP requests."
        issues = GrandioseStakesRule().check(content, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.vocab import GrandioseStakesRule

        rule = GrandioseStakesRule()
        assert rule.id == "V006"
        assert rule.name == "Grandiose Stakes"


class TestInventedConceptLabels:
    """Tests for V007: Invented Concept Labels."""

    def test_detects_multiple_labels(self) -> None:
        """Detect 2+ compound analytical labels in same document."""
        from slop_lint.rules.vocab import InventedConceptLabelsRule

        content = (
            "The supervision paradox makes management harder.\n"
            "Combined with the acceleration trap, teams burn out.\n"
            "Workload creep compounds the problem."
        )
        issues = InventedConceptLabelsRule().check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "V007"

    def test_ignores_single_label(self) -> None:
        """Don't flag a single compound label."""
        from slop_lint.rules.vocab import InventedConceptLabelsRule

        content = "The productivity paradox has been studied extensively."
        issues = InventedConceptLabelsRule().check(content, "test.md")
        assert len(issues) == 0

    def test_ignores_normal_prose(self) -> None:
        """Don't flag prose without compound labels."""
        from slop_lint.rules.vocab import InventedConceptLabelsRule

        content = "The system handles errors gracefully and logs all events."
        issues = InventedConceptLabelsRule().check(content, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.vocab import InventedConceptLabelsRule

        rule = InventedConceptLabelsRule()
        assert rule.id == "V007"
        assert rule.name == "Invented Concept Labels"


# ---------- Phase 1 (Journalism Tropes) TDD: V008 ----------


class TestTrendOverclaim:
    """Tests for V008: Trend Overclaim."""

    def test_detects_more_and_more_people(self) -> None:
        """Detect 'more and more people' trend overclaim."""
        from slop_lint.rules.vocab import TrendOverclaimRule

        content = "More and more people are adopting this framework."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "V008"

    def test_detects_growing_number(self) -> None:
        """Detect 'a growing number of' trend overclaim."""
        from slop_lint.rules.vocab import TrendOverclaimRule

        content = "A growing number of developers prefer TypeScript."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_detects_everyone_is_talking(self) -> None:
        """Detect 'everyone is talking about' trend overclaim."""
        from slop_lint.rules.vocab import TrendOverclaimRule

        content = "Everyone is talking about this new approach."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_detects_increasingly_popular(self) -> None:
        """Detect 'increasingly popular' trend overclaim."""
        from slop_lint.rules.vocab import TrendOverclaimRule

        content = "Rust is increasingly popular among systems programmers."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal technical prose."""
        from slop_lint.rules.vocab import TrendOverclaimRule

        content = "The library provides a simple API for HTTP requests."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.vocab import TrendOverclaimRule

        rule = TrendOverclaimRule()
        assert rule.id == "V008"
        assert rule.name == "Trend Overclaim"


class TestAcademicVocabularyExpansions:
    """Tests for academic writing vocabulary additions to V001."""

    def test_detects_problematize(self) -> None:
        """Detect TIER1 academic jargon 'problematize'."""
        rule = AIVocabularyRule()
        issues = rule.check("We must problematize these assumptions.", "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.HIGH

    def test_detects_facilitate(self) -> None:
        """Detect TIER2 Latinate vocabulary 'facilitate'."""
        rule = AIVocabularyRule()
        issues = rule.check("This will facilitate better outcomes.", "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.MEDIUM

    def test_detects_positionality(self) -> None:
        """Detect TIER2 concept inflation 'positionality'."""
        rule = AIVocabularyRule()
        issues = rule.check("The researcher's positionality matters.", "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.MEDIUM

    def test_detects_assemblage(self) -> None:
        """Detect TIER2 concept inflation 'assemblage'."""
        rule = AIVocabularyRule()
        issues = rule.check("This assemblage of factors is complex.", "test.md")
        assert len(issues) >= 1

    def test_detects_interrogate_academic_usage(self) -> None:
        """Detect 'interrogate' in academic context."""
        rule = AIVocabularyRule()
        issues = rule.check("We must interrogate the dominant assumptions.", "test.md")
        interrogate_issues = [i for i in issues if "interrogat" in i.message.lower()]
        assert len(interrogate_issues) >= 1

    def test_ignores_interrogate_non_academic(self) -> None:
        """Don't flag 'interrogate' in non-academic context."""
        rule = AIVocabularyRule()
        issues = rule.check("The detective will interrogate the suspect.", "test.md")
        interrogate_issues = [i for i in issues if "interrogat" in i.message.lower()]
        assert len(interrogate_issues) == 0

    def test_suggestions_for_new_words(self) -> None:
        """New words should have suggestions."""
        from slop_lint.data.vocabulary import VOCABULARY_SUGGESTIONS

        new_words = [
            "problematize",
            "destabilize",
            "facilitate",
            "demonstrate",
            "regarding",
            "implement",
            "positionality",
            "praxis",
        ]
        for word in new_words:
            assert word in VOCABULARY_SUGGESTIONS, f"Missing suggestion for '{word}'"


class TestBusinessJargonVocabulary:
    """Tests for business jargon additions to V001."""

    def test_detects_synergy(self) -> None:
        """Detect TIER2 business jargon 'synergy'."""
        rule = AIVocabularyRule()
        issues = rule.check("We will leverage cross-functional synergy.", "test.md")
        synergy_issues = [i for i in issues if "synerg" in i.message.lower()]
        assert len(synergy_issues) >= 1

    def test_detects_value_add(self) -> None:
        """Detect 'value-add' business jargon."""
        rule = AIVocabularyRule()
        issues = rule.check("This provides real value-add for our clients.", "test.md")
        value_issues = [i for i in issues if "value-add" in i.message.lower()]
        assert len(value_issues) >= 1

    def test_detects_bandwidth(self) -> None:
        """Detect figurative 'bandwidth' business jargon."""
        rule = AIVocabularyRule()
        issues = rule.check("I don't have the bandwidth for that right now.", "test.md")
        bw_issues = [i for i in issues if "bandwidth" in i.message.lower()]
        assert len(bw_issues) >= 1

    def test_detects_incentivize(self) -> None:
        """Detect 'incentivize' inflated verb."""
        rule = AIVocabularyRule()
        issues = rule.check("We need to incentivize early adoption.", "test.md")
        inc_issues = [i for i in issues if "incentiviz" in i.message.lower()]
        assert len(inc_issues) >= 1

    def test_detects_ideate(self) -> None:
        """Detect 'ideate' inflated verb."""
        rule = AIVocabularyRule()
        issues = rule.check("The team will ideate on new product concepts.", "test.md")
        id_issues = [i for i in issues if "ideat" in i.message.lower()]
        assert len(id_issues) >= 1

    def test_detects_socialize_business_context(self) -> None:
        """Detect 'socialize' in business context."""
        rule = AIVocabularyRule()
        issues = rule.check(
            "We need to socialize the plan with stakeholders.", "test.md"
        )
        soc_issues = [i for i in issues if "socializ" in i.message.lower()]
        assert len(soc_issues) >= 1

    def test_ignores_socialize_normal_context(self) -> None:
        """Don't flag 'socialize' in non-business context."""
        rule = AIVocabularyRule()
        issues = rule.check("Puppies need to socialize with other dogs.", "test.md")
        soc_issues = [i for i in issues if "socializ" in i.message.lower()]
        assert len(soc_issues) == 0

    def test_suggestions_for_business_words(self) -> None:
        """Business jargon words should have suggestions."""
        from slop_lint.data.vocabulary import VOCABULARY_SUGGESTIONS

        new_words = [
            "synergy",
            "value-add",
            "bandwidth",
            "incentivize",
            "ideate",
            "socialize",
        ]
        for word in new_words:
            assert word in VOCABULARY_SUGGESTIONS, f"Missing suggestion for '{word}'"


class TestPolitenessFogPhrases:
    """Tests for business politeness fog additions to V002."""

    def test_detects_just_circling_back(self) -> None:
        """Detect 'just circling back' politeness fog."""
        from slop_lint.rules.vocab import CollaborativePhrasesRule

        rule = CollaborativePhrasesRule()
        issues = rule.check("Just circling back on the previous thread.", "test.md")
        assert len(issues) >= 1

    def test_detects_just_following_up(self) -> None:
        """Detect 'just following up' politeness fog."""
        from slop_lint.rules.vocab import CollaborativePhrasesRule

        rule = CollaborativePhrasesRule()
        issues = rule.check("Just following up on the proposal.", "test.md")
        assert len(issues) >= 1

    def test_detects_gentle_reminder(self) -> None:
        """Detect 'just a gentle reminder' politeness fog."""
        from slop_lint.rules.vocab import CollaborativePhrasesRule

        rule = CollaborativePhrasesRule()
        issues = rule.check("Just a gentle reminder about the deadline.", "test.md")
        assert len(issues) >= 1

    def test_detects_per_our_last_conversation(self) -> None:
        """Detect 'per our last conversation' politeness fog."""
        from slop_lint.rules.vocab import CollaborativePhrasesRule

        rule = CollaborativePhrasesRule()
        issues = rule.check("Per our last conversation, here is the update.", "test.md")
        assert len(issues) >= 1
