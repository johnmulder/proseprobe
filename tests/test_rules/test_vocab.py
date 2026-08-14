"""Tests for vocabulary rules (V001-V011 and V013-V017)."""

import pytest

from proseprobe.config import Config
from proseprobe.data.phrases import (
    NEEDLESS_INTENSIFIER_REPLACEMENTS,
    REDUNDANT_MODIFIER_REPLACEMENTS,
    REDUNDANT_PAIR_REPLACEMENTS,
    VERBOSE_VERB_PHRASE_REPLACEMENTS,
    WORDY_PHRASE_REPLACEMENTS,
)
from proseprobe.rules import get_all_rules
from proseprobe.rules.base import Confidence, Rule, Severity
from proseprobe.rules.vocab import (
    AbsoluteReliabilityClaimRule,
    AIVocabularyRule,
    CollaborativePhrasesRule,
    GrandioseStakesRule,
    ImpreciseQuantityRule,
    InventedConceptLabelsRule,
    KnowledgeCutoffRule,
    NeedlessIntensifierRule,
    PromotionalLanguageRule,
    RedundantModifierRule,
    RedundantPairRule,
    TrendOverclaimRule,
    UnboundedSuperlativeRule,
    VerboseVerbPhraseRule,
    WeaselWordsRule,
    WordyPhraseRule,
)


def test_grandiose_stakes_has_exact_source_span() -> None:
    source = "This release will change everything."
    [issue] = GrandioseStakesRule().check(source, "test.md")

    assert source[issue.column - 1 : issue.end_column - 1] == "will change everything"


def test_invented_labels_retain_each_exact_span() -> None:
    source = "The trust gap compounds the access divide."
    issues = InventedConceptLabelsRule(threshold=2).check(source, "test.md")

    assert [source[issue.column - 1 : issue.end_column - 1] for issue in issues] == [
        "trust gap",
        "access divide",
    ]


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


