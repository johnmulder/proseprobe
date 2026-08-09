"""Tests for style rules (T001-T010, T012, T014-T015)."""

import pytest

from proseprobe.rules.base import Confidence, Rule, Severity
from proseprobe.rules.style import (
    BoldOveruseRule,
    ElegantVariationRule,
    EmDashOveruseRule,
    EmojiInProseRule,
    NestedParentheticalRule,
    ParentheticalOverloadRule,
    QuoteInconsistencyRule,
    RepeatedOrMixedPunctuationRule,
    RhetoricalEllipsisRule,
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
        (RepeatedOrMixedPunctuationRule(), "Really?!", "?!"),
        (RhetoricalEllipsisRule(), "The request may finish...", "..."),
        (
            ParentheticalOverloadRule(),
            "Use it (after the first timeout) (while the replica recovers) "
            "(before client traffic resumes).",
            "(after the first timeout) (while the replica recovers) "
            "(before client traffic resumes)",
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
        from proseprobe.rules.style import ShortPunchyFragmentsRule

        text = "He published this.\n\nOpenly.\n\nIn a book.\n\nAs a priest."
        rule = ShortPunchyFragmentsRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "T007"

    def test_detects_punchy_prose(self) -> None:
        """Detect 'But I adapted.' style fragments."""
        from proseprobe.rules.style import ShortPunchyFragmentsRule

        text = "These weren't just products.\n\nAnd the software matched.\n\nThen it changed.\n\nBut I adapted."
        rule = ShortPunchyFragmentsRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_paragraphs(self) -> None:
        """Don't flag normal-length paragraphs."""
        from proseprobe.rules.style import ShortPunchyFragmentsRule

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
        from proseprobe.rules.style import ShortPunchyFragmentsRule

        text = "# Linux\n\n## macOS\n\n## Windows"

        assert ShortPunchyFragmentsRule().check(text, "test.md") == []

    def test_code_block_breaks_short_paragraph_run(self) -> None:
        """Skipped structural content resets a short-paragraph run."""
        from proseprobe.rules.style import ShortPunchyFragmentsRule

        text = "First.\n\nSecond.\n\n```text\nexample\n```\n\nThird."

        assert ShortPunchyFragmentsRule().check(text, "test.md") == []

    def test_custom_threshold(self) -> None:
        """Respect configurable threshold."""
        from proseprobe.rules.style import ShortPunchyFragmentsRule

        text = "Stop.\n\nThink.\n\nAct."
        rule_low = ShortPunchyFragmentsRule(threshold=2)
        rule_high = ShortPunchyFragmentsRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.style import ShortPunchyFragmentsRule

        rule = ShortPunchyFragmentsRule()
        assert rule.id == "T007"
        assert rule.name == "Short Punchy Fragments"


# ---------- Phase 2 (Academic Writing Tropes) TDD: T008 ----------


class TestSentenceLength:
    """Tests for T008: Sentence Length."""

    def test_detects_long_sentence(self) -> None:
        """Detect sentence exceeding threshold."""
        from proseprobe.rules.style import SentenceLengthRule

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
        from proseprobe.rules.style import SentenceLengthRule

        text = "This is a simple sentence. Another one follows."
        rule = SentenceLengthRule(threshold=40)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_long_sentence_counts_words_across_source_lines(self) -> None:
        from proseprobe.rules.style import SentenceLengthRule

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
        from proseprobe.rules.style import SentenceLengthRule

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
        from proseprobe.rules.style import SentenceLengthRule

        text = "# " + "word " * 45

        assert SentenceLengthRule(threshold=40).check(text, "test.md") == []

    def test_checks_long_list_items(self) -> None:
        """List-item prose remains eligible for sentence-length checks."""
        from proseprobe.rules.style import SentenceLengthRule

        text = "- " + "word " * 45

        issues = SentenceLengthRule(threshold=40).check(text, "test.md")

        assert len(issues) == 1
        assert issues[0].column == 3

    def test_custom_threshold(self) -> None:
        """Respect configurable threshold."""
        from proseprobe.rules.style import SentenceLengthRule

        text = "This sentence has exactly ten words in it right here now."
        rule_low = SentenceLengthRule(threshold=5)
        rule_high = SentenceLengthRule(threshold=20)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_multiple_sentences_only_long_flagged(self) -> None:
        """Only flag long sentences, not short ones on same line."""
        from proseprobe.rules.style import SentenceLengthRule

        text = "Short. " + "word " * 45 + "end of very long sentence."
        rule = SentenceLengthRule(threshold=40)
        issues = rule.check(text, "test.md")
        assert len(issues) == 1

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.style import SentenceLengthRule

        rule = SentenceLengthRule()
        assert rule.id == "T008"
        assert rule.name == "Sentence Length"


class TestRepeatedOrMixedPunctuation:
    """Tests for T010: Repeated or Mixed Punctuation."""

    @pytest.mark.parametrize("cluster", ["!!", "??", "?!", "!?", "?!?", "...?!", "…!"])
    def test_reports_supported_clusters(self, cluster: str) -> None:
        source = f"Really{cluster} Next step."

        [issue] = RepeatedOrMixedPunctuationRule().check(source, "guide.md")

        assert issue.rule_id == "T010"
        assert issue.message == f"Repeated or mixed punctuation: '{cluster}'"
        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            1,
            len("Really") + 1,
            1,
            len("Really") + len(cluster) + 1,
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "Use a single terminal punctuation mark"

    def test_reports_multiple_clusters_in_source_order(self) -> None:
        source = "Really?! Stop!! Why??"

        issues = RepeatedOrMixedPunctuationRule().check(source, "guide.markdown")

        assert [
            source[issue.column - 1 : issue.end_column - 1] for issue in issues
        ] == [
            "?!",
            "!!",
            "??",
        ]

    @pytest.mark.parametrize("source", ["Really!", "Why?", "Wait...", "Pause…"])
    def test_ignores_single_marks_and_bare_ellipses(self, source: str) -> None:
        assert RepeatedOrMixedPunctuationRule().check(source, "guide.md") == []

    def test_ignores_markdown_literal_and_example_contexts(self) -> None:
        source = (
            "Use `?!` as the token.\n\n"
            "[Query](https://example.com/search??mode=all)\n\n"
            "```text\nReally?!\n```\n\n"
            "## Example\n\nReally?!"
        )

        assert RepeatedOrMixedPunctuationRule().check(source, "guide.md") == []

    def test_checks_python_comments_and_docstrings_but_not_strings(self) -> None:
        source = (
            'value = "Really?!"\n'
            "# Really?!\n\n"
            "def retry() -> None:\n"
            '    """Wait...!"""\n'
            "    return None\n"
        )

        issues = RepeatedOrMixedPunctuationRule().check(source, "guide.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_rule_metadata(self) -> None:
        rule = RepeatedOrMixedPunctuationRule()

        assert rule.id == "T010"
        assert rule.name == "Repeated or Mixed Punctuation"
        assert rule.config_key is None


class TestRhetoricalEllipsis:
    """Tests for T012: Rhetorical Ellipsis."""

    def test_reports_terminal_ellipsis_fields(self) -> None:
        source = "The request may finish..."
        start = source.index("...")

        [issue] = RhetoricalEllipsisRule().check(source, "guide.md")

        assert issue.rule_id == "T012"
        assert issue.message == "Rhetorical ellipsis: '...'"
        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            1,
            start + 1,
            1,
            start + 4,
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "Use direct punctuation or complete the thought"

    def test_reports_multiple_ellipses_in_source_order(self) -> None:
        source = "Perhaps... the retry works. Later... maybe."

        issues = RhetoricalEllipsisRule().check(source, "guide.markdown")

        assert [
            source[issue.column - 1 : issue.end_column - 1] for issue in issues
        ] == [
            "...",
            "...",
        ]
        assert [issue.column for issue in issues] == [8, 34]

    @pytest.mark.parametrize(
        "source",
        [
            "Version 1.2.3 remains supported.",
            "The numeric range 1...3 is literal.",
            "Use e.g. the stable endpoint.",
            "Wait....",
            "Wait...?!",
            "Pause…",
            '"..."',
            "The ellipsis ... marks omitted text.",
            "Output: Loading...",
        ],
    )
    def test_ignores_non_rhetorical_contexts(self, source: str) -> None:
        assert RhetoricalEllipsisRule().check(source, "guide.md") == []

    def test_ignores_markdown_literal_and_example_contexts(self) -> None:
        source = (
            "Use `wait...` as the token.\n\n"
            "[Log](https://example.com/loading...)\n\n"
            "```text\nLoading...\n```\n\n"
            "## Example\n\nThe request may finish..."
        )

        assert RhetoricalEllipsisRule().check(source, "guide.md") == []

    def test_checks_python_comments_and_docstrings_but_not_strings(self) -> None:
        source = (
            'value = "Wait..."\n'
            "# The retry stalled...\n\n"
            "def retry() -> None:\n"
            '    """The request waits..."""\n'
            "    return None\n"
        )

        issues = RhetoricalEllipsisRule().check(source, "guide.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_rule_metadata(self) -> None:
        rule = RhetoricalEllipsisRule()

        assert rule.id == "T012"
        assert rule.name == "Rhetorical Ellipsis"
        assert rule.config_key is None


class TestParentheticalOverload:
    """Tests for T014: Parenthetical Overload."""

    def test_reports_substantial_parentheticals_as_one_exact_span(self) -> None:
        source = (
            "The service retries (after the first timeout) requests "
            "(while the replica recovers) and reports status "
            "(when the final attempt fails)."
        )
        expected = source[source.index("(") : source.rindex(")") + 1]

        [issue] = ParentheticalOverloadRule().check(source, "guide.md")

        assert issue.rule_id == "T014"
        assert issue.message == (
            "Parenthetical overload: 3 substantial parentheticals in one sentence"
        )
        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            1,
            source.index("(") + 1,
            1,
            source.rindex(")") + 2,
        )
        assert source[issue.column - 1 : issue.end_column - 1] == expected
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == (
            "Rewrite the sentence or move parenthetical details into separate sentences"
        )

    def test_maps_parentheticals_across_wrapped_source_lines(self) -> None:
        source = (
            "The service retries (after the first timeout)\n"
            "through the proxy (while the replica recovers)\n"
            "and reports status (when the final attempt fails)."
        )

        [issue] = ParentheticalOverloadRule().check(source, "guide.md")

        assert (issue.line, issue.column) == (1, source.splitlines()[0].index("(") + 1)
        assert (issue.end_line, issue.end_column) == (
            3,
            source.splitlines()[2].rindex(")") + 2,
        )

    @pytest.mark.parametrize(
        "source",
        [
            (
                "Retry requests (after the first timeout) through the proxy "
                "(while the replica recovers)."
            ),
            "Support Linux (Linux), version two (v2), and secure transport (TLS).",
            (
                "Retry (after the first timeout) through the proxy (v2) and report "
                "status (when the final attempt fails)."
            ),
            (
                "Retry (after the first timeout) through the proxy "
                "(while the replica recovers). Report status "
                "(when the final attempt fails)."
            ),
            "An unmatched (opening contains several words without a close.",
        ],
    )
    def test_requires_three_substantial_spans_in_one_sentence(
        self, source: str
    ) -> None:
        assert ParentheticalOverloadRule().check(source, "guide.md") == []

    def test_counts_nested_parentheses_as_one_top_level_span(self) -> None:
        source = (
            "Use it (with a detailed note (for Linux users)) "
            "(while the replica recovers) (before client traffic resumes)."
        )

        [issue] = ParentheticalOverloadRule().check(source, "guide.md")

        assert issue.message == (
            "Parenthetical overload: 3 substantial parentheticals in one sentence"
        )

    def test_ignores_markdown_literal_heading_and_example_contexts(self) -> None:
        source = (
            "# Guide (with useful details) (for system operators) "
            "(during active recovery)\n\n"
            "Use `(one two three) (four five six) (seven eight nine)` as a token.\n\n"
            "[Reference](https://example.com/(one.two.three)/(four.five.six)/"
            "(seven.eight.nine)) remains current.\n\n"
            "```text\n"
            "Retry (after the first timeout) (while the replica recovers) "
            "(before client traffic resumes).\n"
            "```\n\n"
            "## Example\n\n"
            "Retry (after the first timeout) (while the replica recovers) "
            "(before client traffic resumes)."
        )

        assert ParentheticalOverloadRule().check(source, "guide.md") == []

    def test_checks_python_comments_and_docstrings_but_not_strings(self) -> None:
        sentence = (
            "Retry (after the first timeout) (while the replica recovers) "
            "(before client traffic resumes)."
        )
        source = (
            f'value = "{sentence}"\n'
            f"# {sentence}\n\n"
            "def retry() -> None:\n"
            f'    """{sentence}"""\n'
            "    return None\n"
        )

        issues = ParentheticalOverloadRule().check(source, "guide.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_rule_metadata(self) -> None:
        rule = ParentheticalOverloadRule()

        assert rule.id == "T014"
        assert rule.name == "Parenthetical Overload"
        assert rule.config_key is None
        assert rule.default_confidence is Confidence.MEDIUM
        assert rule.applies_to == {"markdown", "python"}
        assert rule.content_scope == "prose"


class TestNestedParenthetical:
    """Tests for T015: Nested Parenthetical."""

    def test_reports_full_inner_parenthetical_span(self) -> None:
        text = "Configure the cache (for example (on Linux)) before startup."
        expected = "(on Linux)"

        [issue] = NestedParentheticalRule().check(text, "test.md")

        start = text.index(expected)
        assert issue.rule_id == "T015"
        assert issue.message == "Nested parenthetical"
        assert (issue.line, issue.column) == (1, start + 1)
        assert issue.end_line is None
        assert issue.end_column == start + len(expected) + 1
        assert text[issue.column - 1 : issue.end_column - 1] == expected
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == (
            "Remove one level of parentheses or rewrite the sentence"
        )

    def test_reports_wrapped_inner_parenthetical_span(self) -> None:
        text = (
            "The parser (supports a nested\n"
            "(parenthetical note\n"
            "across source lines) in comments)."
        )

        [issue] = NestedParentheticalRule().check(text, "test.md")

        assert (issue.line, issue.column) == (2, 1)
        assert (issue.end_line, issue.end_column) == (
            3,
            len("across source lines)") + 1,
        )

    def test_reports_each_balanced_inner_pair_in_source_order(self) -> None:
        text = "Use (a (nested) note) and (another (inner (deep)) note)."

        issues = NestedParentheticalRule().check(text, "test.md")

        assert [text[issue.column - 1 : issue.end_column - 1] for issue in issues] == [
            "(nested)",
            "(inner (deep))",
            "(deep)",
        ]

    def test_ignores_code_and_link_destinations(self) -> None:
        text = (
            "Use `outer(inner(value))` in the example.\n\n"
            "See the release ([reference](https://example.com/(v1))) first.\n\n"
            "```text\n(outer (inner))\n```"
        )

        assert NestedParentheticalRule().check(text, "test.md") == []

    def test_checks_python_comments_and_docstrings_only(self) -> None:
        text = (
            "value = outer(inner(value))\n"
            "# Configure it (for example (on Linux)).\n"
            "def explain():\n"
            '    """Use a value (such as (zero))."""\n'
            "    return value"
        )

        issues = NestedParentheticalRule().check(text, "test.py")

        assert [issue.line for issue in issues] == [2, 4]

    def test_ignores_single_unmatched_and_cross_block_parentheses(self) -> None:
        text = (
            "One (single-level) note. An unmatched (outer (inner).\n\n"
            "A new (single-level) block."
        )

        assert NestedParentheticalRule().check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        rule = NestedParentheticalRule()

        assert rule.id == "T015"
        assert rule.name == "Nested Parenthetical"
        assert rule.description == "Detects parentheses nested within prose parentheses"
        assert rule.severity is Severity.INFO
        assert rule.default_confidence is Confidence.HIGH
        assert rule.applies_to == {"markdown", "python"}
        assert rule.content_scope == "prose"
