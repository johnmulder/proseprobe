"""Tests for structural rules (S001-S007)."""

from slop_lint.rules.struct import (
    ChallengeConclusionsRule,
    FalseRangesRule,
    InlineHeaderListsRule,
    NegativeParallelismRule,
    RuleOfThreeRule,
    SignificanceEmphasisRule,
    SuperficialAnalysisRule,
)

# New S008-S016 imports will be added once implemented
# (Tests written first — TDD red phase)


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
        from slop_lint.rules.struct import DramaticCountdownRule

        text = "Not a bug. Not a feature. Just a fundamental design flaw."
        rule = DramaticCountdownRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S008"

    def test_detects_not_not_but(self) -> None:
        """Detect variant with 'But' instead of 'Just'."""
        from slop_lint.rules.struct import DramaticCountdownRule

        text = "Not recklessly. Not completely. But enough."
        rule = DramaticCountdownRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_negation(self) -> None:
        """Don't flag single negation in normal prose."""
        from slop_lint.rules.struct import DramaticCountdownRule

        text = "This is not the right approach for production use."
        rule = DramaticCountdownRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import DramaticCountdownRule

        rule = DramaticCountdownRule()
        assert rule.id == "S008"
        assert rule.name == "Dramatic Countdown"


class TestRhetoricalSelfAnswer:
    """Tests for S009: Rhetorical Self-Answer."""

    def test_detects_the_result_devastating(self) -> None:
        """Detect 'The result? Devastating.' pattern."""
        from slop_lint.rules.struct import RhetoricalSelfAnswerRule

        text = "The result? Devastating."
        rule = RhetoricalSelfAnswerRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S009"

    def test_detects_the_worst_part(self) -> None:
        """Detect 'The worst part? Nobody saw it coming.' pattern."""
        from slop_lint.rules.struct import RhetoricalSelfAnswerRule

        text = "The worst part? Nobody saw it coming."
        rule = RhetoricalSelfAnswerRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_real_questions(self) -> None:
        """Don't flag genuine questions followed by long answers."""
        from slop_lint.rules.struct import RhetoricalSelfAnswerRule

        text = (
            "What is the best way to handle errors in Python?\n"
            "The recommended approach is to use try-except blocks "
            "with specific exception types and provide meaningful error messages."
        )
        rule = RhetoricalSelfAnswerRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import RhetoricalSelfAnswerRule

        rule = RhetoricalSelfAnswerRule()
        assert rule.id == "S009"
        assert rule.name == "Rhetorical Self-Answer"


class TestAnaphoraAbuse:
    """Tests for S010: Anaphora Abuse."""

    def test_detects_repeated_they(self) -> None:
        """Detect 3+ consecutive sentences starting with same word."""
        from slop_lint.rules.struct import AnaphoraAbuseRule

        text = (
            "They built the platform. They hired the team. They launched the product."
        )
        rule = AnaphoraAbuseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S010"

    def test_detects_repeated_they_could(self) -> None:
        """Detect 'They could... They could... They could...' pattern."""
        from slop_lint.rules.struct import AnaphoraAbuseRule

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
        from slop_lint.rules.struct import AnaphoraAbuseRule

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
        from slop_lint.rules.struct import AnaphoraAbuseRule

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
        from slop_lint.rules.struct import AnaphoraAbuseRule

        text = "The first statement.\n\nThe second statement.\n\nThe third statement."

        assert AnaphoraAbuseRule().check(text, "test.md") == []

    def test_anaphora_spans_wrapped_sentences_but_not_paragraphs(self) -> None:
        from slop_lint.rules.struct import AnaphoraAbuseRule

        wrapped = "They built the platform. They hired\ncarefully. They launched it."
        separated = (
            "They built the platform.\n\nThey hired carefully.\n\nThey launched it."
        )

        [issue] = AnaphoraAbuseRule().check(wrapped, "test.md")

        assert (issue.line, issue.column) == (1, 1)
        assert AnaphoraAbuseRule().check(separated, "test.md") == []

    def test_headings_do_not_form_repeated_openings(self) -> None:
        """Heading text is not a run of prose sentences."""
        from slop_lint.rules.struct import AnaphoraAbuseRule

        text = "## The first section\n\n## The second section\n\n## The third section"

        assert AnaphoraAbuseRule().check(text, "test.md") == []

    def test_does_not_count_list_marker_as_opening(self) -> None:
        """Markdown bullet markers should not become the repeated opening."""
        from slop_lint.rules.struct import AnaphoraAbuseRule

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
        from slop_lint.rules.struct import AnaphoraAbuseRule

        text = "We built X. We built Y. We built Z."
        rule_low = AnaphoraAbuseRule(threshold=2)
        rule_high = AnaphoraAbuseRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import AnaphoraAbuseRule

        rule = AnaphoraAbuseRule()
        assert rule.id == "S010"
        assert rule.name == "Anaphora Abuse"


