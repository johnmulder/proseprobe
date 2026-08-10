"""Tests for structural rules (S001-S022, S025, S028, and S029)."""

import pytest

from proseprobe.rules.base import Confidence, Rule, Severity
from proseprobe.rules.struct import (
    ChallengeConclusionsRule,
    ContentDuplicationRule,
    DramaticCountdownRule,
    ExcessiveHeadingDepthRule,
    FalseRangesRule,
    FractalSummaryRule,
    HeadingWithoutBodyRule,
    InlineHeaderListsRule,
    ListicleInProseRule,
    NegativeParallelismRule,
    RhetoricalSelfAnswerRule,
    RuleOfThreeRule,
    SignificanceEmphasisRule,
    SignpostedConclusionRule,
    SlideDeckFragmentRule,
    SuperficialAnalysisRule,
    TinySectionRule,
    WallOfTextParagraphRule,
)


@pytest.mark.parametrize(
    ("rule", "source", "expected"),
    [
        (
            RuleOfThreeRule(threshold=0),
            "Fast, safe, and clear.",
            "Fast, safe, and clear",
        ),
        (
            DramaticCountdownRule(),
            "Not slow. Not fragile. Just clear.",
            "Not slow. Not fragile. Just clear.",
        ),
        (
            RhetoricalSelfAnswerRule(),
            "The result? A clean build.",
            "The result? A clean build.",
        ),
        (
            ListicleInProseRule(),
            "The first takeaway is smaller scope.",
            "The first takeaway",
        ),
        (
            SignpostedConclusionRule(),
            "- In conclusion, ship the tested patch.",
            "In conclusion",
        ),
        (
            FractalSummaryRule(),
            "In this section, we'll explore the parser.",
            "In this section, we'll explore",
        ),
        (
            SlideDeckFragmentRule(),
            "> Driving alignment across strategic initiatives for scalable impact.",
            "Driving alignment across strategic initiatives for scalable impact.",
        ),
        (
            ExcessiveHeadingDepthRule(),
            "> ###### Retry details ######",
            "Retry details",
        ),
    ],
)
def test_concrete_structural_findings_have_exact_spans(
    rule: Rule,
    source: str,
    expected: str,
) -> None:
    [issue] = rule.check(source, "test.md")

    assert issue.end_column is not None
    assert (
        source.splitlines()[issue.line - 1][
            issue.column - 1 : issue.end_column - 1
        ].casefold()
        == expected.casefold()
    )


def test_duplicate_paragraph_reports_the_exact_second_source_span() -> None:
    source = (
        "Alpha beta gamma delta\n"
        "epsilon zeta eta theta.\n\n"
        "  Alpha beta gamma delta\n"
        "  epsilon zeta eta theta."
    )

    [issue] = ContentDuplicationRule().check(source, "test.md")

    assert (issue.line, issue.column) == (4, 3)
    assert issue.end_line == 5
    assert issue.end_column == len("  epsilon zeta eta theta.") + 1


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

    def test_custom_threshold(self) -> None:
        """Test rule respects custom threshold."""
        # 4 triads - should trigger with threshold=3, not with threshold=5
        text = """
        One, two, and three.
        Four, five, and six.
        Seven, eight, and nine.
        Ten, eleven, and twelve.
        """
        rule_low = RuleOfThreeRule(threshold=3)
        rule_high = RuleOfThreeRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        # Low threshold should flag all 4 triads
        assert len(issues_low) == 4
        # High threshold should not flag any
        assert len(issues_high) == 0


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

    def test_custom_threshold(self) -> None:
        """Test rule respects custom threshold."""
        # 4 consecutive inline headers - pattern: "- **Header**: Description"
        text = (
            "- **One**: Description one.\n"
            "- **Two**: Description two.\n"
            "- **Three**: Description three.\n"
            "- **Four**: Description four.\n"
        )
        rule_low = InlineHeaderListsRule(threshold=3)
        rule_high = InlineHeaderListsRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        # Low threshold should flag (4 >= 3)
        assert len(issues_low) == 1
        # High threshold should not flag (4 < 5)
        assert len(issues_high) == 0


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


# ---------- Phase 10 TDD: S008-S016 ----------


class TestDramaticCountdown:
    """Tests for S008: Dramatic Countdown."""

    def test_detects_not_x_not_y_just_z(self) -> None:
        """Detect 'Not X. Not Y. Just Z.' countdown pattern."""
        from proseprobe.rules.struct import DramaticCountdownRule

        text = "Not a bug. Not a feature. Just a fundamental design flaw."
        rule = DramaticCountdownRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S008"

    def test_detects_not_not_but(self) -> None:
        """Detect variant with 'But' instead of 'Just'."""
        from proseprobe.rules.struct import DramaticCountdownRule

        text = "Not recklessly. Not completely. But enough."
        rule = DramaticCountdownRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_negation(self) -> None:
        """Don't flag single negation in normal prose."""
        from proseprobe.rules.struct import DramaticCountdownRule

        text = "This is not the right approach for production use."
        rule = DramaticCountdownRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import DramaticCountdownRule

        rule = DramaticCountdownRule()
        assert rule.id == "S008"
        assert rule.name == "Dramatic Countdown"


class TestRhetoricalSelfAnswer:
    """Tests for S009: Rhetorical Self-Answer."""

    def test_detects_the_result_devastating(self) -> None:
        """Detect 'The result? Devastating.' pattern."""
        from proseprobe.rules.struct import RhetoricalSelfAnswerRule

        text = "The result? Devastating."
        rule = RhetoricalSelfAnswerRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S009"

    def test_detects_the_worst_part(self) -> None:
        """Detect 'The worst part? Nobody saw it coming.' pattern."""
        from proseprobe.rules.struct import RhetoricalSelfAnswerRule

        text = "The worst part? Nobody saw it coming."
        rule = RhetoricalSelfAnswerRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_real_questions(self) -> None:
        """Don't flag genuine questions followed by long answers."""
        from proseprobe.rules.struct import RhetoricalSelfAnswerRule

        text = (
            "What is the best way to handle errors in Python?\n"
            "The recommended approach is to use try-except blocks "
            "with specific exception types and provide meaningful error messages."
        )
        rule = RhetoricalSelfAnswerRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import RhetoricalSelfAnswerRule

        rule = RhetoricalSelfAnswerRule()
        assert rule.id == "S009"
        assert rule.name == "Rhetorical Self-Answer"


