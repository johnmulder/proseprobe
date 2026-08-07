"""Property-based tests using Hypothesis.

These tests verify invariants that should hold for all inputs:
- Rules never crash on arbitrary input
- Issue positions are always within bounds
- Rules are deterministic
"""

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from slop_lint.rules.base import Issue, Rule, Severity
from slop_lint.rules.code import (
    AIPlaceholdersRule,
    CollaborativeCommentsRule,
    DocstringVocabularyRule,
    VerboseCommentsRule,
)
from slop_lint.rules.grammar import (
    CopulaAvoidanceRule,
    ExcessiveHedgingRule,
    ParticipleChainsRule,
)
from slop_lint.rules.markup import (
    BrokenReferencesRule,
    ChatGPTMarkersRule,
    UnresolvedMarkdownReferencesRule,
    UTMParametersRule,
    WrongMarkupRule,
)
from slop_lint.rules.struct import (
    ChallengeConclusionsRule,
    FalseRangesRule,
    InlineHeaderListsRule,
    NegativeParallelismRule,
    RuleOfThreeRule,
    SignificanceEmphasisRule,
    SuperficialAnalysisRule,
)
from slop_lint.rules.style import (
    BoldOveruseRule,
    ElegantVariationRule,
    EmDashOveruseRule,
    EmojiInProseRule,
    QuoteInconsistencyRule,
    TitleCaseHeadingsRule,
)
from slop_lint.rules.vocab import (
    AIVocabularyRule,
    CollaborativePhrasesRule,
    KnowledgeCutoffRule,
    PromotionalLanguageRule,
    WeaselWordsRule,
)

# Text strategies
text_content = st.text(
    min_size=0,
    max_size=2000,
    alphabet=st.characters(
        blacklist_categories=("Cs",),  # type: ignore[arg-type]  # Exclude surrogates
        blacklist_characters="\x00",  # Exclude null bytes
    ),
)

filenames = st.sampled_from(
    ["test.md", "readme.md", "doc.py", "main.py", "CHANGELOG.md"]
)


# Collect all rules for parametrized tests
ALL_RULES = [
    AIVocabularyRule(),
    CollaborativePhrasesRule(),
    KnowledgeCutoffRule(),
    PromotionalLanguageRule(),
    WeaselWordsRule(),
    RuleOfThreeRule(),
    NegativeParallelismRule(),
    ChallengeConclusionsRule(),
    InlineHeaderListsRule(),
    SignificanceEmphasisRule(),
    SuperficialAnalysisRule(),
    FalseRangesRule(),
    TitleCaseHeadingsRule(),
    BoldOveruseRule(),
    EmDashOveruseRule(),
    QuoteInconsistencyRule(),
    EmojiInProseRule(),
    ElegantVariationRule(),
    CopulaAvoidanceRule(),
    ExcessiveHedgingRule(),
    ParticipleChainsRule(),
    WrongMarkupRule(),
    ChatGPTMarkersRule(),
    UTMParametersRule(),
    BrokenReferencesRule(),
    UnresolvedMarkdownReferencesRule(),
    DocstringVocabularyRule(),
    VerboseCommentsRule(),
    CollaborativeCommentsRule(),
    AIPlaceholdersRule(),
]


class TestRuleRobustness:
    """Test that rules handle arbitrary input gracefully."""

    @pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.id)
    @given(content=text_content, filename=filenames)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_rule_never_crashes(self, rule: Rule, content: str, filename: str) -> None:
        """All rules should handle any input without crashing."""
        try:
            issues = rule.check(content, filename)
            assert isinstance(issues, list)
            for issue in issues:
                assert isinstance(issue, Issue)
        except Exception as e:
            pytest.fail(f"Rule {rule.id} crashed on input: {e}")

    @pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.id)
    @given(content=text_content, filename=filenames)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_issue_positions_valid(
        self, rule: Rule, content: str, filename: str
    ) -> None:
        """Issue positions should be within content bounds."""
        issues = rule.check(content, filename)
        lines = content.split("\n")

        for issue in issues:
            # Line number should be valid
            assert 1 <= issue.line <= len(lines) + 1, (
                f"Line {issue.line} out of bounds (1-{len(lines)})"
            )

            # Column should be positive
            assert issue.column >= 1, f"Column {issue.column} should be >= 1"

    @pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.id)
    @given(content=text_content, filename=filenames)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_rules_are_deterministic(
        self, rule: Rule, content: str, filename: str
    ) -> None:
        """Running a rule twice should give the same results."""
        issues1 = rule.check(content, filename)
        issues2 = rule.check(content, filename)

        assert len(issues1) == len(issues2)
        for i1, i2 in zip(issues1, issues2, strict=True):
            assert i1.rule_id == i2.rule_id
            assert i1.line == i2.line
            assert i1.column == i2.column
            assert i1.message == i2.message