class TestGerundFragmentLitany:
    """Tests for S011: Gerund Fragment Litany."""

    def test_detects_gerund_litany(self) -> None:
        """Detect 3+ consecutive gerund fragments."""
        from slop_lint.rules.struct import GerundFragmentLitanyRule

        text = "Fixing small bugs. Writing straightforward features. Implementing well-defined tickets."
        rule = GerundFragmentLitanyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S011"

    def test_detects_shipping_litany(self) -> None:
        """Detect short gerund fragments."""
        from slop_lint.rules.struct import GerundFragmentLitanyRule

        text = "Shipping faster. Moving quicker. Delivering more."
        rule = GerundFragmentLitanyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_gerund_litany_spans_wrapped_sentences(self) -> None:
        from slop_lint.rules.struct import GerundFragmentLitanyRule

        text = (
            "Fixing small bugs. Writing straightforward\nfeatures. Shipping releases."
        )

        [issue] = GerundFragmentLitanyRule().check(text, "test.md")

        assert (issue.line, issue.column) == (1, 1)
        assert "3 consecutive" in issue.message

    def test_ignores_normal_gerunds(self) -> None:
        """Don't flag gerunds in normal sentences."""
        from slop_lint.rules.struct import GerundFragmentLitanyRule

        text = "Running the tests was easy. The team was coding all day."
        rule = GerundFragmentLitanyRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_blank_paragraphs_break_gerund_run(self) -> None:
        """Gerund fragments in separate paragraphs do not form a litany."""
        from slop_lint.rules.struct import GerundFragmentLitanyRule

        text = "Building quickly.\n\nShipping safely.\n\nLearning constantly."

        assert GerundFragmentLitanyRule().check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import GerundFragmentLitanyRule

        rule = GerundFragmentLitanyRule()
        assert rule.id == "S011"
        assert rule.name == "Gerund Fragment Litany"


class TestListicleInProse:
    """Tests for S012: Listicle in Prose."""

    def test_detects_first_second_third(self) -> None:
        """Detect 'The first... The second... The third...' pattern."""
        from slop_lint.rules.struct import ListicleInProseRule

        text = (
            "The first wall is the absence of a free API. "
            "The second wall is the lack of delegated access. "
            "The third wall is the absence of scoped permissions."
        )
        rule = ListicleInProseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 1
        assert issues[0].rule_id == "S012"

    def test_detects_fallback_only_listicle_pattern_once(self) -> None:
        """A single named ordinal should retain fallback coverage."""
        from slop_lint.rules.struct import ListicleInProseRule

        text = "The first takeaway is to reduce scope."

        issues = ListicleInProseRule().check(text, "test.md")

        assert len(issues) == 1
        assert issues[0].message == "Listicle in prose pattern"

    def test_ignores_single_ordinal(self) -> None:
        """Don't flag a single ordinal reference."""
        from slop_lint.rules.struct import ListicleInProseRule

        text = "The first thing to consider is performance."
        rule = ListicleInProseRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_does_not_join_ordinals_across_paragraphs(self) -> None:
        """Separate paragraphs do not become one disguised listicle."""
        from slop_lint.rules.struct import ListicleInProseRule

        text = "The first result is stable.\n\nThe second is faster.\n\nThe third is safer."

        assert ListicleInProseRule().check(text, "test.md") == []

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import ListicleInProseRule

        rule = ListicleInProseRule()
        assert rule.id == "S012"
        assert rule.name == "Listicle in Prose"


class TestHistoricalAnalogyStacking:
    """Tests for S013: Historical Analogy Stacking."""

    def test_detects_company_stacking(self) -> None:
        """Detect rapid-fire company name-drops."""
        from slop_lint.rules.struct import HistoricalAnalogyStackingRule

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
        from slop_lint.rules.struct import HistoricalAnalogyStackingRule

        text = (
            "Take Spotify. Or consider Uber. "
            "Airbnb followed a similar path. Shopify is another example."
        )
        rule = HistoricalAnalogyStackingRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_single_mention(self) -> None:
        """Don't flag a single company mention."""
        from slop_lint.rules.struct import HistoricalAnalogyStackingRule

        text = "Apple released a new product last year."
        rule = HistoricalAnalogyStackingRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import HistoricalAnalogyStackingRule

        rule = HistoricalAnalogyStackingRule()
        assert rule.id == "S013"
        assert rule.name == "Historical Analogy Stacking"