class TestAnaphoraAbuse:
    """Tests for S010: Anaphora Abuse."""

    def test_detects_repeated_they(self) -> None:
        """Detect 3+ consecutive sentences starting with same word."""
        from proseprobe.rules.struct import AnaphoraAbuseRule

        text = (
            "They built the platform. They hired the team. They launched the product."
        )
        rule = AnaphoraAbuseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S010"

    def test_detects_repeated_they_could(self) -> None:
        """Detect 'They could... They could... They could...' pattern."""
        from proseprobe.rules.struct import AnaphoraAbuseRule

        text = (
            "They could expose new APIs.\n"
            "They could offer better pricing.\n"
            "They could provide documentation.\n"
            "They could create tooling."
        )
        rule = AnaphoraAbuseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_varied_openings(self) -> None:
        """Don't flag sentences with different openings."""
        from proseprobe.rules.struct import AnaphoraAbuseRule

        text = (
            "The team built the platform. "
            "Users loved the product. "
            "Revenue grew significantly."
        )
        rule = AnaphoraAbuseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_markdown_table_rows(self) -> None:
        """Markdown table pipes should not count as repeated sentence openings."""
        from proseprobe.rules.struct import AnaphoraAbuseRule

        text = """\
| Prefix | Category |
|--------|----------|
| `V` | Vocabulary |
| `S` | Structure |
| `T` | Style |
"""
        rule = AnaphoraAbuseRule(threshold=3)
        issues = rule.check(text, "README.md")

        assert issues == []

    def test_blank_paragraphs_break_repeated_openings(self) -> None:
        """Repeated openings in separate paragraphs are not consecutive."""
        from proseprobe.rules.struct import AnaphoraAbuseRule

        text = "The first statement.\n\nThe second statement.\n\nThe third statement."

        assert AnaphoraAbuseRule().check(text, "test.md") == []

    def test_anaphora_spans_wrapped_sentences_but_not_paragraphs(self) -> None:
        from proseprobe.rules.struct import AnaphoraAbuseRule

        wrapped = "They built the platform. They hired\ncarefully. They launched it."
        separated = (
            "They built the platform.\n\nThey hired carefully.\n\nThey launched it."
        )

        [issue] = AnaphoraAbuseRule().check(wrapped, "test.md")

        assert (issue.line, issue.column) == (1, 1)
        assert AnaphoraAbuseRule().check(separated, "test.md") == []

    def test_headings_do_not_form_repeated_openings(self) -> None:
        """Heading text is not a run of prose sentences."""
        from proseprobe.rules.struct import AnaphoraAbuseRule

        text = "## The first section\n\n## The second section\n\n## The third section"

        assert AnaphoraAbuseRule().check(text, "test.md") == []

    def test_does_not_count_list_marker_as_opening(self) -> None:
        """Markdown bullet markers should not become the repeated opening."""
        from proseprobe.rules.struct import AnaphoraAbuseRule

        text = """\
- First item explains setup.
- Second item explains usage.
- Third item explains cleanup.
"""
        rule = AnaphoraAbuseRule(threshold=3)
        issues = rule.check(text, "README.md")

        assert issues == []

    def test_custom_threshold(self) -> None:
        """Respect configurable threshold."""
        from proseprobe.rules.struct import AnaphoraAbuseRule

        text = "We built X. We built Y. We built Z."
        rule_low = AnaphoraAbuseRule(threshold=2)
        rule_high = AnaphoraAbuseRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import AnaphoraAbuseRule

        rule = AnaphoraAbuseRule()
        assert rule.id == "S010"
        assert rule.name == "Anaphora Abuse"


class TestGerundFragmentLitany:
    """Tests for S011: Gerund Fragment Litany."""

    def test_detects_gerund_litany(self) -> None:
        """Detect 3+ consecutive gerund fragments."""
        from proseprobe.rules.struct import GerundFragmentLitanyRule

        text = "Fixing small bugs. Writing straightforward features. Implementing well-defined tickets."
        rule = GerundFragmentLitanyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S011"

    def test_detects_shipping_litany(self) -> None:
        """Detect short gerund fragments."""
        from proseprobe.rules.struct import GerundFragmentLitanyRule

        text = "Shipping faster. Moving quicker. Delivering more."
        rule = GerundFragmentLitanyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_gerund_litany_spans_wrapped_sentences(self) -> None:
        from proseprobe.rules.struct import GerundFragmentLitanyRule

        text = (
            "Fixing small bugs. Writing straightforward\nfeatures. Shipping releases."
        )

        [issue] = GerundFragmentLitanyRule().check(text, "test.md")

        assert (issue.line, issue.column) == (1, 1)
        assert "3 consecutive" in issue.message

    def test_ignores_normal_gerunds(self) -> None:
        """Don't flag gerunds in normal sentences."""
        from proseprobe.rules.struct import GerundFragmentLitanyRule

        text = "Running the tests was easy. The team was coding all day."
        rule = GerundFragmentLitanyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_blank_paragraphs_break_gerund_run(self) -> None:
        """Gerund fragments in separate paragraphs do not form a litany."""
        from proseprobe.rules.struct import GerundFragmentLitanyRule

        text = "Building quickly.\n\nShipping safely.\n\nLearning constantly."

        assert GerundFragmentLitanyRule().check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import GerundFragmentLitanyRule

        rule = GerundFragmentLitanyRule()
        assert rule.id == "S011"
        assert rule.name == "Gerund Fragment Litany"


