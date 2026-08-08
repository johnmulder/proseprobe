"""Tests using fixture samples with known bad practices and clean writing."""

from pathlib import Path

import pytest

from proseprobe.config import Config
from proseprobe.core.linter import Linter
from proseprobe.rules import get_all_rules

FIXTURES_DIR = Path(__file__).parent / "fixtures"
AI_GENERATED = FIXTURES_DIR / "ai_generated"
HUMAN_WRITTEN = FIXTURES_DIR / "human_written"


@pytest.fixture
def linter() -> Linter:
    """Create a linter with all rules enabled."""
    config = Config()
    lint = Linter(config)
    for rule in get_all_rules():
        lint.register_rule(rule)
    return lint


class TestAIGeneratedFixtures:
    """Tests that samples with bad practices trigger rules."""

    def test_ai_markdown_sample1_has_issues(self, linter: Linter) -> None:
        """sample1.md should trigger multiple rules."""
        results = linter.check([AI_GENERATED / "sample1.md"])

        assert len(results.issues_by_file) > 0
        all_issues = []
        for issues in results.issues_by_file.values():
            all_issues.extend(issues)

        # Should find overused vocabulary
        rule_ids = {issue.rule_id for issue in all_issues}
        assert "V001" in rule_ids, "Expected V001 (overused vocabulary) to trigger"

    def test_ai_markdown_sample2_has_multiple_rule_types(self, linter: Linter) -> None:
        """sample2.md should trigger vocabulary, markup, and structural rules."""
        results = linter.check([AI_GENERATED / "sample2.md"])

        all_issues = []
        for issues in results.issues_by_file.values():
            all_issues.extend(issues)

        rule_ids = {issue.rule_id for issue in all_issues}

        # Should have vocabulary issues
        assert any(rid.startswith("V") for rid in rule_ids), "Expected vocabulary rules"
        # Should have markup issues (utm parameters, chatgpt markers)
        assert any(rid.startswith("M") for rid in rule_ids), "Expected markup rules"

    def test_ai_python_sample1_has_docstring_issues(self, linter: Linter) -> None:
        """sample1.py should trigger code-specific rules."""
        results = linter.check([AI_GENERATED / "sample1.py"])

        all_issues = []
        for issues in results.issues_by_file.values():
            all_issues.extend(issues)

        # Should find issues in docstrings
        assert len(all_issues) > 0, (
            "Expected issues in Python sample with bad practices"
        )

    def test_ai_python_sample2_has_code_issues(self, linter: Linter) -> None:
        """sample2.py should trigger multiple code rules."""
        results = linter.check([AI_GENERATED / "sample2.py"])

        all_issues = []
        for issues in results.issues_by_file.values():
            all_issues.extend(issues)

        # Should have code-specific issues
        assert len(all_issues) >= 3, (
            "Expected multiple issues in bad-practice Python sample"
        )


class TestHumanWrittenFixtures:
    """Tests that human-written samples have minimal issues."""

    def test_human_markdown_sample1_is_clean(self, linter: Linter) -> None:
        """Human-written sample1.md should have few/no issues."""
        results = linter.check([HUMAN_WRITTEN / "sample1.md"])

        total_issues = sum(len(issues) for issues in results.issues_by_file.values())
        # May have some style issues but should be minimal
        assert total_issues < 5, f"Expected few issues, got {total_issues}"

    def test_human_markdown_sample2_is_clean(self, linter: Linter) -> None:
        """Human-written sample2.md should have few/no issues."""
        results = linter.check([HUMAN_WRITTEN / "sample2.md"])

        total_issues = sum(len(issues) for issues in results.issues_by_file.values())
        assert total_issues < 3, f"Expected minimal issues, got {total_issues}"

    def test_human_python_sample1_is_clean(self, linter: Linter) -> None:
        """Human-written sample1.py should have minimal issues."""
        results = linter.check([HUMAN_WRITTEN / "sample1.py"])

        total_issues = sum(len(issues) for issues in results.issues_by_file.values())
        assert total_issues < 3, f"Expected minimal issues, got {total_issues}"

    def test_human_python_sample2_is_clean(self, linter: Linter) -> None:
        """Human-written sample2.py should have minimal issues."""
        results = linter.check([HUMAN_WRITTEN / "sample2.py"])

        total_issues = sum(len(issues) for issues in results.issues_by_file.values())
        assert total_issues < 2, f"Expected minimal issues, got {total_issues}"


class TestComparativeAnalysis:
    """Compare bad-practice samples vs clean samples."""

    def test_ai_samples_have_more_issues_than_human(self, linter: Linter) -> None:
        """Bad-practice samples should trigger more rules than clean samples."""
        ai_results = linter.check([AI_GENERATED])
        human_results = linter.check([HUMAN_WRITTEN])

        ai_total = sum(len(issues) for issues in ai_results.issues_by_file.values())
        human_total = sum(
            len(issues) for issues in human_results.issues_by_file.values()
        )

        assert ai_total > human_total, (
            f"Bad-practice samples ({ai_total}) should have more issues than "
            f"human samples ({human_total})"
        )

    def test_ai_samples_trigger_more_rule_categories(self, linter: Linter) -> None:
        """Bad-practice samples should trigger rules from more categories."""
        ai_results = linter.check([AI_GENERATED])

        all_issues = []
        for issues in ai_results.issues_by_file.values():
            all_issues.extend(issues)

        # Get unique category prefixes
        categories = {issue.rule_id[0] for issue in all_issues}

        # Should trigger at least 3 different categories
        assert len(categories) >= 3, f"Expected 3+ categories, got {categories}"