@pytest.mark.parametrize(
    ("phrase", "expected_rule_ids"),
    [
        ("robust", ("V001",)),
        ("seamless", ("V001",)),
        ("world-class", ("V004",)),
        ("powerful", ()),
        ("flexible", ()),
        ("intuitive", ()),
    ],
)
def test_quality_language_keeps_existing_rule_ownership(
    phrase: str,
    expected_rule_ids: tuple[str, ...],
) -> None:
    content = f"The adapter provides {phrase} defaults."
    issues = AIVocabularyRule().check(content, "test.md")
    issues += PromotionalLanguageRule().check(content, "test.md")

    assert tuple(issue.rule_id for issue in issues) == expected_rule_ids


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

    @pytest.mark.parametrize(
        "text",
        [
            "utilize",
            "utilizes",
            "utilized",
            "utilizing",
            "utilise",
            "utilises",
            "utilised",
            "utilising",
        ],
    )
    def test_utilize_forms_have_one_canonical_finding(
        self,
        rule: AIVocabularyRule,
        text: str,
    ) -> None:
        issues = rule.check(f"The adapter will {text} the parser.", "test.md")

        assert len(issues) == 1
        assert issues[0].confidence is Confidence.MEDIUM
        assert issues[0].suggestion == "use"

    def test_allowed_utilize_suppresses_every_supported_form(self) -> None:
        rule = AIVocabularyRule(allowed={"utilize"})
        content = (
            "utilize utilizes utilized utilizing utilise utilises utilised utilising"
        )

        assert rule.check(content, "test.md") == []

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

    def test_ignores_plain_dated_statement(self, rule: KnowledgeCutoffRule) -> None:
        content = "As of August 2026, version 1.4.0 is the supported release."

        assert rule.check(content, "test.md") == []


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
        from proseprobe.rules.vocab import GrandioseStakesRule

        content = "This will fundamentally reshape how we think about everything."
        issues = GrandioseStakesRule().check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "V006"

    def test_detects_define_the_next_era(self) -> None:
        """Detect 'define the next era' inflation."""
        from proseprobe.rules.vocab import GrandioseStakesRule

        content = "This technology will define the next era of computing."
        issues = GrandioseStakesRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_detects_change_everything(self) -> None:
        """Detect 'will change everything' inflation."""
        from proseprobe.rules.vocab import GrandioseStakesRule

        content = "AI will change everything about how we work."
        issues = GrandioseStakesRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal technical prose."""
        from proseprobe.rules.vocab import GrandioseStakesRule

        content = "The library provides a simple API for HTTP requests."
        issues = GrandioseStakesRule().check(content, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.vocab import GrandioseStakesRule

        rule = GrandioseStakesRule()
        assert rule.id == "V006"
        assert rule.name == "Grandiose Stakes"


class TestInventedConceptLabels:
    """Tests for V007: Invented Concept Labels."""

    def test_detects_multiple_labels(self) -> None:
        """Detect 2+ compound analytical labels in same document."""
        from proseprobe.rules.vocab import InventedConceptLabelsRule

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
        from proseprobe.rules.vocab import InventedConceptLabelsRule

        content = "The productivity paradox has been studied extensively."
        issues = InventedConceptLabelsRule().check(content, "test.md")
        assert len(issues) == 0

    def test_excludes_literal_reference_from_reported_labels(self) -> None:
        from proseprobe.rules.vocab import InventedConceptLabelsRule

        content = (
            "The automation paradox slows delivery.\n"
            "The innovation trap wastes time.\n"
            "This study fills that gap."
        )

        issues = InventedConceptLabelsRule().check(content, "test.md")

        assert [issue.message for issue in issues] == [
            "Invented concept label: 'automation paradox'",
            "Invented concept label: 'innovation trap'",
        ]

    def test_literal_references_do_not_satisfy_threshold(self) -> None:
        from proseprobe.rules.vocab import InventedConceptLabelsRule

        content = "This study fills a gap. That dilemma remains unresolved."

        assert InventedConceptLabelsRule().check(content, "test.md") == []

    @pytest.mark.parametrize(
        ("gap_reference", "dilemma_reference"),
        [
            ("our gap", "their dilemma"),
            ("another gap", "every dilemma"),
            ("which gap", "neither dilemma"),
            ("other gap", "what dilemma"),
        ],
    )
    def test_other_literal_determiners_do_not_satisfy_threshold(
        self, gap_reference: str, dilemma_reference: str
    ) -> None:
        from proseprobe.rules.vocab import InventedConceptLabelsRule

        content = (
            f"This study fills {gap_reference}. The team studies {dilemma_reference}."
        )

        assert InventedConceptLabelsRule().check(content, "test.md") == []

    @pytest.mark.parametrize(
        "literal_reference",
        ["our gap", "every dilemma", "which gap", "other dilemma"],
    )
    def test_other_literal_determiners_are_not_reported_with_labels(
        self, literal_reference: str
    ) -> None:
        from proseprobe.rules.vocab import InventedConceptLabelsRule

        content = (
            "The automation paradox slows delivery.\n"
            "The innovation trap wastes time.\n"
            f"This study addresses {literal_reference}."
        )

        issues = InventedConceptLabelsRule().check(content, "test.md")

        assert [issue.message for issue in issues] == [
            "Invented concept label: 'automation paradox'",
            "Invented concept label: 'innovation trap'",
        ]

    @pytest.mark.parametrize(
        "content",
        [
            "The team's gap remains. John's dilemma continues.",
            "The team\u2019s gap remains. John\u2019s dilemma continues.",
        ],
    )
    def test_possessive_clitics_do_not_satisfy_threshold(self, content: str) -> None:
        from proseprobe.rules.vocab import InventedConceptLabelsRule

        assert InventedConceptLabelsRule().check(content, "test.md") == []

    def test_single_quoted_labels_still_satisfy_threshold(self) -> None:
        from proseprobe.rules.vocab import InventedConceptLabelsRule

        content = "The 'automation paradox' compounds the 'innovation trap'."

        issues = InventedConceptLabelsRule().check(content, "test.md")

        assert [issue.message for issue in issues] == [
            "Invented concept label: 'automation paradox'",
            "Invented concept label: 'innovation trap'",
        ]

    def test_ignores_normal_prose(self) -> None:
        """Don't flag prose without compound labels."""
        from proseprobe.rules.vocab import InventedConceptLabelsRule

        content = "The system handles errors gracefully and logs all events."
        issues = InventedConceptLabelsRule().check(content, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.vocab import InventedConceptLabelsRule

        rule = InventedConceptLabelsRule()
        assert rule.id == "V007"
        assert rule.name == "Invented Concept Labels"


# ---------- Phase 1 (Journalism Tropes) TDD: V008 ----------


class TestTrendOverclaim:
    """Tests for V008: Trend Overclaim."""

    def test_detects_more_and_more_people(self) -> None:
        """Detect 'more and more people' trend overclaim."""
        from proseprobe.rules.vocab import TrendOverclaimRule

        content = "More and more people are adopting this framework."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "V008"

    def test_detects_growing_number(self) -> None:
        """Detect 'a growing number of' trend overclaim."""
        from proseprobe.rules.vocab import TrendOverclaimRule

        content = "A growing number of developers prefer TypeScript."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_detects_everyone_is_talking(self) -> None:
        """Detect 'everyone is talking about' trend overclaim."""
        from proseprobe.rules.vocab import TrendOverclaimRule

        content = "Everyone is talking about this new approach."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_detects_increasingly_popular(self) -> None:
        """Detect 'increasingly popular' trend overclaim."""
        from proseprobe.rules.vocab import TrendOverclaimRule

        content = "Rust is increasingly popular among systems programmers."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal technical prose."""
        from proseprobe.rules.vocab import TrendOverclaimRule

        content = "The library provides a simple API for HTTP requests."
        issues = TrendOverclaimRule().check(content, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.vocab import TrendOverclaimRule

        rule = TrendOverclaimRule()
        assert rule.id == "V008"
        assert rule.name == "Trend Overclaim"


class TestWordyPhrase:
    """Tests for V009: Wordy Phrase."""

    def test_curated_phrase_table(self) -> None:
        assert WORDY_PHRASE_REPLACEMENTS == {
            "at this point in time": "now",
            "due to the fact that": "because",
            "during the course of": "during",
            "enable the ability to": "allow",
            "enables the ability to": "allows",
            "has the ability to": "can",
            "have the ability to": "can",
            "in close proximity to": "near",
            "in order to": "to",
            "in the event that": "if",
            "on the basis of": "based on",
            "with regard to": "about",
        }

    @pytest.mark.parametrize(
        ("phrase", "replacement"), WORDY_PHRASE_REPLACEMENTS.items()
    )
    def test_suggests_each_curated_replacement(
        self, phrase: str, replacement: str
    ) -> None:
        [issue] = WordyPhraseRule().check(f"Use {phrase} finish.", "guide.md")

        assert issue.suggestion == replacement

    def test_reports_exact_metadata_and_source_span(self) -> None:
        source = "Use in order to retry."

        [issue] = WordyPhraseRule().check(source, "guide.md")

        assert issue.rule_id == "V009"
        assert issue.message == "Wordy phrase: 'in order to'"
        assert (issue.line, issue.column, issue.end_column) == (1, 5, 16)
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "to"

    def test_case_repetitions_and_different_phrases_follow_source_order(self) -> None:
        source = "IN ORDER TO retry, act at this point in time, in order to recover."

        issues = WordyPhraseRule().check(source, "guide.md")

        assert [issue.message for issue in issues] == [
            "Wordy phrase: 'IN ORDER TO'",
            "Wordy phrase: 'at this point in time'",
            "Wordy phrase: 'in order to'",
        ]

    def test_ignores_markdown_headings_and_code(self) -> None:
        source = """\
# In order to

Use `in order to` as the legacy label.

```text
due to the fact that
```
"""

        assert WordyPhraseRule().check(source, "guide.md") == []

    def test_checks_python_documentation_but_not_code_strings(self) -> None:
        source = '''\
label = "in order to"
# In order to retry, call the client again.

def retry():
    """At this point in time, retry once."""
'''

        issues = WordyPhraseRule().check(source, "client.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_ignores_nonmatching_fragments(self) -> None:
        source = "The rows remain in order. The event that failed was recorded."

        assert WordyPhraseRule().check(source, "guide.md") == []


class TestRedundantPair:
    """Tests for V010: Redundant Pair."""

    def test_curated_redundant_pair_table(self) -> None:
        assert REDUNDANT_PAIR_REPLACEMENTS == {
            "each and every": "each",
            "merge together": "merge",
            "merged together": "merged",
            "merges together": "merges",
            "merging together": "merging",
            "past history": "history",
            "repeat again": "repeat",
            "repeated again": "repeated",
            "repeating again": "repeating",
            "repeats again": "repeats",
            "revert back": "revert",
            "reverted back": "reverted",
            "reverting back": "reverting",
            "reverts back": "reverts",
        }

    @pytest.mark.parametrize(
        ("phrase", "replacement"), REDUNDANT_PAIR_REPLACEMENTS.items()
    )
    def test_suggests_each_curated_replacement(
        self, phrase: str, replacement: str
    ) -> None:
        [issue] = RedundantPairRule().check(f"They {phrase} today.", "guide.md")

        assert issue.suggestion == replacement

    def test_reports_exact_metadata_and_source_span(self) -> None:
        source = "Review each and every request."

        [issue] = RedundantPairRule().check(source, "guide.md")

        assert issue.rule_id == "V010"
        assert issue.message == "Redundant pair: 'each and every'"
        assert (issue.line, issue.column, issue.end_column) == (1, 8, 22)
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "each"

    def test_case_repetitions_and_different_pairs_follow_source_order(self) -> None:
        source = "REVERT BACK, review past history, then revert back."

        issues = RedundantPairRule().check(source, "guide.md")

        assert [issue.message for issue in issues] == [
            "Redundant pair: 'REVERT BACK'",
            "Redundant pair: 'past history'",
            "Redundant pair: 'revert back'",
        ]

    def test_ignores_markdown_headings_and_code(self) -> None:
        source = """\
# Each and every

Use `past history` as the legacy label.

```text
revert back
```
"""

        assert RedundantPairRule().check(source, "guide.md") == []

    def test_checks_python_documentation_but_not_code_strings(self) -> None:
        source = '''\
label = "past history"
# Review each and every request.

def rollback():
    """The client reverted back after the failure."""
'''

        issues = RedundantPairRule().check(source, "client.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_ignores_nearby_nonmatching_words(self) -> None:
        source = "Review each request and every response in the history report."

        assert RedundantPairRule().check(source, "guide.md") == []

    def test_shared_scan_keeps_v009_message_and_suggestion(self) -> None:
        [issue] = WordyPhraseRule().check("Use in order to retry.", "guide.md")

        assert issue.message == "Wordy phrase: 'in order to'"
        assert issue.suggestion == "to"


class TestVerboseVerbPhrase:
    """Tests for V011: Verbose Verb Phrase."""

    def test_curated_phrase_table(self) -> None:
        assert VERBOSE_VERB_PHRASE_REPLACEMENTS == {
            "conduct an analysis": "analyze",
            "conducted an analysis": "analyzed",
            "conducting an analysis": "analyzing",
            "conducts an analysis": "analyzes",
            "gave consideration to": "considered",
            "give consideration to": "consider",
            "gives consideration to": "considers",
            "giving consideration to": "considering",
            "made a decision": "decided",
            "make a decision": "decide",
            "makes a decision": "decides",
            "making a decision": "deciding",
            "provide an explanation": "explain",
            "provided an explanation": "explained",
            "provides an explanation": "explains",
            "providing an explanation": "explaining",
        }

    @pytest.mark.parametrize(
        ("phrase", "replacement"), VERBOSE_VERB_PHRASE_REPLACEMENTS.items()
    )
    def test_suggests_each_curated_replacement(
        self, phrase: str, replacement: str
    ) -> None:
        [issue] = VerboseVerbPhraseRule().check(
            f"They {phrase} the result.", "guide.md"
        )

        assert issue.suggestion == replacement

    def test_reports_exact_metadata_and_source_span(self) -> None:
        source = "Teams make a decision before deployment."

        [issue] = VerboseVerbPhraseRule().check(source, "guide.md")

        assert VerboseVerbPhraseRule.description == (
            "Detects curated weak verbs with abstract-noun complements"
        )
        assert issue.rule_id == "V011"
        assert issue.message == "Verbose verb phrase: 'make a decision'"
        assert (issue.line, issue.column, issue.end_column) == (1, 7, 22)
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "decide"

    def test_reports_repeated_and_different_phrases_in_source_order(self) -> None:
        source = "MAKE A DECISION, conduct an analysis, then make a decision again."

        issues = VerboseVerbPhraseRule().check(source, "guide.md")

        assert [issue.message for issue in issues] == [
            "Verbose verb phrase: 'MAKE A DECISION'",
            "Verbose verb phrase: 'conduct an analysis'",
            "Verbose verb phrase: 'make a decision'",
        ]

    def test_ignores_markdown_headings_and_code(self) -> None:
        source = """\
# Make a decision

Use `conduct an analysis` as the legacy label.

```text
provide an explanation
```
"""

        assert VerboseVerbPhraseRule().check(source, "guide.md") == []

    def test_checks_python_documentation_but_not_code_strings(self) -> None:
        source = '''\
label = "make a decision"
# Conduct an analysis before deployment.

def explain():
    """Provide an explanation for the result."""
'''

        issues = VerboseVerbPhraseRule().check(source, "client.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_ignores_near_misses(self) -> None:
        source = (
            "Make the decision after teams conduct analysis. Provide explanations "
            "and give careful consideration to every result."
        )

        assert VerboseVerbPhraseRule().check(source, "guide.md") == []

    @pytest.mark.parametrize(
        "compound", ["decision boundary", "decision table", "decision tree"]
    )
    def test_ignores_decision_compounds(self, compound: str) -> None:
        source = f"The builder makes a {compound} available."

        assert VerboseVerbPhraseRule().check(source, "guide.md") == []


class TestRedundantModifier:
    """Tests for V013: Redundant Modifier."""

    def test_curated_modifier_table(self) -> None:
        assert REDUNDANT_MODIFIER_REPLACEMENTS == {
            "advance planning": "planning",
            "basic fundamental": "fundamental",
            "basic fundamentals": "fundamentals",
            "joint collaboration": "collaboration",
            "joint collaborations": "collaborations",
            "negative drawback": "drawback",
            "negative drawbacks": "drawbacks",
            "positive benefit": "benefit",
            "positive benefits": "benefits",
            "true fact": "fact",
            "true facts": "facts",
            "unexpected surprise": "surprise",
            "unexpected surprises": "surprises",
        }

    @pytest.mark.parametrize(
        ("phrase", "replacement"), REDUNDANT_MODIFIER_REPLACEMENTS.items()
    )
    def test_suggests_each_curated_replacement(
        self, phrase: str, replacement: str
    ) -> None:
        [issue] = RedundantModifierRule().check(
            f"Review the {phrase} today.", "guide.md"
        )

        assert issue.suggestion == replacement

    def test_reports_exact_metadata_and_source_span(self) -> None:
        source = "Review the basic fundamentals before deployment."

        [issue] = RedundantModifierRule().check(source, "guide.md")

        assert issue.rule_id == "V013"
        assert issue.message == "Redundant modifier: 'basic fundamentals'"
        assert (issue.line, issue.column, issue.end_column) == (1, 12, 30)
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "fundamentals"

    def test_reports_repeated_and_different_phrases_in_source_order(self) -> None:
        source = "TRUE FACTS, one positive benefit, then another positive benefit."

        issues = RedundantModifierRule().check(source, "guide.md")

        assert [issue.message for issue in issues] == [
            "Redundant modifier: 'TRUE FACTS'",
            "Redundant modifier: 'positive benefit'",
            "Redundant modifier: 'positive benefit'",
        ]

    def test_ignores_markdown_headings_and_code(self) -> None:
        source = """\
# Basic fundamentals

Use `positive benefit` as the legacy label.

```text
unexpected surprise
```
"""

        assert RedundantModifierRule().check(source, "guide.md") == []

    def test_checks_python_documentation_but_not_code_strings(self) -> None:
        source = '''\
label = "basic fundamentals"
# Record every positive benefit.

def summarize():
    """Report any unexpected surprise."""
'''

        issues = RedundantModifierRule().check(source, "client.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_ignores_debatable_modifiers_and_near_misses(self) -> None:
        source = (
            "The brief summary covers the final outcome and future plans. "
            "Past experience found a completely unanimous result and a very unique "
            "case. The benefit was positive for one group but negative for another."
        )

        assert RedundantModifierRule().check(source, "guide.md") == []


class TestImpreciseQuantity:
    """Tests for V014: Imprecise Quantity."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "a considerable number of",
            "a large number of",
            "a small number of",
            "a handful of",
        ],
    )
    def test_reports_each_curated_phrase(self, phrase: str) -> None:
        source = f"The queue contains {phrase} requests."

        [issue] = ImpreciseQuantityRule().check(source, "guide.md")

        assert issue.rule_id == "V014"
        assert issue.message == f"Imprecise quantity: '{phrase}'"
        assert source[issue.column - 1 : issue.end_column - 1] == phrase
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "Use a measured quantity or cite the source"

    def test_preserves_a_wrapped_source_span(self) -> None:
        source = "A large number\nof requests failed."

        [issue] = ImpreciseQuantityRule().check(source, "guide.md")

        assert (issue.line, issue.column) == (1, 1)
        assert (issue.end_line, issue.end_column) == (2, 3)
        assert issue.message == "Imprecise quantity: 'A large number of'"

    def test_reports_multiple_phrases_in_source_order(self) -> None:
        source = "A handful of clients sent a small number of requests."

        issues = ImpreciseQuantityRule().check(source, "guide.md")

        assert [issue.message for issue in issues] == [
            "Imprecise quantity: 'A handful of'",
            "Imprecise quantity: 'a small number of'",
        ]

    @pytest.mark.parametrize(
        "source",
        [
            "A large number of requests failed; 42 timed out.",
            "The benchmark found a large number of failures.",
            "In July, a handful of clients retried.",
            "Mina Ortiz reported a small number of failures.",
            (
                "The [benchmark report](https://example.com/report) found "
                "a considerable number of failures."
            ),
        ],
    )
    def test_local_evidence_lowers_confidence(self, source: str) -> None:
        [issue] = ImpreciseQuantityRule().check(source, "guide.md")

        assert issue.confidence is Confidence.LOW

    def test_uses_adjacent_evidence_in_the_same_scope(self) -> None:
        source = (
            "The benchmark measured 42 failures. A large number of requests timed out."
        )

        [issue] = ImpreciseQuantityRule().check(source, "guide.md")

        assert issue.confidence is Confidence.LOW

    def test_evidence_does_not_cross_scope_boundaries(self) -> None:
        source = (
            "The benchmark measured 42 failures.\n\n"
            "# Findings\n\nA large number of requests timed out."
        )

        [issue] = ImpreciseQuantityRule().check(source, "guide.md")

        assert issue.line == 5
        assert issue.confidence is Confidence.MEDIUM

    @pytest.mark.parametrize(
        "source",
        [
            "# A large number of failures",
            "## Example\n\nA large number of requests failed.",
            "Use `a large number of` as the legacy label.",
            "```text\na handful of failures\n```",
        ],
    )
    def test_ignores_headings_examples_and_code(self, source: str) -> None:
        assert ImpreciseQuantityRule().check(source, "guide.md") == []

    def test_checks_python_documentation_but_not_code_strings(self) -> None:
        source = '''\
label = "a large number of"
# A handful of clients retried.

def summarize():
    """A small number of requests failed."""
'''

        issues = ImpreciseQuantityRule().check(source, "client.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_ignores_broad_and_overlapping_quantifiers(self) -> None:
        source = (
            "Many clients sent some requests. Several retries succeeded. "
            "A significant number of jobs and a substantial number of tasks ran."
        )

        assert ImpreciseQuantityRule().check(source, "guide.md") == []

    def test_rule_metadata(self) -> None:
        rule = ImpreciseQuantityRule()

        assert rule.id == "V014"
        assert rule.name == "Imprecise Quantity"
        assert rule.default_confidence is Confidence.MEDIUM


class TestUnboundedSuperlative:
    """Tests for V015: Unbounded Superlative."""

    @pytest.mark.parametrize(
        ("source", "claim"),
        [
            ("Atlas is the best option.", "the best"),
            ("The legacy route was the worst.", "the worst"),
            ("This parser is fastest.", "fastest"),
            ("The fallback remains the most reliable.", "the most reliable"),
            ("These clusters are the least scalable.", "the least scalable"),
            ("Its queue is smallest.", "smallest"),
        ],
    )
    def test_reports_each_curated_claim(self, source: str, claim: str) -> None:
        [issue] = UnboundedSuperlativeRule().check(source, "guide.md")

        assert issue.rule_id == "V015"
        assert issue.message == f"Unbounded superlative: '{claim}'"
        assert source[issue.column - 1 : issue.end_column - 1] == claim
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.LOW
        assert issue.suggestion == "Name the comparison set and supporting evidence"

    def test_preserves_a_wrapped_source_span(self) -> None:
        source = "Atlas is the most\nreliable option."

        [issue] = UnboundedSuperlativeRule().check(source, "guide.md")

        assert (issue.line, issue.column) == (1, 10)
        assert (issue.end_line, issue.end_column) == (2, 9)
        assert issue.message == "Unbounded superlative: 'the most reliable'"

    def test_reports_multiple_claims_in_source_order(self) -> None:
        source = "Atlas is fastest, but Boreal is slowest."

        issues = UnboundedSuperlativeRule().check(source, "guide.md")

        assert [issue.message for issue in issues] == [
            "Unbounded superlative: 'fastest'",
            "Unbounded superlative: 'slowest'",
        ]

    @pytest.mark.parametrize(
        "source",
        [
            "We compared three parsers. Atlas is the fastest among them.",
            "In our benchmark, Atlas is fastest.",
            "Of the three options, Atlas is best.",
            "Atlas processed 100 requests in 12 ms. It is the fastest.",
            "Mina Ortiz reported that Atlas is the most reliable.",
        ],
    )
    def test_suppresses_local_comparison_or_evidence(self, source: str) -> None:
        assert UnboundedSuperlativeRule().check(source, "guide.md") == []

    def test_comparison_evidence_does_not_cross_scope_boundaries(self) -> None:
        source = "We compared three parsers.\n\n# Finding\n\nAtlas is the fastest."

        [issue] = UnboundedSuperlativeRule().check(source, "guide.md")

        assert issue.line == 5

    @pytest.mark.parametrize(
        "source",
        [
            "Which parser is fastest?",
            "If Atlas is fastest, deploy it.",
            "Determine whether Atlas is fastest.",
            'Avoid claiming "Atlas is the best" in release notes.',
            "Choose the fastest parser.",
            "Atlas is best-in-class.",
            "Atlas performs fastest under load.",
            "# Atlas is the fastest",
            "## Example\n\nAtlas is the fastest.",
            "Use `Atlas is the fastest` as the label.",
            "```text\nAtlas is the fastest.\n```",
        ],
    )
    def test_ignores_non_claim_and_excluded_contexts(self, source: str) -> None:
        assert UnboundedSuperlativeRule().check(source, "guide.md") == []

    def test_checks_python_documentation_but_not_code_strings(self) -> None:
        source = '''\
label = "Atlas is the fastest"
# Atlas is the fastest.

def rank():
    """Boreal is the least efficient."""
'''

        issues = UnboundedSuperlativeRule().check(source, "client.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_rule_metadata(self) -> None:
        rule = UnboundedSuperlativeRule()

        assert rule.id == "V015"
        assert rule.name == "Unbounded Superlative"
        assert rule.default_confidence is Confidence.LOW


class TestAbsoluteReliabilityClaim:
    """Tests for V016: Absolute Reliability Claim."""

    @pytest.mark.parametrize(
        ("source", "claim"),
        [
            ("The cache never fails.", "never fails"),
            ("The deployment always succeeds.", "always succeeds"),
            ("The filter eliminates all errors.", "eliminates all errors"),
            ("The gateway is 100% secure.", "100% secure"),
        ],
    )
    def test_reports_each_curated_claim(self, source: str, claim: str) -> None:
        [issue] = AbsoluteReliabilityClaimRule().check(source, "guide.md")

        assert issue.rule_id == "V016"
        assert issue.message == f"Absolute reliability claim: '{claim}'"
        assert source[issue.column - 1 : issue.end_column - 1] == claim
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "State the tested scope and observed result"

    def test_reports_multiple_claims_in_source_order(self) -> None:
        source = "The cache never fails, and deployment always succeeds."

        issues = AbsoluteReliabilityClaimRule().check(source, "guide.md")

        assert [issue.message for issue in issues] == [
            "Absolute reliability claim: 'never fails'",
            "Absolute reliability claim: 'always succeeds'",
        ]

    def test_preserves_a_wrapped_source_span(self) -> None:
        source = "The migration always\nsucceeds after validation."

        [issue] = AbsoluteReliabilityClaimRule().check(source, "guide.md")

        assert (issue.line, issue.column) == (1, 15)
        assert (issue.end_line, issue.end_column) == (2, 9)
        assert issue.message == "Absolute reliability claim: 'always succeeds'"

    @pytest.mark.parametrize(
        "source",
        [
            "Across 10,000 test runs, the migration always succeeds.",
            "Under the tested configuration, the retry loop never fails.",
            (
                "We observed no failures in 5,000 requests. "
                "The parser eliminates all errors."
            ),
        ],
    )
    def test_suppresses_concrete_test_bounds(self, source: str) -> None:
        assert AbsoluteReliabilityClaimRule().check(source, "guide.md") == []

    def test_test_evidence_does_not_cross_scope_boundaries(self) -> None:
        source = (
            "We observed no failures in 5,000 requests.\n\n"
            "# Deployment\n\nThe migration always succeeds."
        )

        [issue] = AbsoluteReliabilityClaimRule().check(source, "guide.md")

        assert issue.line == 5

    @pytest.mark.parametrize(
        "source",
        [
            'Avoid saying "never fails" in release notes.',
            "The phrase always succeeds is misleading.",
            "## Example\n\nThe migration always succeeds.",
            "Use `always succeeds` only as a test label.",
            "```text\nThe migration always succeeds.\n```",
        ],
    )
    def test_ignores_literal_examples_and_code(self, source: str) -> None:
        assert AbsoluteReliabilityClaimRule().check(source, "guide.md") == []

    def test_checks_python_documentation_but_not_code_strings(self) -> None:
        source = '''\
label = "always succeeds"
# The deployment always succeeds.

def retry():
    """The retry loop never fails."""
'''

        issues = AbsoluteReliabilityClaimRule().check(source, "client.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_ignores_near_misses(self) -> None:
        source = (
            "The migration should always succeed. The test never failed. "
            "The gateway is 99.9% secure. The filter eliminates most errors."
        )

        assert AbsoluteReliabilityClaimRule().check(source, "guide.md") == []

    def test_rule_metadata(self) -> None:
        rule = AbsoluteReliabilityClaimRule()

        assert rule.id == "V016"
        assert rule.name == "Absolute Reliability Claim"
        assert rule.default_confidence is Confidence.MEDIUM


class TestNeedlessIntensifier:
    """Tests for V017: Needless Intensifier."""

    def test_curated_replacement_table(self) -> None:
        assert NEEDLESS_INTENSIFIER_REPLACEMENTS == {
            "completely unanimous": "unanimous",
            "very unique": "unique",
        }

    @pytest.mark.parametrize(
        ("phrase", "replacement"), NEEDLESS_INTENSIFIER_REPLACEMENTS.items()
    )
    def test_suggests_each_curated_replacement(
        self, phrase: str, replacement: str
    ) -> None:
        [issue] = NeedlessIntensifierRule().check(
            f"The report calls this {phrase}.", "guide.md"
        )

        assert issue.rule_id == "V017"
        assert issue.suggestion == replacement
        assert issue.confidence is Confidence.LOW

    def test_reports_exact_metadata_and_source_span(self) -> None:
        source = "The panel reached a completely unanimous decision."

        [issue] = NeedlessIntensifierRule().check(source, "guide.md")

        assert issue.message == "Needless intensifier: 'completely unanimous'"
        assert source[issue.column - 1 : issue.end_column - 1] == (
            "completely unanimous"
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.LOW
        assert issue.suggestion == "unanimous"

    def test_reports_repeated_phrases_in_source_order(self) -> None:
        source = "A VERY UNIQUE fault followed a completely unanimous vote."

        issues = NeedlessIntensifierRule().check(source, "guide.md")

        assert [issue.message for issue in issues] == [
            "Needless intensifier: 'VERY UNIQUE'",
            "Needless intensifier: 'completely unanimous'",
        ]

    def test_ignores_markdown_headings_and_code(self) -> None:
        source = """\
# Very unique behavior

Use `completely unanimous` as the legacy label.

```text
very unique
```
"""

        assert NeedlessIntensifierRule().check(source, "guide.md") == []

    def test_checks_python_documentation_but_not_code_strings(self) -> None:
        source = '''\
label = "very unique"
# The panel reached a completely unanimous decision.

def summarize():
    """Describe the very unique failure mode."""
'''

        issues = NeedlessIntensifierRule().check(source, "client.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_ignores_near_misses(self) -> None:
        source = (
            "The reviewers were almost unanimous. The failure mode is unique to "
            "this deployment. The shards are very different and completely empty."
        )

        assert NeedlessIntensifierRule().check(source, "guide.md") == []

    def test_does_not_duplicate_redundant_modifier_rule(self) -> None:
        source = "The vote was completely unanimous in a very unique case."

        assert RedundantModifierRule().check(source, "guide.md") == []
        assert len(NeedlessIntensifierRule().check(source, "guide.md")) == 2

    def test_rule_metadata(self) -> None:
        rule = NeedlessIntensifierRule()

        assert rule.id == "V017"
        assert rule.name == "Needless Intensifier"
        assert rule.default_confidence is Confidence.LOW


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
        from proseprobe.data.vocabulary import VOCABULARY_SUGGESTIONS

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
        from proseprobe.data.vocabulary import VOCABULARY_SUGGESTIONS

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
        from proseprobe.rules.vocab import CollaborativePhrasesRule

        rule = CollaborativePhrasesRule()
        issues = rule.check("Just circling back on the previous thread.", "test.md")
        assert len(issues) >= 1

    def test_detects_just_following_up(self) -> None:
        """Detect 'just following up' politeness fog."""
        from proseprobe.rules.vocab import CollaborativePhrasesRule

        rule = CollaborativePhrasesRule()
        issues = rule.check("Just following up on the proposal.", "test.md")
        assert len(issues) >= 1

    def test_detects_gentle_reminder(self) -> None:
        """Detect 'just a gentle reminder' politeness fog."""
        from proseprobe.rules.vocab import CollaborativePhrasesRule

        rule = CollaborativePhrasesRule()
        issues = rule.check("Just a gentle reminder about the deadline.", "test.md")
        assert len(issues) >= 1

    def test_detects_per_our_last_conversation(self) -> None:
        """Detect 'per our last conversation' politeness fog."""
        from proseprobe.rules.vocab import CollaborativePhrasesRule

        rule = CollaborativePhrasesRule()
        issues = rule.check("Per our last conversation, here is the update.", "test.md")
        assert len(issues) >= 1