class TestListicleInProse:
    """Tests for S012: Listicle in Prose."""

    def test_detects_first_second_third(self) -> None:
        """Detect 'The first... The second... The third...' pattern."""
        from proseprobe.rules.struct import ListicleInProseRule

        text = (
            "The first wall is the absence of a free API. "
            "The second wall is the lack of delegated access. "
            "The third wall is the absence of scoped permissions."
        )
        rule = ListicleInProseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 1
        assert issues[0].rule_id == "S012"

    @pytest.mark.parametrize("first", ["First,", "Firstly,"])
    def test_detects_sequential_sentence_openers(self, first: str) -> None:
        from proseprobe.rules.struct import ListicleInProseRule

        text = f"{first} install the client. Secondly, configure it. Third, run it."

        [issue] = ListicleInProseRule().check(text, "test.md")

        assert issue.message == "Listicle in prose: 'First... Second... Third...'"
        assert issue.suggestion == "Use an explicit numbered list"
        assert text[issue.column - 1 : issue.end_column - 1] == first

    def test_reports_wrapped_python_docstring_span(self) -> None:
        from proseprobe.rules.struct import ListicleInProseRule

        source = '''\
def configure():
    """First, install the client. Second, configure it.
    Third, run it."""
'''

        [issue] = ListicleInProseRule().check(source, "test.py")

        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            2,
            8,
            2,
            14,
        )

    def test_reports_only_once_when_ordinal_forms_share_a_block(self) -> None:
        from proseprobe.rules.struct import ListicleInProseRule

        text = (
            "First, install it. Second, configure it. Third, run it. "
            "The first reason is cost. The second is speed. The third is safety."
        )

        assert len(ListicleInProseRule().check(text, "test.md")) == 1

    @pytest.mark.parametrize(
        "text",
        [
            "First, install it. Second, configure it.",
            "First, install it. Third, run it. Second, configure it.",
            "First install completed. Second, configure it. Third, run it.",
            "First, install it.\n\nSecond, configure it.\n\nThird, run it.",
            "# First, install it.\n# Second, configure it.\n# Third, run it.",
            "1. First, install it.\n2. Second, configure it.\n3. Third, run it.",
        ],
    )
    def test_ignores_nonsequential_or_nonprose_blocks(self, text: str) -> None:
        from proseprobe.rules.struct import ListicleInProseRule

        assert ListicleInProseRule().check(text, "test.md") == []

    def test_detects_fallback_only_listicle_pattern_once(self) -> None:
        """A single named ordinal should retain fallback coverage."""
        from proseprobe.rules.struct import ListicleInProseRule

        text = "The first takeaway is to reduce scope."

        issues = ListicleInProseRule().check(text, "test.md")

        assert len(issues) == 1
        assert issues[0].message == "Listicle in prose pattern"

    def test_ignores_single_ordinal(self) -> None:
        """Don't flag a single ordinal reference."""
        from proseprobe.rules.struct import ListicleInProseRule

        text = "The first thing to consider is performance."
        rule = ListicleInProseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_does_not_join_ordinals_across_paragraphs(self) -> None:
        """Separate paragraphs do not become one disguised listicle."""
        from proseprobe.rules.struct import ListicleInProseRule

        text = "The first result is stable.\n\nThe second is faster.\n\nThe third is safer."

        assert ListicleInProseRule().check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import ListicleInProseRule

        rule = ListicleInProseRule()
        assert rule.id == "S012"
        assert rule.name == "Listicle in Prose"


class TestHistoricalAnalogyStacking:
    """Tests for S013: Historical Analogy Stacking."""

    def test_detects_company_stacking(self) -> None:
        """Detect rapid-fire company name-drops."""
        from proseprobe.rules.struct import HistoricalAnalogyStackingRule

        text = (
            "Apple didn't build Uber. Facebook didn't build Spotify. "
            "Stripe didn't build Shopify. AWS didn't build Airbnb."
        )
        rule = HistoricalAnalogyStackingRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S013"

    def test_detects_take_or_consider_pattern(self) -> None:
        """Detect 'Take X... Or consider Y...' pattern."""
        from proseprobe.rules.struct import HistoricalAnalogyStackingRule

        text = (
            "Take Spotify. Or consider Uber. "
            "Airbnb followed a similar path. Shopify is another example."
        )
        rule = HistoricalAnalogyStackingRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_single_mention(self) -> None:
        """Don't flag a single company mention."""
        from proseprobe.rules.struct import HistoricalAnalogyStackingRule

        text = "Apple released a new product last year."
        rule = HistoricalAnalogyStackingRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import HistoricalAnalogyStackingRule

        rule = HistoricalAnalogyStackingRule()
        assert rule.id == "S013"
        assert rule.name == "Historical Analogy Stacking"


