"""Tests for style rules (T001-T006)."""

import pytest

from slop_lint.rules.base import Rule
from slop_lint.rules.style import (
    BoldOveruseRule,
    ElegantVariationRule,
    EmDashOveruseRule,
    EmojiInProseRule,
    QuoteInconsistencyRule,
    TitleCaseHeadingsRule,
)


@pytest.mark.parametrize(
    ("rule", "source", "expected"),
    [
        (
            TitleCaseHeadingsRule(),
            "## Reliable System Design",
            "Reliable System Design",
        ),
        (
            QuoteInconsistencyRule(),
            'He said "hello" and “goodbye”.',
            "“",
        ),
        (EmojiInProseRule(), "Ship it 🚀 today.", "🚀"),
        (
            ElegantVariationRule(),
            "The guide said this. The reference stated that.",
            "stated",
        ),
    ],
)
def test_style_rules_report_exact_source_spans(
    rule: Rule,
    source: str,
    expected: str,
) -> None:
    [issue] = rule.check(source, "test.md")

    assert issue.end_column is not None
    assert source[issue.column - 1 : issue.end_column - 1] == expected


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

    def test_custom_threshold(self) -> None:
        """Test rule respects custom threshold."""
        # 4 bold phrases - should trigger with threshold=3, not with threshold=5
        text = "This is **one** and **two** and **three** and **four**."
        rule_low = BoldOveruseRule(threshold=3)
        rule_high = BoldOveruseRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) == 1
        assert len(issues_high) == 0


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

    def test_custom_threshold(self) -> None:
        """Test rule respects custom threshold."""
        # 6 em dashes - should trigger with threshold=5, not with threshold=10
        text = "One—two—three—four—five—six—seven"
        rule_low = EmDashOveruseRule(threshold=5)
        rule_high = EmDashOveruseRule(threshold=10)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) == 1
        assert len(issues_high) == 0


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

    def test_detects_mixed_curly_straight(self) -> None:
        """Test detecting mixed curly and straight quotes."""
        # Content with both straight " and curly " quotes
        text = 'He said "hello" and \u201cgoodbye\u201d'
        rule = QuoteInconsistencyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 1
        assert "Mixed quote" in issues[0].message


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

    def test_elegant_variation_stays_within_one_prose_scope(self) -> None:
        local = (
            "The first status message said the retry failed. "
            "The second stated that it did not succeed."
        )
        unrelated = (
            "The release notes said the retry changed.\n\n"
            "A later academic paragraph noted a limitation."
        )

        assert len(ElegantVariationRule().check(local, "test.md")) == 1
        assert ElegantVariationRule().check(unrelated, "test.md") == []

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = ElegantVariationRule()
        assert rule.id == "T006"


# ---------- Phase 10 TDD: T007 ----------


class TestShortPunchyFragments:
    """Tests for T007: Short Punchy Fragments."""

    def test_detects_consecutive_short_paras(self) -> None:
        """Detect 3+ consecutive short-sentence paragraphs."""
        from slop_lint.rules.style import ShortPunchyFragmentsRule

        text = "He published this.\n\nOpenly.\n\nIn a book.\n\nAs a priest."
        rule = ShortPunchyFragmentsRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "T007"

    def test_detects_punchy_prose(self) -> None:
        """Detect 'But I adapted.' style fragments."""
        from slop_lint.rules.style import ShortPunchyFragmentsRule

        text = "These weren't just products.\n\nAnd the software matched.\n\nThen it changed.\n\nBut I adapted."
        rule = ShortPunchyFragmentsRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_paragraphs(self) -> None:
        """Don't flag normal-length paragraphs."""
        from slop_lint.rules.style import ShortPunchyFragmentsRule

        text = (
            "The system provides reliable error handling and comprehensive logging.\n\n"
            "Users can configure retry policies and timeout settings through the TOML file.\n\n"
            "The caching layer reduces database queries by approximately forty percent."
        )
        rule = ShortPunchyFragmentsRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_short_headings(self) -> None:
        """Consecutive short headings are not punchy prose paragraphs."""
        from slop_lint.rules.style import ShortPunchyFragmentsRule

        text = "# Linux\n\n## macOS\n\n## Windows"

        assert ShortPunchyFragmentsRule().check(text, "test.md") == []

    def test_code_block_breaks_short_paragraph_run(self) -> None:
        """Skipped structural content resets a short-paragraph run."""
        from slop_lint.rules.style import ShortPunchyFragmentsRule

        text = "First.\n\nSecond.\n\n```text\nexample\n```\n\nThird."

        assert ShortPunchyFragmentsRule().check(text, "test.md") == []

    def test_custom_threshold(self) -> None:
        """Respect configurable threshold."""
        from slop_lint.rules.style import ShortPunchyFragmentsRule

        text = "Stop.\n\nThink.\n\nAct."
        rule_low = ShortPunchyFragmentsRule(threshold=2)
        rule_high = ShortPunchyFragmentsRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.style import ShortPunchyFragmentsRule

        rule = ShortPunchyFragmentsRule()
        assert rule.id == "T007"
        assert rule.name == "Short Punchy Fragments"


