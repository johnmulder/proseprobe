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


@pytest.mark.parametrize(
    ("rule", "phrase", "replacement"),
    [
        (WordyPhraseRule(), "due to the\nfact that", "because"),
        (RedundantPairRule(), "each and\nevery", "each"),
        (VerboseVerbPhraseRule(), "make a\ndecision", "decide"),
        (RedundantModifierRule(), "basic\nfundamentals", "fundamentals"),
        (NeedlessIntensifierRule(), "very\nunique", "unique"),
    ],
)
@pytest.mark.parametrize("filename", ["case.md", "case.py"])
def test_replacement_phrases_keep_wrapped_spans(
    rule: Rule, phrase: str, replacement: str, filename: str
) -> None:
    source = phrase if filename.endswith(".md") else f'"""{phrase}"""'
    [issue] = rule.check(source, filename)
    assert (issue.line, issue.column) == (1, 1 if filename.endswith(".md") else 4)
    assert (issue.end_line, issue.end_column) == (2, len(phrase.split("\n")[1]) + 1)
    assert issue.suggestion == replacement
    assert " ".join(phrase.split()) in issue.message


@pytest.mark.parametrize(
    ("source", "filename"),
    [
        ("# due to the\n# fact that", "case.py"),
        ("> due to the\n> fact that", "case.md"),
    ],
)
def test_wrapped_phrases_allow_structural_prefixes(source: str, filename: str) -> None:
    [issue] = WordyPhraseRule().check(source, filename)
    assert (issue.line, issue.column, issue.end_line, issue.end_column) == (1, 3, 2, 12)


@pytest.mark.parametrize(
    "source",
    [
        "due to the\n\nfact that",
        "due to the\n# fact that",
        "- due to the\n- fact that",
        "in `sorted` order to",
        "in <code>x</code> order to",
        "```\ndue to the\nfact that\n```",
    ],
)
def test_wrapped_phrases_do_not_cross_boundaries_or_masked_text(source: str) -> None:
    assert WordyPhraseRule().check(source, "case.md") == []