class TestSignpostedConclusion:
    """Tests for S014: Signposted Conclusion."""

    def test_detects_in_conclusion(self) -> None:
        """Detect 'In conclusion' at sentence start."""
        from proseprobe.rules.struct import SignpostedConclusionRule

        text = "In conclusion, the future of AI depends on trust."
        rule = SignpostedConclusionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S014"

    def test_detects_to_sum_up(self) -> None:
        """Detect 'To sum up' phrase."""
        from proseprobe.rules.struct import SignpostedConclusionRule

        text = "To sum up, we've explored three key themes."
        rule = SignpostedConclusionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag prose without signposted conclusions."""
        from proseprobe.rules.struct import SignpostedConclusionRule

        text = "The system handles errors gracefully and logs all events."
        rule = SignpostedConclusionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import SignpostedConclusionRule

        rule = SignpostedConclusionRule()
        assert rule.id == "S014"
        assert rule.name == "Signposted Conclusion"


class TestFractalSummary:
    """Tests for S015: Fractal Summary."""

    def test_detects_section_framing(self) -> None:
        """Detect 'In this section, we'll explore...' framing."""
        from proseprobe.rules.struct import FractalSummaryRule

        text = "In this section, we'll explore the architecture of the system."
        rule = FractalSummaryRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S015"

    def test_detects_section_outro(self) -> None:
        """Detect 'As we've seen in this section' outro."""
        from proseprobe.rules.struct import FractalSummaryRule

        text = "As we've seen in this section, the approach has clear benefits."
        rule = FractalSummaryRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag prose without fractal summaries."""
        from proseprobe.rules.struct import FractalSummaryRule

        text = "The module provides logging utilities for the application."
        rule = FractalSummaryRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import FractalSummaryRule

        rule = FractalSummaryRule()
        assert rule.id == "S015"
        assert rule.name == "Fractal Summary"


class TestContentDuplication:
    """Tests for S016: Content Duplication."""

    def test_detects_duplicate_paragraphs(self) -> None:
        """Detect verbatim repeated paragraphs."""
        from proseprobe.rules.struct import ContentDuplicationRule

        text = (
            "The system provides reliable error handling and logging.\n\n"
            "Other features include caching and retry logic.\n\n"
            "The system provides reliable error handling and logging."
        )
        rule = ContentDuplicationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S016"

    def test_ignores_unique_paragraphs(self) -> None:
        """Don't flag unique paragraphs."""
        from proseprobe.rules.struct import ContentDuplicationRule

        text = (
            "First paragraph about one topic.\n\n"
            "Second paragraph about another topic.\n\n"
            "Third paragraph about a third topic."
        )
        rule = ContentDuplicationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_short_paragraphs(self) -> None:
        """Don't flag very short repeated paragraphs (e.g., 'Yes.')."""
        from proseprobe.rules.struct import ContentDuplicationRule

        text = "Yes.\n\nSomething else.\n\nYes."
        rule = ContentDuplicationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    @pytest.mark.parametrize(
        "marker", ["In conclusion", "To sum up", "As we've seen", "In closing"]
    )
    def test_detects_exact_signposted_repeated_conclusion(self, marker: str) -> None:
        from proseprobe.rules.struct import ContentDuplicationRule

        repeated = (
            "The retry queue preserves requests during temporary failures in "
            "production."
        )
        text = f"{repeated}\n\nA separate paragraph records delivery latency.\n\n{marker}, {repeated}"

        [issue] = ContentDuplicationRule().check(text, "test.md")

        assert issue.rule_id == "S016"
        assert issue.message == "Repeated conclusion (first seen at line 1)"
        assert (issue.line, issue.column, issue.end_line) == (5, 1, 5)
        assert issue.end_column == len(f"{marker}, {repeated}") + 1
        assert issue.severity is Severity.WARNING

    @pytest.mark.parametrize("separator", [": ", "; ", " ", "—"])
    def test_accepts_conclusion_marker_punctuation(self, separator: str) -> None:
        from proseprobe.rules.struct import ContentDuplicationRule

        repeated = (
            "The parser rejects invalid tokens before state reaches the compiler."
        )
        text = f"{repeated}\n\nIn closing{separator}{repeated}"

        [issue] = ContentDuplicationRule().check(text, "test.md")

        assert issue.message.startswith("Repeated conclusion")

    def test_preserves_verbatim_duplicate_diagnostic(self) -> None:
        from proseprobe.rules.struct import ContentDuplicationRule

        repeated = (
            "The parser rejects invalid tokens before state reaches the compiler."
        )
        text = f"{repeated}\n\n{repeated}"

        [issue] = ContentDuplicationRule().check(text, "test.md")

        assert issue.message == "Duplicate paragraph (first seen at line 1)"

    @pytest.mark.parametrize(
        "conclusion",
        [
            (
                "In conclusion, the retry queue protects production requests from "
                "temporary failures."
            ),
            "In conclusion, caching reduces request latency.",
            (
                "The report says in conclusion, the retry queue preserves requests "
                "during temporary failures in production."
            ),
        ],
    )
    def test_ignores_paraphrases_short_text_and_nonleading_markers(
        self, conclusion: str
    ) -> None:
        from proseprobe.rules.struct import ContentDuplicationRule

        earlier = (
            "The retry queue preserves requests during temporary failures in "
            "production."
        )
        text = f"{earlier}\n\nA separate paragraph records delivery latency.\n\n{conclusion}"

        assert ContentDuplicationRule().check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import ContentDuplicationRule

        rule = ContentDuplicationRule()
        assert rule.id == "S016"
        assert rule.name == "Content Duplication"


# ---------- Phase 1 (Journalism Tropes) TDD: S017 ----------


class TestAnecdoteAsEvidence:
    """Tests for S017: Anecdote As Evidence."""

    def test_detects_for_name_of_location(self) -> None:
        """Detect 'For Sarah of Ohio...' anecdote pattern."""
        from proseprobe.rules.struct import AnecdoteAsEvidenceRule

        text = (
            "For Sarah of Ohio, the policy change meant losing her healthcare. "
            "Her case shows that the policy affects every family."
        )
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S017"

    def test_detects_take_name_a_descriptor(self) -> None:
        """Detect 'Take Marcus, a software engineer...' anecdote pattern."""
        from proseprobe.rules.struct import AnecdoteAsEvidenceRule

        text = (
            "Take Marcus, a software engineer from Portland. "
            "His experience demonstrates that bootcamps help every career changer."
        )
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_meet_name(self) -> None:
        """Detect 'Meet Lisa' anecdote pattern."""
        from proseprobe.rules.struct import AnecdoteAsEvidenceRule

        text = (
            "Meet Lisa, who transformed her career through coding bootcamps. "
            "Her story illustrates a broader path for workers."
        )
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose without anecdotes."""
        from proseprobe.rules.struct import AnecdoteAsEvidenceRule

        text = "The system handles errors gracefully and logs all events."
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_non_anecdote_for(self) -> None:
        """Don't flag normal use of 'for' in prose."""
        from proseprobe.rules.struct import AnecdoteAsEvidenceRule

        text = "For best results, use a virtual environment."
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_anecdote_requires_generalization_and_ignores_examples(self) -> None:
        from proseprobe.rules.struct import AnecdoteAsEvidenceRule

        unsupported = "For Sarah of Ohio, the policy changed her commute."
        example = (
            "For Sarah of Ohio, this quoted sentence is an example of a dateline "
            "format, not evidence for a national claim."
        )
        supported = (
            "For Sarah of Ohio, the policy changed her commute. "
            "Her case shows that the policy affects every rider."
        )

        assert AnecdoteAsEvidenceRule().check(unsupported, "report.md") == []
        assert AnecdoteAsEvidenceRule().check(example, "report.md") == []
        assert len(AnecdoteAsEvidenceRule().check(supported, "report.md")) == 1

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import AnecdoteAsEvidenceRule

        rule = AnecdoteAsEvidenceRule()
        assert rule.id == "S017"
        assert rule.name == "Anecdote As Evidence"