# ---------- Phase 2 (Academic Writing Tropes) TDD: T008 ----------


class TestSentenceLength:
    """Tests for T008: Sentence Length."""

    def test_detects_long_sentence(self) -> None:
        """Detect sentence exceeding threshold."""
        from slop_lint.rules.style import SentenceLengthRule

        # 45-word sentence
        text = (
            "In considering the implications of the findings which themselves "
            "arise from a complex interaction of factors that are not easily "
            "reducible to simple causal explanations we must also consider the "
            "broader context in which these results were obtained and the "
            "various methodological limitations that constrain our interpretations."
        )
        rule = SentenceLengthRule(threshold=40)
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "T008"

    def test_ignores_short_sentence(self) -> None:
        """Don't flag short sentences."""
        from slop_lint.rules.style import SentenceLengthRule

        text = "This is a simple sentence. Another one follows."
        rule = SentenceLengthRule(threshold=40)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_long_sentence_counts_words_across_source_lines(self) -> None:
        from slop_lint.rules.style import SentenceLengthRule

        text = "One two three four five\nsix seven eight nine ten."

        [issue] = SentenceLengthRule(threshold=8).check(text, "test.md")

        assert issue.message == "Long sentence: 10 words (threshold 8)"
        assert (issue.line, issue.column) == (1, 1)
        assert (issue.end_line, issue.end_column) == (
            2,
            len("six seven eight nine ten.") + 1,
        )

    def test_ignores_code_blocks(self) -> None:
        """Don't flag long lines inside code blocks."""
        from slop_lint.rules.style import SentenceLengthRule

        text = (
            "Short intro sentence.\n\n"
            "```python\n"
            "# This is a very long comment line that would normally exceed the threshold "
            "if it were counted as prose but it should not be because it is inside a code "
            "block and code blocks should be excluded from sentence length checking.\n"
            "```\n\n"
            "Short conclusion."
        )
        rule = SentenceLengthRule(threshold=20)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_long_heading(self) -> None:
        """Sentence length applies to prose contexts, not headings."""
        from slop_lint.rules.style import SentenceLengthRule

        text = "# " + "word " * 45

        assert SentenceLengthRule(threshold=40).check(text, "test.md") == []

    def test_checks_long_list_items(self) -> None:
        """List-item prose remains eligible for sentence-length checks."""
        from slop_lint.rules.style import SentenceLengthRule

        text = "- " + "word " * 45

        issues = SentenceLengthRule(threshold=40).check(text, "test.md")

        assert len(issues) == 1
        assert issues[0].column == 3

    def test_custom_threshold(self) -> None:
        """Respect configurable threshold."""
        from slop_lint.rules.style import SentenceLengthRule

        text = "This sentence has exactly ten words in it right here now."
        rule_low = SentenceLengthRule(threshold=5)
        rule_high = SentenceLengthRule(threshold=20)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_multiple_sentences_only_long_flagged(self) -> None:
        """Only flag long sentences, not short ones on same line."""
        from slop_lint.rules.style import SentenceLengthRule

        text = "Short. " + "word " * 45 + "end of very long sentence."
        rule = SentenceLengthRule(threshold=40)
        issues = rule.check(text, "test.md")
        assert len(issues) == 1

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.style import SentenceLengthRule

        rule = SentenceLengthRule()
        assert rule.id == "T008"
        assert rule.name == "Sentence Length"