@pytest.mark.parametrize("source", ["make a\ndecision tree", "make a\ndecision\ntree"])
def test_wrapped_decision_compound_remains_a_negative(source: str) -> None:
    assert VerboseVerbPhraseRule().check(source, "case.md") == []


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

    @pytest.mark.parametrize(
        "content",
        [
            "The implementation uses robust regression to limit outlier effects.",
            "Use ROBUST REGRESSION when fitting contaminated samples.",
            "The tutorial describes robust regressions for contaminated data.",
        ],
    )
    def test_preserves_named_regression_method(
        self, rule: AIVocabularyRule, content: str
    ) -> None:
        assert rule.check(content, "methods.md") == []

    def test_statistical_term_does_not_exempt_other_claims(
        self, rule: AIVocabularyRule
    ) -> None:
        content = (
            "A robust regression model and a robust platform serve different purposes."
        )
        [issue] = rule.check(content, "methods.md")

        assert content[issue.column - 1 : issue.end_column - 1] == "robust"
        assert content[issue.column - 1 :].startswith("robust platform")

    @pytest.mark.parametrize(
        "content",
        [
            "The kernel was implemented in C.",
            "The module implements the buffer protocol.",
            "The port is implementing the same interface.",
        ],
    )
    def test_preserves_technical_implement_forms(
        self, rule: AIVocabularyRule, content: str
    ) -> None:
        assert rule.check(content, "interfaces.md") == []

    @pytest.mark.parametrize(
        "form", ["implement", "implements", "implemented", "implementing"]
    )
    def test_generic_implement_forms_keep_review_and_safe_suggestions(
        self, rule: AIVocabularyRule, form: str
    ) -> None:
        source = {
            "implement": "The team will implement the migration plan.",
            "implements": "The team implements the migration plan.",
            "implemented": "The team implemented the migration plan.",
            "implementing": "The team is implementing the migration plan.",
        }[form]
        [issue] = rule.check(source, "plan.md")

        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == ("carry out" if form == "implement" else None)

    @pytest.mark.parametrize("style", ["markdown", "docstring", "comment"])
    @pytest.mark.parametrize(
        "text",
        [
            "The hash table stores each key with its value.",
            "The dictionary key identifies the entry.",
            "The foreign key references the row.",
            "The cache key identifies this response.",
            "The result is statistically significant at this threshold.",
            "The fundamental theorem of calculus relates the operations.",
            "The fundamental theorem of algebra describes the roots.",
            "The adapter implements the buffer protocol.",
            "The adapter implements the same interface.",
            "The kernel was implemented in C.",
            "The kernel was implemented in `C`.",
            "The kernel was implemented in C++.",
            "The kernel was implemented in Rust.",
        ],
    )
    def test_named_technical_terms_are_preserved_in_prose_contexts(
        self, rule: AIVocabularyRule, text: str, style: str
    ) -> None:
        if style == "markdown":
            content, filename = text, "guide.md"
        elif style == "docstring":
            content, filename = f'"""{text}"""', "guide.py"
        else:
            content, filename = f"# {text}", "guide.py"

        assert rule.check(content, filename) == []

    @pytest.mark.parametrize(
        "style", ["markdown", "docstring", "comment", "blockquote"]
    )
    @pytest.mark.parametrize(
        "text",
        [
            "Use ROBUST\nREGRESSION for this fit.",
            "The result is statistically\nsignificant at this threshold.",
            "The fundamental theorem\nof calculus describes this relation.",
            "The adapter implements\nthe buffer protocol.",
            "The hash table stores each\nkey with its value.",
            "The kernel was implemented\nin C.",
        ],
    )
    def test_technical_context_survives_layout_wrapping(
        self, rule: AIVocabularyRule, text: str, style: str
    ) -> None:
        if style == "markdown":
            content, filename = text, "guide.md"
        elif style == "docstring":
            content, filename = f'"""{text}"""', "guide.py"
        else:
            prefix = "# " if style == "comment" else "> "
            content = "\n".join(prefix + line for line in text.splitlines())
            filename = "guide.py" if style == "comment" else "guide.md"

        assert rule.check(content, filename) == []

    @pytest.mark.parametrize(
        ("text", "word"),
        [
            ("A key benefit of the hash table is lookup speed.", "key"),
            ("The hash table stores each key benefit for the slide.", "key"),
            ("The result is a significant improvement.", "significant"),
            ("This is a fundamental change.", "fundamental"),
            ("The plan was implemented in C-suite priorities.", "implemented"),
            ("The adapter implements the business protocol.", "implements"),
            ("The procedure uses robust defaults.", "robust"),
            ("A robust `hidden` regression model is discussed.", "robust"),
            ("The result is statistically `hidden` significant.", "significant"),
            ("The fundamental theorem\n\nof calculus is discussed.", "fundamental"),
        ],
    )
    def test_generic_and_disconnected_near_misses_keep_their_findings(
        self, rule: AIVocabularyRule, text: str, word: str
    ) -> None:
        issues = rule.check(text, "guide.md")

        assert [issue.message.split("'")[1] for issue in issues] == [word]

    @pytest.mark.parametrize(
        ("text", "word"),
        [
            ("The dictionary key identifies a key benefit.", "key"),
            (
                "A statistically significant result differs from a significant improvement.",
                "significant",
            ),
            (
                "The fundamental theorem of calculus is fundamental to this result.",
                "fundamental",
            ),
            (
                "A robust regression model and robust defaults serve different purposes.",
                "robust",
            ),
            (
                "The module implements the buffer protocol and implements the migration plan.",
                "implements",
            ),
        ],
    )
    def test_technical_occurrence_does_not_hide_a_generic_use_in_the_same_clause(
        self, rule: AIVocabularyRule, text: str, word: str
    ) -> None:
        [issue] = rule.check(text, "guide.md")

        assert issue.column == text.rindex(word) + 1
        assert issue.end_column == issue.column + len(word)

    def test_configured_allowed_phrase_still_exempts_its_entire_line(self) -> None:
        rule = AIVocabularyRule(allowed_phrases={"robust regression"})

        assert (
            rule.check("Use robust regression and delve into the fit.", "guide.md")
            == []
        )

    def test_plain_blockquotes_keep_generic_vocabulary_findings(self) -> None:
        [issue] = AIVocabularyRule().check(
            "> The team will delve into the topic.", "guide.md"
        )

        assert issue.rule_id == "V001"

    def test_case_matching_keeps_original_unicode_source_columns(self) -> None:
        content = "İ/O exposes a key benefit."

        [issue] = AIVocabularyRule().check(content, "guide.md")

        assert content[issue.column - 1 : issue.end_column - 1] == "key"

    def test_base_implement_retains_its_suggestion(
        self, rule: AIVocabularyRule
    ) -> None:
        [issue] = rule.check("We will implement the migration plan.", "plan.md")

        assert issue.suggestion == "carry out"

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