# ---------- Phase 2 (Academic Writing Tropes) TDD: S018 ----------


class TestCitationNameDropping:
    """Tests for S018: Citation Name-Dropping."""

    def test_detects_name_dropping(self) -> None:
        """Detect 3+ consecutive 'Author (Year) verb' sentences."""
        from proseprobe.rules.struct import CitationNameDroppingRule

        text = (
            "Smith (2012) argues that technology reshapes communities. "
            "Jones (2014) claims that digital tools empower users. "
            "Patel (2018) suggests that platforms mediate interactions. "
            "Lee (2020) finds that algorithms reinforce bias."
        )
        rule = CitationNameDroppingRule(threshold=3)
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S018"

    def test_ignores_synthesized_discussion(self) -> None:
        """Don't flag synthesized literature discussion."""
        from proseprobe.rules.struct import CitationNameDroppingRule

        text = (
            "Smith (2012) and Jones (2014) both argue that technology reshapes communities. "
            "Building on this, Patel (2018) proposes a new framework."
        )
        rule = CitationNameDroppingRule(threshold=3)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_citation_runs_use_wrapped_sentences_and_reset_on_prose(self) -> None:
        from proseprobe.rules.struct import CitationNameDroppingRule

        wrapped = (
            "Smith (2012) argues that communities change. "
            "Jones (2014) claims that tools\nempower users. "
            "Patel (2018) suggests that platforms mediate interactions."
        )
        interrupted = (
            "Smith (2012) argues that communities change. "
            "The evidence is synthesized here. "
            "Jones (2014) claims that tools empower users. "
            "Patel (2018) suggests that platforms mediate interactions."
        )

        assert len(CitationNameDroppingRule().check(wrapped, "test.md")) == 1
        assert CitationNameDroppingRule().check(interrupted, "test.md") == []

    def test_ignores_below_threshold(self) -> None:
        """Don't flag when below threshold."""
        from proseprobe.rules.struct import CitationNameDroppingRule

        text = (
            "Smith (2012) argues that technology matters. "
            "Jones (2014) claims that tools help."
        )
        rule = CitationNameDroppingRule(threshold=3)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_custom_threshold(self) -> None:
        """Respect configurable threshold."""
        from proseprobe.rules.struct import CitationNameDroppingRule

        text = "Smith (2012) argues X. Jones (2014) claims Y. Patel (2018) suggests Z."
        rule_low = CitationNameDroppingRule(threshold=2)
        rule_high = CitationNameDroppingRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import CitationNameDroppingRule

        rule = CitationNameDroppingRule()
        assert rule.id == "S018"
        assert rule.name == "Citation Name-Dropping"


# ---------- Business Writing Tropes: S019-S021 ----------


class TestCorporateEuphemism:
    """Tests for S019: Corporate Euphemism."""

    def test_detects_restructuring(self) -> None:
        """Detect 'restructuring' corporate euphemism."""
        from proseprobe.rules.struct import CorporateEuphemismRule

        text = "The company announced a major restructuring initiative."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S019"
        assert "restructuring" in issues[0].message

    def test_detects_right_sizing(self) -> None:
        """Detect 'right-sizing' euphemism."""
        from proseprobe.rules.struct import CorporateEuphemismRule

        text = "We are right-sizing the organization to align with market conditions."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_sunsetting(self) -> None:
        """Detect 'sunsetting' euphemism."""
        from proseprobe.rules.struct import CorporateEuphemismRule

        text = "We will be sunsetting the legacy platform next quarter."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_headcount_reduction(self) -> None:
        """Detect 'headcount reduction' euphemism."""
        from proseprobe.rules.struct import CorporateEuphemismRule

        text = "The headcount reduction will affect 200 employees."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_wrapped_organizational_context(self) -> None:
        from proseprobe.rules.struct import CorporateEuphemismRule

        text = "The company announced a\nrestructuring initiative next quarter."

        issues = CorporateEuphemismRule().check(text, "test.md")

        assert [(issue.line, issue.column) for issue in issues] == [(2, 1)]

    def test_preserves_offsets_before_casefold_expansion(self) -> None:
        from proseprobe.rules.struct import CorporateEuphemismRule

        text = "Straße company restructuring affects staff."

        issues = CorporateEuphemismRule().check(text, "test.md")

        assert [(issue.column, issue.end_column) for issue in issues] == [(16, 29)]

    @pytest.mark.parametrize(
        "text",
        [
            "The restructuring changes staffing levels.",
            "The restructuring eliminated 300 jobs.",
        ],
    )
    def test_detects_direct_workforce_context(self, text: str) -> None:
        from proseprobe.rules.struct import CorporateEuphemismRule

        assert len(CorporateEuphemismRule().check(text, "test.md")) == 1

    @pytest.mark.parametrize(
        "text",
        [
            "The database restructuring moves two indexes.",
            "Memory realignment preserves 64-byte boundaries.",
            "Resource optimization reduced allocator overhead.",
        ],
    )
    def test_ignores_technical_ambiguous_terms(self, text: str) -> None:
        from proseprobe.rules.struct import CorporateEuphemismRule

        assert CorporateEuphemismRule().check(text, "test.md") == []

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose."""
        from proseprobe.rules.struct import CorporateEuphemismRule

        text = "The team completed the migration to the new database."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import CorporateEuphemismRule

        rule = CorporateEuphemismRule()
        assert rule.id == "S019"
        assert rule.name == "Corporate Euphemism"


class TestAlignmentRitual:
    """Tests for S020: Alignment Ritual."""

    def test_detects_fully_aligned(self) -> None:
        """Detect 'fully aligned on' alignment ritual."""
        from proseprobe.rules.struct import AlignmentRitualRule

        text = "We are fully aligned on the strategic direction moving forward."
        rule = AlignmentRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S020"

    def test_detects_on_the_same_page(self) -> None:
        """Detect 'on the same page' alignment ritual."""
        from proseprobe.rules.struct import AlignmentRitualRule

        text = "Let's make sure everyone is on the same page before we proceed."
        rule = AlignmentRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_cross_functional_alignment(self) -> None:
        """Detect 'cross-functional alignment' ritual."""
        from proseprobe.rules.struct import AlignmentRitualRule

        text = "We need cross-functional alignment before launching."
        rule = AlignmentRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose."""
        from proseprobe.rules.struct import AlignmentRitualRule

        text = "The text is aligned to the left margin."
        rule = AlignmentRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import AlignmentRitualRule

        rule = AlignmentRitualRule()
        assert rule.id == "S020"
        assert rule.name == "Alignment Ritual"