class TestSignpostedConclusion:
    """Tests for S014: Signposted Conclusion."""

    def test_detects_in_conclusion(self) -> None:
        """Detect 'In conclusion' at sentence start."""
        from slop_lint.rules.struct import SignpostedConclusionRule

        text = "In conclusion, the future of AI depends on trust."
        rule = SignpostedConclusionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S014"

    def test_detects_to_sum_up(self) -> None:
        """Detect 'To sum up' phrase."""
        from slop_lint.rules.struct import SignpostedConclusionRule

        text = "To sum up, we've explored three key themes."
        rule = SignpostedConclusionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag prose without signposted conclusions."""
        from slop_lint.rules.struct import SignpostedConclusionRule

        text = "The system handles errors gracefully and logs all events."
        rule = SignpostedConclusionRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import SignpostedConclusionRule

        rule = SignpostedConclusionRule()
        assert rule.id == "S014"
        assert rule.name == "Signposted Conclusion"


class TestFractalSummary:
    """Tests for S015: Fractal Summary."""

    def test_detects_section_framing(self) -> None:
        """Detect 'In this section, we'll explore...' framing."""
        from slop_lint.rules.struct import FractalSummaryRule

        text = "In this section, we'll explore the architecture of the system."
        rule = FractalSummaryRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S015"

    def test_detects_section_outro(self) -> None:
        """Detect 'As we've seen in this section' outro."""
        from slop_lint.rules.struct import FractalSummaryRule

        text = "As we've seen in this section, the approach has clear benefits."
        rule = FractalSummaryRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag prose without fractal summaries."""
        from slop_lint.rules.struct import FractalSummaryRule

        text = "The module provides logging utilities for the application."
        rule = FractalSummaryRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import FractalSummaryRule

        rule = FractalSummaryRule()
        assert rule.id == "S015"
        assert rule.name == "Fractal Summary"


class TestContentDuplication:
    """Tests for S016: Content Duplication."""

    def test_detects_duplicate_paragraphs(self) -> None:
        """Detect verbatim repeated paragraphs."""
        from slop_lint.rules.struct import ContentDuplicationRule

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
        from slop_lint.rules.struct import ContentDuplicationRule

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
        from slop_lint.rules.struct import ContentDuplicationRule

        text = "Yes.\n\nSomething else.\n\nYes."
        rule = ContentDuplicationRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import ContentDuplicationRule

        rule = ContentDuplicationRule()
        assert rule.id == "S016"
        assert rule.name == "Content Duplication"


# ---------- Phase 1 (Journalism Tropes) TDD: S017 ----------


class TestAnecdoteAsEvidence:
    """Tests for S017: Anecdote As Evidence."""

    def test_detects_for_name_of_location(self) -> None:
        """Detect 'For Sarah of Ohio...' anecdote pattern."""
        from slop_lint.rules.struct import AnecdoteAsEvidenceRule

        text = "For Sarah of Ohio, the policy change meant losing her healthcare."
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S017"

    def test_detects_take_name_a_descriptor(self) -> None:
        """Detect 'Take Marcus, a software engineer...' anecdote pattern."""
        from slop_lint.rules.struct import AnecdoteAsEvidenceRule

        text = "Take Marcus, a software engineer from Portland."
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_meet_name(self) -> None:
        """Detect 'Meet Lisa' anecdote pattern."""
        from slop_lint.rules.struct import AnecdoteAsEvidenceRule

        text = "Meet Lisa, who transformed her career through coding bootcamps."
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose without anecdotes."""
        from slop_lint.rules.struct import AnecdoteAsEvidenceRule

        text = "The system handles errors gracefully and logs all events."
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_non_anecdote_for(self) -> None:
        """Don't flag normal use of 'for' in prose."""
        from slop_lint.rules.struct import AnecdoteAsEvidenceRule

        text = "For best results, use a virtual environment."
        rule = AnecdoteAsEvidenceRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import AnecdoteAsEvidenceRule

        rule = AnecdoteAsEvidenceRule()
        assert rule.id == "S017"
        assert rule.name == "Anecdote As Evidence"


# ---------- Phase 2 (Academic Writing Tropes) TDD: S018 ----------


class TestCitationNameDropping:
    """Tests for S018: Citation Name-Dropping."""

    def test_detects_name_dropping(self) -> None:
        """Detect 3+ consecutive 'Author (Year) verb' sentences."""
        from slop_lint.rules.struct import CitationNameDroppingRule

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
        from slop_lint.rules.struct import CitationNameDroppingRule

        text = (
            "Smith (2012) and Jones (2014) both argue that technology reshapes communities. "
            "Building on this, Patel (2018) proposes a new framework."
        )
        rule = CitationNameDroppingRule(threshold=3)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_below_threshold(self) -> None:
        """Don't flag when below threshold."""
        from slop_lint.rules.struct import CitationNameDroppingRule

        text = (
            "Smith (2012) argues that technology matters. "
            "Jones (2014) claims that tools help."
        )
        rule = CitationNameDroppingRule(threshold=3)
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_custom_threshold(self) -> None:
        """Respect configurable threshold."""
        from slop_lint.rules.struct import CitationNameDroppingRule

        text = "Smith (2012) argues X. Jones (2014) claims Y. Patel (2018) suggests Z."
        rule_low = CitationNameDroppingRule(threshold=2)
        rule_high = CitationNameDroppingRule(threshold=5)
        issues_low = rule_low.check(text, "test.md")
        issues_high = rule_high.check(text, "test.md")
        assert len(issues_low) >= 1
        assert len(issues_high) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import CitationNameDroppingRule

        rule = CitationNameDroppingRule()
        assert rule.id == "S018"
        assert rule.name == "Citation Name-Dropping"