class TestVocabularyContextReview:
    @pytest.mark.parametrize("rule", [AIVocabularyRule(), PromotionalLanguageRule()])
    def test_quote_typography_keeps_raw_findings(self, rule: Rule) -> None:
        content = '> The customer wrote, "A groundbreaking result."'

        assert len(rule.check(content, "guide.md")) == 1

    def test_explicit_quote_suppression_is_narrow_and_preserves_raw_findings(
        self,
    ) -> None:
        from pathlib import Path

        from proseprobe.core.linter import Linter

        content = (
            '<!-- proseprobe-ignore-next-line V001 -->\n> The customer wrote, "We will delve into the topic."\n\n'
            "> We will delve into the topic.\n"
        )
        rule = AIVocabularyRule()
        assert len(rule.check(content, "guide.md")) == 2
        linter = Linter(Config(select=["V001"]))
        linter.register_rule(rule)

        [issue] = linter.check_content(content, Path("guide.md"))

        assert issue.rule_id == "V001"
        assert issue.line == 4

    @pytest.mark.parametrize(
        ("rule", "generic", "supported"),
        [
            (
                WeaselWordsRule(),
                "Experts say the bridge needs repairs.",
                "Experts say the bridge needs repairs. Structural engineers Mina Ortiz and Paul Chen published their measurements on July 18.",
            ),
            (
                TrendOverclaimRule(),
                "A growing number of weekday trips use the eastern line.",
                "A growing number of weekday trips use the eastern line. The share rose from 31.2% to 34.8% between January and July.",
            ),
        ],
    )
    def test_following_journalism_evidence_lowers_confidence_without_claiming_proof(
        self, rule: Rule, generic: str, supported: str
    ) -> None:
        [generic_issue] = rule.check(generic, "report.md")
        [supported_issue] = rule.check(supported, "report.md")

        assert generic_issue.confidence is Confidence.MEDIUM
        assert supported_issue.confidence is Confidence.LOW
        assert supported_issue.line == generic_issue.line == 1
        assert supported_issue.column == generic_issue.column


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

    def test_dive_into_has_one_longest_match(
        self, rule: CollaborativePhrasesRule
    ) -> None:
        source = "Let's dive into the API."

        [issue] = rule.check(source, "test.md")

        assert issue.message == "Collaborative phrase: 'Let's dive into'"
        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            1,
            1,
            None,
            16,
        )
        assert issue.severity is Severity.WARNING
        assert issue.confidence is Confidence.MEDIUM

    def test_partly_overlapping_phrases_have_one_longest_owner(
        self, rule: CollaborativePhrasesRule
    ) -> None:
        [issue] = rule.check("Just circling back on the proposal.", "test.md")

        assert issue.message == "Collaborative phrase: 'just circling back'"
        assert (issue.column, issue.end_column) == (1, 19)

    def test_wrapping_does_not_change_overlapping_phrase_ownership(
        self, rule: CollaborativePhrasesRule
    ) -> None:
        [issue] = rule.check("Just circling back\n    on the proposal.", "test.md")

        assert issue.message == "Collaborative phrase: 'just circling back'"
        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            1,
            1,
            None,
            19,
        )

    def test_repeated_nonoverlapping_phrases_follow_source_order(
        self, rule: CollaborativePhrasesRule
    ) -> None:
        source = "Let's dive into A; let's dive into B; I hope this helps."

        issues = rule.check(source, "test.md")

        assert [
            source[issue.column - 1 : issue.end_column - 1] for issue in issues
        ] == ["Let's dive into", "let's dive into", "I hope this helps"]

    @pytest.mark.parametrize(
        ("source", "filename", "start", "end"),
        [
            ("Let's dive\ninto the API.", "test.md", (1, 1), (2, 5)),
            ("> Let's dive\n> into the API.", "test.md", (1, 3), (2, 7)),
            ('"""Let\'s dive\ninto the API."""', "test.py", (1, 4), (2, 5)),
            ("# Let's dive\n# into the API.", "test.py", (1, 3), (2, 7)),
        ],
    )
    def test_wrapped_phrase_has_exact_source_endpoints(
        self,
        rule: CollaborativePhrasesRule,
        source: str,
        filename: str,
        start: tuple[int, int],
        end: tuple[int, int],
    ) -> None:
        [issue] = rule.check(source, filename)

        assert issue.message == "Collaborative phrase: 'Let's dive into'"
        assert (issue.line, issue.column) == start
        assert (issue.end_line, issue.end_column) == end

    @pytest.mark.parametrize(
        "source",
        [
            "Let's dive inside the API.",
            "Let's dive intoits details.",
            "Mallet's dive into the API.",
            "Let's dive `mode` into the API.",
            "Let's dive <code>mode</code> into the API.",
            "Let's dive\n\ninto the API.",
            "- Let's dive\n- into the API.",
            "Let's dive\n\n# into the API",
            "Use `Let's dive into` as the label.",
            "```text\nLet's dive into the API.\n```",
        ],
    )
    def test_phrase_boundaries_and_masked_gaps_do_not_create_matches(
        self, rule: CollaborativePhrasesRule, source: str
    ) -> None:
        assert rule.check(source, "test.md") == []

    def test_punctuation_ending_callouts_keep_their_original_messages(
        self, rule: CollaborativePhrasesRule
    ) -> None:
        issues = rule.check("Certainly! Absolutely!", "test.md")

        assert [issue.message for issue in issues] == [
            "Collaborative phrase: 'Certainly!'",
            "Collaborative phrase: 'Absolutely!'",
        ]

    @pytest.mark.parametrize(
        ("selected", "ignored", "expected"),
        [
            ("V002", None, ["V002"]),
            ("G009", None, ["G009"]),
            ("V002,G009", None, ["G009", "V002"]),
            ("V002,G009", "V002", ["G009"]),
        ],
    )
    def test_explicit_selections_preserve_each_diagnostic_id(
        self, selected: str, ignored: str | None, expected: list[str]
    ) -> None:
        from pathlib import Path

        from proseprobe.core.policy import prepare_scan

        _, linter, _ = prepare_scan(
            Config(), select=selected, ignore=ignored, severity="info"
        )

        issues = linter.check_content("Let's dive into the API.", Path("test.md"))

        assert [issue.rule_id for issue in issues] == expected
        assert all((issue.column, issue.end_column) == (1, 16) for issue in issues)

    def test_suppression_preserves_the_other_selected_rule_on_a_wrapped_phrase(
        self,
    ) -> None:
        from pathlib import Path

        from proseprobe.core.policy import prepare_scan

        _, linter, _ = prepare_scan(Config(), select="V002,G009", severity="info")
        source = "<!-- proseprobe-ignore-next-line V002 -->\nLet's dive\ninto the API."

        [issue] = linter.check_content(source, Path("test.md"))

        assert issue.rule_id == "G009"
        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            2,
            1,
            3,
            5,
        )


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
        ],
    )
    def test_suppresses_explicit_local_comparisons(self, source: str) -> None:
        assert UnboundedSuperlativeRule().check(source, "guide.md") == []

    @pytest.mark.parametrize(
        "source",
        [
            "Release 4 is the fastest parser.",
            "The server listens on port 443. Atlas is the fastest parser.",
            "The release shipped in June 2026. Atlas is the fastest parser.",
            "John Smith reviewed the release. Atlas is the fastest parser.",
            "Read [the report](https://example.com). Atlas is the fastest parser.",
            "Atlas is the fastest parser. Boreal processed 100 requests in 12 ms.",
            "Atlas processed 100 requests in 12 ms. It is the fastest.",
            "Mina Ortiz reported that Atlas is the most reliable.",
            "Atlas is fastest when the port is between 443 and 444.",
            "When the port is between 443 and 444, Atlas is fastest.",
            "Atlas is fastest among.",
            "Of the, Atlas is fastest.",
        ],
    )
    def test_unrelated_metadata_or_evidence_does_not_bound_the_claim(
        self, source: str
    ) -> None:
        [issue] = UnboundedSuperlativeRule().check(source, "guide.md")

        assert issue.confidence is Confidence.LOW

    def test_comparison_set_applies_only_to_its_own_claim(self) -> None:
        source = (
            "Atlas is fastest among the three parsers, but Boreal is the most reliable."
        )

        [issue] = UnboundedSuperlativeRule().check(source, "guide.md")

        assert source[issue.column - 1 : issue.end_column - 1] == "the most reliable"

    @pytest.mark.parametrize(
        "source",
        [
            "In this benchmark, Atlas was fastest among the three tested parsers.",
            "Among the parsers and compilers, Atlas is the most reliable.",
        ],
    )
    def test_direct_scope_and_metric_qualify_the_comparison(self, source: str) -> None:
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
        ],
    )
    def test_suppresses_concrete_test_bounds(self, source: str) -> None:
        assert AbsoluteReliabilityClaimRule().check(source, "guide.md") == []

    @pytest.mark.parametrize(
        "source",
        [
            "The parser was tested over 100 runs. The parser never fails.",
            "We observed no failures in 5,000 requests. The parser eliminates all errors.",
            "The parser never fails. The server was tested over 100 runs.",
            "The parser never fails; the server was tested over 100 runs.",
            "The parser never fails, while the server was tested over 100 runs.",
            "The parser never failed during those 100 runs, but the parser never fails.",
        ],
    )
    def test_finite_or_unrelated_testing_does_not_validate_a_universal_claim(
        self, source: str
    ) -> None:
        [issue] = AbsoluteReliabilityClaimRule().check(source, "guide.md")

        assert issue.confidence is Confidence.MEDIUM

    def test_mixed_bounded_and_unbounded_claims_keep_the_unbounded_finding(
        self,
    ) -> None:
        source = "The parser never fails during 100 test runs, but the gateway is 100% secure."

        [issue] = AbsoluteReliabilityClaimRule().check(source, "guide.md")

        assert source[issue.column - 1 : issue.end_column - 1] == "100% secure"

    @pytest.mark.parametrize(
        "source",
        [
            "The parser never failed during those 100 runs.",
            "The parser never fails during those 100 runs.",
            "Across 100 tests and 50 trials, the parser never fails.",
            "The parser never fails under the tested configuration.",
            "The parser never fails during 10,000 runs.",
        ],
    )
    def test_bound_qualifies_the_same_observation(self, source: str) -> None:
        assert AbsoluteReliabilityClaimRule().check(source, "guide.md") == []

    def test_unclear_testing_scope_remains_a_lower_confidence_prompt(self) -> None:
        [issue] = AbsoluteReliabilityClaimRule().check(
            "The parser never fails in our tests.", "guide.md"
        )

        assert issue.confidence is Confidence.LOW

    def test_neighboring_testing_does_not_shift_wrapped_claim_coordinates(self) -> None:
        source = "The parser was tested over 100 runs.\nThe parser never\nfails."

        [issue] = AbsoluteReliabilityClaimRule().check(source, "guide.md")

        assert (issue.line, issue.column) == (2, 12)
        assert (issue.end_line, issue.end_column) == (3, 6)
        assert issue.message == "Absolute reliability claim: 'never fails'"

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


