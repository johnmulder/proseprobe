"""Additional tests for fixer module."""

from pathlib import Path

from slop_lint.core.fixer import Fixer
from slop_lint.rules.base import Issue, Rule, Severity


class SimpleMockRule(Rule):
    """Mock rule for testing fixer."""

    id = "MOCK"
    name = "Mock Rule"
    description = "A mock rule for testing"
    severity = Severity.WARNING
    fixable = True

    def check(self, content: str, filename: str) -> list[Issue]:
        """Return empty list for mock."""
        return []

    def fix(self, content: str, issue: Issue) -> str:
        """Apply fix by replacing 'bad' with 'good'."""
        return content.replace("bad", "good")


class TestFixer:
    """Tests for the Fixer class."""

    def test_fixer_creation(self) -> None:
        """Test creating a Fixer instance."""
        rule = SimpleMockRule()
        fixer = Fixer([rule])
        assert fixer is not None

    def test_fix_file(self, tmp_path: Path) -> None:
        """Test fixing a file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This is bad content.")

        rule = SimpleMockRule()
        fixer = Fixer([rule])

        issue = Issue(
            rule_id="MOCK",
            message="Test",
            line=1,
            column=1,
            severity=Severity.WARNING,
            fixable=True,
        )

        fixed_content, count = fixer.fix_file(test_file, [issue])

        assert fixed_content == "This is good content."
        assert count == 1

    def test_fix_file_no_fixable_issues(self, tmp_path: Path) -> None:
        """Test fixing a file with no fixable issues."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This is content.")

        rule = SimpleMockRule()
        fixer = Fixer([rule])

        issue = Issue(
            rule_id="MOCK",
            message="Test",
            line=1,
            column=1,
            severity=Severity.WARNING,
            fixable=False,  # Not fixable
        )

        fixed_content, count = fixer.fix_file(test_file, [issue])

        assert fixed_content == "This is content."
        assert count == 0

    def test_fix_and_write(self, tmp_path: Path) -> None:
        """Test fixing and writing back to file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This is bad content.")

        rule = SimpleMockRule()
        fixer = Fixer([rule])

        issue = Issue(
            rule_id="MOCK",
            message="Test",
            line=1,
            column=1,
            severity=Severity.WARNING,
            fixable=True,
        )

        count = fixer.fix_and_write(test_file, [issue])

        assert count == 1
        assert test_file.read_text() == "This is good content."

    def test_fix_unknown_rule(self, tmp_path: Path) -> None:
        """Test fixing with unknown rule ID."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This is content.")

        rule = SimpleMockRule()
        fixer = Fixer([rule])

        issue = Issue(
            rule_id="UNKNOWN",  # Unknown rule
            message="Test",
            line=1,
            column=1,
            severity=Severity.WARNING,
            fixable=True,
        )

        fixed_content, count = fixer.fix_file(test_file, [issue])

        assert count == 0


class TestRuleBase:
    """Tests for the base Rule class."""

    def test_rule_fix_method(self) -> None:
        """Test that fix method works."""
        rule = SimpleMockRule()

        issue = Issue(
            rule_id="MOCK",
            message="Test",
            line=1,
            column=1,
            severity=Severity.WARNING,
        )

        content = "This is bad."
        fixed = rule.fix(content, issue)
        assert fixed == "This is good."