class TestEmptyAndEdgeCases:
    """Test edge cases that should be handled gracefully."""

    @pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.id)
    def test_empty_content(self, rule: Rule) -> None:
        """Rules should handle empty content."""
        issues = rule.check("", "test.md")
        assert isinstance(issues, list)
        assert len(issues) == 0

    @pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.id)
    def test_whitespace_only(self, rule: Rule) -> None:
        """Rules should handle whitespace-only content."""
        issues = rule.check("   \n\t\n   ", "test.md")
        assert isinstance(issues, list)

    @pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.id)
    def test_single_character(self, rule: Rule) -> None:
        """Rules should handle single character content."""
        issues = rule.check("x", "test.md")
        assert isinstance(issues, list)

    @pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.id)
    def test_very_long_line(self, rule: Rule) -> None:
        """Rules should handle very long lines."""
        content = "a" * 10000
        issues = rule.check(content, "test.md")
        assert isinstance(issues, list)

    @pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.id)
    def test_many_short_lines(self, rule: Rule) -> None:
        """Rules should handle many short lines."""
        content = "\n".join(["x"] * 1000)
        issues = rule.check(content, "test.md")
        assert isinstance(issues, list)

    @pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.id)
    def test_unicode_content(self, rule: Rule) -> None:
        """Rules should handle unicode content."""
        content = "Hello 世界! Γεια σου κόσμε! 🌍🎉"
        issues = rule.check(content, "test.md")
        assert isinstance(issues, list)


class TestIssueInvariants:
    """Test that Issue objects maintain invariants."""

    @given(
        rule_id=st.text(min_size=1, max_size=10, alphabet="A-Z0-9"),
        message=st.text(min_size=1, max_size=100),
        line=st.integers(min_value=1, max_value=10000),
        column=st.integers(min_value=1, max_value=1000),
    )
    def test_issue_creation(
        self, rule_id: str, message: str, line: int, column: int
    ) -> None:
        """Issue should be constructable with valid parameters."""
        issue = Issue(
            rule_id=rule_id,
            message=message,
            line=line,
            column=column,
        )

        assert issue.rule_id == rule_id
        assert issue.message == message
        assert issue.line == line
        assert issue.column == column
        assert issue.severity == Severity.WARNING  # Default

    @given(
        line=st.integers(min_value=1),
        end_line=st.integers(min_value=1),
    )
    def test_issue_line_range(self, line: int, end_line: int) -> None:
        """When end_line is provided, it should be >= line."""
        assume(end_line >= line)  # Only test valid ranges

        issue = Issue(
            rule_id="TEST",
            message="test",
            line=line,
            column=1,
            end_line=end_line,
        )

        assert issue.end_line is not None
        assert issue.end_line >= issue.line


class TestParserInvariants:
    """Property tests for parser pure functions."""

    @given(content=text_content, filename=filenames)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_iter_prose_lines_in_bounds(self, content: str, filename: str) -> None:
        """Prose line numbers must reference valid lines in the original content."""
        from slop_lint.parsers.prose import iter_prose_lines

        result = iter_prose_lines(content, filename)
        total_lines = len(content.split("\n"))

        for line_num, line_text in result:
            assert 1 <= line_num <= total_lines, (
                f"Line {line_num} out of bounds (1-{total_lines})"
            )
            assert isinstance(line_text, str)

    @given(content=text_content, filename=filenames)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_iter_non_code_lines_subset(self, content: str, filename: str) -> None:
        """Non-code lines must be a subset of all lines."""
        from slop_lint.parsers.markdown import iter_non_code_lines

        result = iter_non_code_lines(content, filename)
        all_lines = content.split("\n")
        total = len(all_lines)

        line_nums = [n for n, _ in result]
        # No duplicates
        assert len(line_nums) == len(set(line_nums))
        # All in bounds
        for n in line_nums:
            assert 1 <= n <= total


class TestBaselineEntry:
    """Property tests for baseline entry stability."""

    @given(
        rule_id=st.text(min_size=1, max_size=10, alphabet="A-Z0-9"),
        message=st.text(min_size=1, max_size=100),
        line=st.integers(min_value=1, max_value=100),
        content=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_entry_is_deterministic(
        self, rule_id: str, message: str, line: int, content: str
    ) -> None:
        """Same inputs must always produce the same structured identity."""
        from pathlib import Path as P

        from slop_lint.core.baseline import Baseline

        lines = content.split("\n")
        line = min(line, len(lines))

        issue = Issue(rule_id=rule_id, message=message, line=line, column=1)
        bl = Baseline(P("/dev/null"))
        bl.add_issue(issue, P("test.md"), content)
        first = bl.entries
        bl.add_issue(issue, P("test.md"), content)

        assert bl.entries == first