class TestPromotionalPhraseWrapping:
    """Wrap-invariant literal catalog tests for V004."""

    @pytest.mark.parametrize("filename", ["case.md", "case.py"])
    def test_wrapping_preserves_promotional_metadata_and_endpoints(
        self, filename: str
    ) -> None:
        single = "The product is second to none."
        wrapped = "The product is second\nto none."
        if filename.endswith(".py"):
            single = f'"""{single}"""'
            wrapped = f'"""{wrapped}"""'

        [original] = PromotionalLanguageRule().check(single, filename)
        [issue] = PromotionalLanguageRule().check(wrapped, filename)

        assert (
            issue.message
            == original.message
            == "Promotional language: 'second to none'"
        )
        assert issue.severity is original.severity
        assert issue.confidence is original.confidence
        assert (issue.line, issue.column) == (1, 19 if filename.endswith(".py") else 16)
        assert (issue.end_line, issue.end_column) == (2, 8)

    @pytest.mark.parametrize("prefix", ["# ", "> "])
    def test_wrapping_keeps_documentation_prefix_columns(self, prefix: str) -> None:
        filename = "case.py" if prefix == "# " else "case.md"

        [issue] = PromotionalLanguageRule().check(
            f"{prefix}second\n{prefix}to none", filename
        )

        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            1,
            3,
            2,
            10,
        )

    @pytest.mark.parametrize(
        "gap", [" `mode` ", " <code>mode</code> ", "\n\n", "\n\n# "]
    )
    def test_masked_or_separate_regions_do_not_join(self, gap: str) -> None:
        assert (
            PromotionalLanguageRule().check("second" + gap + "to none.", "case.md")
            == []
        )