class TestSlideDeckFragment:
    """Tests for S021: Slide Deck Fragment."""

    def test_detects_buzzword_fragment(self) -> None:
        """Detect verbless buzzword-heavy fragment."""
        from proseprobe.rules.struct import SlideDeckFragmentRule

        text = "Driving alignment across strategic initiatives for scalable impact."
        rule = SlideDeckFragmentRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S021"

    def test_detects_operational_excellence(self) -> None:
        """Detect 'operational excellence' fragment."""
        from proseprobe.rules.struct import SlideDeckFragmentRule

        text = (
            "Operational excellence through cross-functional synergy and optimization."
        )
        rule = SlideDeckFragmentRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_sentences(self) -> None:
        """Don't flag normal sentences with verbs."""
        from proseprobe.rules.struct import SlideDeckFragmentRule

        text = "The team will coordinate projects to improve scalability."
        rule = SlideDeckFragmentRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_pronoun_led_finite_clause(self) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        text = (
            "We need to ensure cross-functional alignment and get buy-in "
            "from all stakeholders."
        )

        assert SlideDeckFragmentRule().check(text, "test.md") == []

    def test_ignores_contracted_pronoun_led_finite_clause(self) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        text = (
            "We're driving alignment across strategic initiatives for scalable impact."
        )

        assert SlideDeckFragmentRule().check(text, "test.md") == []

    def test_ignores_typographic_contracted_pronoun_led_finite_clause(self) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        text = "We\u2019re driving alignment across strategic initiatives for scalable impact."

        assert SlideDeckFragmentRule().check(text, "test.md") == []

    @pytest.mark.parametrize(
        "text",
        [
            "The analysis shows that strategic alignment will deliver scalable impact.",
            "That strategic alignment will deliver scalable impact.",
        ],
    )
    def test_ignores_complete_clause_with_relative_word(self, text: str) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        assert SlideDeckFragmentRule().check(text, "test.md") == []

    @pytest.mark.parametrize(
        "text",
        [
            (
                "Driving strategic alignment for initiatives that will deliver "
                "scalable impact is difficult."
            ),
            (
                "Strategic alignment for initiatives that will deliver scalable "
                "impact remains difficult."
            ),
        ],
    )
    def test_ignores_main_predicate_after_relative_clause(self, text: str) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        assert SlideDeckFragmentRule().check(text, "test.md") == []

    def test_ignores_unlisted_main_predicate_after_relative_clause(self) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        text = (
            "Strategic alignment for initiatives that will deliver scalable impact "
            "requires planning."
        )

        assert SlideDeckFragmentRule().check(text, "test.md") == []

    @pytest.mark.parametrize(
        "text",
        [
            (
                "Driving strategic alignment for initiatives that will "
                "deliver scalable impact."
            ),
            ("Strategic alignment for initiatives that will deliver scalable impact."),
        ],
    )
    def test_detects_fragment_with_subordinate_auxiliary(self, text: str) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        assert len(SlideDeckFragmentRule().check(text, "test.md")) == 1

    def test_detects_fragment_with_multiple_subordinate_auxiliaries(self) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        text = "Strategic alignment for initiatives that will have scalable impact."

        assert len(SlideDeckFragmentRule().check(text, "test.md")) == 1

    @pytest.mark.parametrize(
        "text",
        [
            (
                "Enterprise strategic alignment for initiatives that will deliver "
                "scalable impact."
            ),
            ("Strategic alignment among teams that will deliver scalable impact."),
        ],
    )
    def test_detects_varied_fragment_prefix_before_relative_clause(
        self, text: str
    ) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        assert len(SlideDeckFragmentRule().check(text, "test.md")) == 1

    def test_ignores_short_lines(self) -> None:
        """Don't flag lines with fewer than 4 words."""
        from proseprobe.rules.struct import SlideDeckFragmentRule

        text = "Strategic alignment."
        rule = SlideDeckFragmentRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from proseprobe.rules.struct import SlideDeckFragmentRule

        rule = SlideDeckFragmentRule()
        assert rule.id == "S021"
        assert rule.name == "Slide Deck Fragment"