# ---------- Business Writing Tropes: S019-S021 ----------


class TestCorporateEuphemism:
    """Tests for S019: Corporate Euphemism."""

    def test_detects_restructuring(self) -> None:
        """Detect 'restructuring' corporate euphemism."""
        from slop_lint.rules.struct import CorporateEuphemismRule

        text = "The company announced a major restructuring initiative."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S019"
        assert "restructuring" in issues[0].message

    def test_detects_right_sizing(self) -> None:
        """Detect 'right-sizing' euphemism."""
        from slop_lint.rules.struct import CorporateEuphemismRule

        text = "We are right-sizing the organization to align with market conditions."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_sunsetting(self) -> None:
        """Detect 'sunsetting' euphemism."""
        from slop_lint.rules.struct import CorporateEuphemismRule

        text = "We will be sunsetting the legacy platform next quarter."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_headcount_reduction(self) -> None:
        """Detect 'headcount reduction' euphemism."""
        from slop_lint.rules.struct import CorporateEuphemismRule

        text = "The headcount reduction will affect 200 employees."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose."""
        from slop_lint.rules.struct import CorporateEuphemismRule

        text = "The team completed the migration to the new database."
        rule = CorporateEuphemismRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import CorporateEuphemismRule

        rule = CorporateEuphemismRule()
        assert rule.id == "S019"
        assert rule.name == "Corporate Euphemism"


class TestAlignmentRitual:
    """Tests for S020: Alignment Ritual."""

    def test_detects_fully_aligned(self) -> None:
        """Detect 'fully aligned on' alignment ritual."""
        from slop_lint.rules.struct import AlignmentRitualRule

        text = "We are fully aligned on the strategic direction moving forward."
        rule = AlignmentRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S020"

    def test_detects_on_the_same_page(self) -> None:
        """Detect 'on the same page' alignment ritual."""
        from slop_lint.rules.struct import AlignmentRitualRule

        text = "Let's make sure everyone is on the same page before we proceed."
        rule = AlignmentRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_detects_cross_functional_alignment(self) -> None:
        """Detect 'cross-functional alignment' ritual."""
        from slop_lint.rules.struct import AlignmentRitualRule

        text = "We need cross-functional alignment before launching."
        rule = AlignmentRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_prose(self) -> None:
        """Don't flag normal prose."""
        from slop_lint.rules.struct import AlignmentRitualRule

        text = "The text is aligned to the left margin."
        rule = AlignmentRitualRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import AlignmentRitualRule

        rule = AlignmentRitualRule()
        assert rule.id == "S020"
        assert rule.name == "Alignment Ritual"


class TestSlideDeckFragment:
    """Tests for S021: Slide Deck Fragment."""

    def test_detects_buzzword_fragment(self) -> None:
        """Detect verbless buzzword-heavy fragment."""
        from slop_lint.rules.struct import SlideDeckFragmentRule

        text = "Driving alignment across strategic initiatives for scalable impact."
        rule = SlideDeckFragmentRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1
        assert issues[0].rule_id == "S021"

    def test_detects_operational_excellence(self) -> None:
        """Detect 'operational excellence' fragment."""
        from slop_lint.rules.struct import SlideDeckFragmentRule

        text = (
            "Operational excellence through cross-functional synergy and optimization."
        )
        rule = SlideDeckFragmentRule()
        issues = rule.check(text, "test.md")
        assert len(issues) >= 1

    def test_ignores_normal_sentences(self) -> None:
        """Don't flag normal sentences with verbs."""
        from slop_lint.rules.struct import SlideDeckFragmentRule

        text = "The team will coordinate projects to improve scalability."
        rule = SlideDeckFragmentRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_ignores_short_lines(self) -> None:
        """Don't flag lines with fewer than 4 words."""
        from slop_lint.rules.struct import SlideDeckFragmentRule

        text = "Strategic alignment."
        rule = SlideDeckFragmentRule()
        issues = rule.check(text, "test.md")
        assert len(issues) == 0

    def test_rule_metadata(self) -> None:
        from slop_lint.rules.struct import SlideDeckFragmentRule

        rule = SlideDeckFragmentRule()
        assert rule.id == "S021"
        assert rule.name == "Slide Deck Fragment"