@pytest.mark.parametrize(
    ("rule", "single", "wrapped", "start_column", "end_column"),
    [
        (
            KnowledgeCutoffRule(),
            "As of my last update, it was accurate.",
            "As of my last\nupdate, it was accurate.",
            1,
            7,
        ),
        (
            WeaselWordsRule(),
            "Studies show this works.",
            "Studies\nshow this works.",
            1,
            5,
        ),
        (
            GrandioseStakesRule(),
            "This will fundamentally reshape the field.",
            "This will fundamentally\nreshape the field.",
            11,
            8,
        ),
    ],
)
@pytest.mark.parametrize("filename", ["case.md", "case.py"])
def test_regex_vocabulary_phrase_wrapping_preserves_diagnostics_and_spans(
    rule: Rule,
    single: str,
    wrapped: str,
    start_column: int,
    end_column: int,
    filename: str,
) -> None:
    if filename.endswith(".py"):
        single = f'"""{single}"""'
        wrapped = f'"""{wrapped}"""'
        start_column += 3

    [original] = rule.check(single, filename)
    [issue] = rule.check(wrapped, filename)

    assert issue.message == original.message
    assert issue.suggestion == original.suggestion
    assert issue.severity is original.severity
    assert issue.confidence is original.confidence
    assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
        1,
        start_column,
        2,
        end_column,
    )