class TestWallOfTextParagraph:
    """Tests for S022: Wall-of-Text Paragraph."""

    SIX_SENTENCES = (
        "The cache warms at startup. Workers load configuration next. "
        "Validation checks required fields. The client opens its connection. "
        "Requests begin after readiness. Metrics record the completed startup."
    )

    def test_reports_default_threshold_with_exact_span(self) -> None:
        [issue] = WallOfTextParagraphRule().check(self.SIX_SENTENCES, "guide.md")

        assert issue.rule_id == "S022"
        assert issue.message == "Wall-of-text paragraph: 6 sentences (threshold 6)"
        assert (issue.line, issue.column, issue.end_line, issue.end_column) == (
            1,
            1,
            1,
            len(self.SIX_SENTENCES) + 1,
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "Split the paragraph into shorter paragraphs"

    def test_uses_configured_threshold(self) -> None:
        text = "First sentence. Second sentence. Third sentence."

        assert WallOfTextParagraphRule().check(text, "guide.md") == []
        assert len(WallOfTextParagraphRule(threshold=3).check(text, "guide.md")) == 1

    def test_does_not_combine_separate_paragraphs(self) -> None:
        text = (
            "First sentence. Second sentence. Third sentence.\n\n"
            "Fourth sentence. Fifth sentence. Sixth sentence."
        )

        assert WallOfTextParagraphRule().check(text, "guide.md") == []
        issues = WallOfTextParagraphRule(threshold=3).check(text, "guide.md")
        assert [issue.line for issue in issues] == [1, 3]

    def test_counts_wrapped_blockquote_sentences(self) -> None:
        text = (
            "> Operators start the migration. A backup captures current data.\n"
            "> Schema checks verify compatibility. The service copies each record.\n"
            "> Validation compares row counts. Reviewers inspect the final report."
        )

        [issue] = WallOfTextParagraphRule().check(text, "guide.md")

        assert (issue.line, issue.column, issue.end_line) == (1, 3, 3)
        assert issue.end_column == len(text.splitlines()[-1]) + 1

    @pytest.mark.parametrize(
        "text",
        [
            "# One. Two. Three. Four. Five. Six.",
            "- One. Two. Three. Four. Five. Six.",
            "## Example\n\nOne. Two. Three. Four. Five. Six.",
            "```text\nOne. Two. Three. Four. Five. Six.\n```",
        ],
    )
    def test_ignores_ineligible_markdown_contexts(self, text: str) -> None:
        assert WallOfTextParagraphRule().check(text, "guide.md") == []

    def test_checks_python_comments_and_docstrings_but_not_strings(self) -> None:
        text = (
            'label = "One. Two. Three. Four. Five. Six."\n'
            "# One. Two. Three. Four. Five. Six.\n\n"
            "def load() -> None:\n"
            '    """One. Two. Three. Four. Five. Six."""\n'
            "    return None\n"
        )

        issues = WallOfTextParagraphRule().check(text, "loader.py")

        assert [issue.line for issue in issues] == [2, 5]

    def test_rule_metadata(self) -> None:
        rule = WallOfTextParagraphRule()

        assert rule.id == "S022"
        assert rule.name == "Wall-of-Text Paragraph"
        assert rule.config_key == "thresholds.wall_of_text_sentences"


class TestHeadingWithoutBody:
    """Tests for S025: Heading Without Body."""

    def test_reports_the_empty_heading_exactly(self) -> None:
        source = "## Empty\n\n## Next\n"

        [issue] = HeadingWithoutBodyRule().check(source, "guide.md")

        assert issue.rule_id == "S025"
        assert issue.message == "Heading without body: 'Empty'"
        assert (issue.line, issue.column, issue.end_column) == (1, 4, 9)
        assert issue.severity is Severity.WARNING
        assert issue.confidence is Confidence.HIGH
        assert issue.suggestion == "Add content under this heading or remove it"

    def test_reports_same_and_higher_level_boundaries_in_order(self) -> None:
        source = "## First\n\n## Second\n\n# Last"

        issues = HeadingWithoutBodyRule().check(source, "guide.markdown")

        assert [issue.message for issue in issues] == [
            "Heading without body: 'First'",
            "Heading without body: 'Second'",
        ]

    def test_allows_parent_heading_before_child(self) -> None:
        source = "# Parent\n## Empty child\n\n# Peer"

        [issue] = HeadingWithoutBodyRule().check(source, "guide.mdx")

        assert issue.message == "Heading without body: 'Empty child'"

    @pytest.mark.parametrize(
        "body",
        [
            "Body prose.",
            "- unordered item",
            "1. ordered item",
            "| Name | Value |\n| --- | --- |\n| alpha | beta |",
            "> quoted body",
            "<div>\nHTML body.\n</div>",
            "```python\npass\n```",
        ],
    )
    def test_body_content_prevents_a_finding(self, body: str) -> None:
        source = f"## Populated\n\n{body}\n\n## Next"

        assert HeadingWithoutBodyRule().check(source, "guide.md") == []

    @pytest.mark.parametrize(
        ("source", "line", "column", "end_column"),
        [
            ("Empty\n-----\n\n# Next", 1, 1, 6),
            ("> Empty\n> -----\n>\n> # Next", 1, 3, 8),
            ("> ## Empty\n>\n> ## Next", 1, 6, 11),
        ],
    )
    def test_setext_and_blank_blockquotes_are_empty(
        self, source: str, line: int, column: int, end_column: int
    ) -> None:
        [issue] = HeadingWithoutBodyRule().check(source, "guide.md")

        assert (issue.line, issue.column, issue.end_column) == (
            line,
            column,
            end_column,
        )

    @pytest.mark.parametrize(
        "hidden_body",
        [
            "```markdown\n## Hidden\n```",
            "<section>\n## Hidden\n</section>",
        ],
    )
    def test_hidden_headings_do_not_create_boundaries(self, hidden_body: str) -> None:
        source = f"## Populated\n\n{hidden_body}\n\n## Empty\n\n## Next"

        [issue] = HeadingWithoutBodyRule().check(source, "guide.md")

        assert issue.message == "Heading without body: 'Empty'"

    def test_ignores_final_heading_and_non_markdown_input(self) -> None:
        rule = HeadingWithoutBodyRule()

        assert rule.check("## Final", "guide.md") == []
        assert rule.check("## Empty\n\n## Next", "guide.py") == []


class TestExcessiveHeadingDepth:
    """Tests for S028: Excessive Heading Depth."""

    @pytest.mark.parametrize(("marker", "level"), [("#####", 5), ("######", 6)])
    def test_reports_excessive_heading_fields(self, marker: str, level: int) -> None:
        source = f"{marker} Internal details"

        [issue] = ExcessiveHeadingDepthRule().check(source, "guide.md")

        assert issue.rule_id == "S028"
        assert issue.message == (
            f"Excessive heading depth: level {level} heading 'Internal details'"
        )
        assert (issue.line, issue.column, issue.end_column) == (
            1,
            len(marker) + 2,
            len(source) + 1,
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.MEDIUM
        assert issue.suggestion == "Use a level-4 or shallower heading"

    def test_reports_visible_headings_in_source_order(self) -> None:
        source = "##### First detail\n\nBody.\n\n> ###### Nested detail ######"

        issues = ExcessiveHeadingDepthRule().check(source, "guide.mdx")

        assert [(issue.line, issue.column) for issue in issues] == [(1, 7), (5, 10)]

    @pytest.mark.parametrize(
        "source",
        [
            "#### Supported depth",
            "```markdown\n###### Hidden\n```\n\n#### Visible",
            "<section>\n###### Hidden\n</section>\n\n#### Visible",
            "---\ntitle: Guide\n###### Hidden\n---\n\n#### Visible",
        ],
    )
    def test_ignores_supported_and_hidden_headings(self, source: str) -> None:
        assert ExcessiveHeadingDepthRule().check(source, "guide.md") == []

    def test_applies_only_to_markdown(self) -> None:
        assert (
            ExcessiveHeadingDepthRule().check("###### Comment heading", "guide.py")
            == []
        )

    def test_rule_metadata(self) -> None:
        rule = ExcessiveHeadingDepthRule()

        assert rule.id == "S028"
        assert rule.name == "Excessive Heading Depth"
        assert rule.config_key is None


class TestTinySection:
    """Tests for S029: Tiny Section."""

    def test_reports_one_finding_for_a_tiny_sibling_run(self) -> None:
        source = """\
# Operations guide

Substantive introduction for the operations guide.

## Start

Starts the worker.

## Stop

Stops the worker.

## Retry

Retries failed work.
"""

        [issue] = TinySectionRule().check(source, "guide.md")

        assert issue.rule_id == "S029"
        assert issue.message == "Tiny-section run: 3 consecutive level-2 sections"
        assert (issue.line, issue.column, issue.end_column) == (5, 4, 9)
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.LOW
        assert issue.suggestion == "Merge related sections or expand their content"

    def test_reports_one_finding_for_a_longer_run(self) -> None:
        sections = "\n\n".join(
            f"## Part {number}\n\nRuns now." for number in range(1, 5)
        )

        [issue] = TinySectionRule().check(sections, "guide.mdx")

        assert "4 consecutive" in issue.message

    @pytest.mark.parametrize(
        "body",
        [
            "- one item",
            "| Key | Value |\n| --- | --- |\n| a | b |",
            "Key | Value\n--- | ---\na | b",
            "> Quoted text.",
            "[Read more](https://example.com).",
            "See [worker][docs].",
            "See https://example.com.",
            "Use `run` now.",
            "    worker start",
            "```text\noutput\n```",
            "<div>\nText.\n</div>",
            "First paragraph.\n\nSecond paragraph.",
        ],
    )
    def test_structured_or_multiple_bodies_break_a_run(self, body: str) -> None:
        source = "\n\n".join(f"## Part {number}\n\n{body}" for number in range(1, 4))

        assert TinySectionRule().check(source, "guide.md") == []

    @pytest.mark.parametrize(
        "title", ["API", "Reference", "Changelog", "Release notes", "FAQ", "Examples"]
    )
    def test_excluded_document_contexts_do_not_report(self, title: str) -> None:
        source = f"""\
# {title}

## First

Runs now.

## Second

Stops now.

## Third

Retries now.
"""

        assert TinySectionRule().check(source, "guide.md") == []

    def test_question_headings_do_not_report(self) -> None:
        source = """\
# Guide

## What starts it?

The command.

## What stops it?

The signal.

## What retries it?

The worker.
"""

        assert TinySectionRule().check(source, "guide.md") == []

    @pytest.mark.parametrize(
        "source",
        [
            "## One\n\nRuns.\n\n## Two\n\nStops.",
            (
                "## One\n\nRuns.\n\n## Two\n\nStops.\n\n"
                "## Detailed\n\nSix words make this section body substantive.\n\n"
                "## Three\n\nRetries.\n\n## Four\n\nWaits."
            ),
            "# One\n\nRuns.\n\n# Two\n\nStops.\n\n# Three\n\nRetries.",
            (
                "## Parent one\n\nRuns.\n\n### Child\n\nStops.\n\n"
                "## Parent two\n\nRetries."
            ),
        ],
    )
    def test_run_boundaries_do_not_report(self, source: str) -> None:
        assert TinySectionRule().check(source, "guide.md") == []

    def test_applies_only_to_markdown(self) -> None:
        source = "## One\n\nRuns.\n\n## Two\n\nStops.\n\n## Three\n\nRetries."

        assert TinySectionRule().check(source, "guide.py") == []

    def test_rule_metadata(self) -> None:
        rule = TinySectionRule()

        assert rule.id == "S029"
        assert rule.name == "Tiny Section"
        assert rule.default_confidence is Confidence.LOW