@pytest.mark.parametrize(
    ("rule", "before", "after"),
    [
        (KnowledgeCutoffRule(), "As of my last", "update, it was accurate."),
        (WeaselWordsRule(), "Studies", "show this works."),
        (GrandioseStakesRule(), "This will fundamentally", "reshape the field."),
    ],
)
@pytest.mark.parametrize("gap", [" `mode` ", " <code>mode</code> ", "\n\n", "\n\n# "])
def test_regex_vocabulary_phrase_gaps_do_not_manufacture_a_match(
    rule: Rule, before: str, after: str, gap: str
) -> None:
    assert rule.check(before + gap + after, "case.md") == []


@pytest.mark.parametrize(
    ("rule", "before", "after", "start_column", "end_column"),
    [
        (KnowledgeCutoffRule(), "As of my last", "update, it was accurate.", 3, 9),
        (WeaselWordsRule(), "Studies", "show this works.", 3, 7),
        (
            GrandioseStakesRule(),
            "This will fundamentally",
            "reshape the field.",
            13,
            10,
        ),
    ],
)
@pytest.mark.parametrize("prefix", ["# ", "> "])
def test_regex_vocabulary_phrase_wrapping_retains_prefix_coordinates(
    rule: Rule, before: str, after: str, start_column: int, end_column: int, prefix: str
) -> None:
    filename = "case.py" if prefix == "# " else "case.md"

    [issue] = rule.check(f"{prefix}{before}\n{prefix}{after}", filename)

    assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
        1,
        start_column,
        2,
        end_column,
    )


def test_wrapped_weasel_phrase_keeps_following_evidence_confidence() -> None:
    evidence = " A survey measured 12% and 34%."
    [original] = WeaselWordsRule().check(
        "Studies show this works." + evidence, "case.md"
    )
    [issue] = WeaselWordsRule().check("Studies\nshow this works." + evidence, "case.md")

    assert original.confidence is issue.confidence is Confidence.LOW
    assert (issue.line, issue.column, issue.end_line, issue.end_column) == (1, 1, 2, 5)


@pytest.mark.parametrize(
    ("rule", "before", "after"),
    [
        (KnowledgeCutoffRule(), "As of my last", "update"),
        (WeaselWordsRule(), "Studies", "show"),
        (GrandioseStakesRule(), "fundamentally", "reshape"),
    ],
)
def test_invalid_masked_regex_candidate_does_not_hide_a_later_valid_match(
    rule: Rule, before: str, after: str
) -> None:
    source = f"{before} `mode` {after}, then {before} {after}."

    [issue] = rule.check(source, "case.md")

    assert source[issue.column - 1 : issue.end_column - 1] == f"{before} {after}"


@pytest.mark.parametrize(
    ("rule", "source"),
    [
        (
            KnowledgeCutoffRule(),
            "As of my last update, A worked. As of my last update, B worked.",
        ),
        (
            GrandioseStakesRule(),
            "This will fundamentally reshape A. This will fundamentally reshape B.",
        ),
    ],
)
def test_regex_migration_preserves_first_per_pattern_on_a_source_line(
    rule: Rule, source: str
) -> None:
    assert len(rule.check(source, "case.md")) == 1
