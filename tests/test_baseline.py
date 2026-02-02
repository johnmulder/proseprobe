"""Tests for baseline functionality."""

from pathlib import Path

from humanize.core.baseline import Baseline, IssueFingerprint, filter_new_issues
from humanize.rules.base import Issue, Severity


class TestIssueFingerprint:
    """Tests for IssueFingerprint."""

    def test_to_dict(self) -> None:
        fp = IssueFingerprint(
            rule_id="V001",
            message_hash="abc123",
            relative_path="test.md",
            context_hash="def456",
        )
        result = fp.to_dict()
        assert result["rule_id"] == "V001"
        assert result["message_hash"] == "abc123"

    def test_from_dict(self) -> None:
        data = {
            "rule_id": "V001",
            "message_hash": "abc123",
            "relative_path": "test.md",
            "context_hash": "def456",
        }
        fp = IssueFingerprint.from_dict(data)
        assert fp.rule_id == "V001"
        assert fp.message_hash == "abc123"


class TestBaseline:
    """Tests for Baseline class."""

    def test_empty_baseline(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / ".humanize-baseline.json")
        assert baseline.count == 0
        assert not baseline.is_loaded

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / "nonexistent.json")
        assert not baseline.load()
        assert not baseline.is_loaded

    def test_save_and_load(self, tmp_path: Path) -> None:
        baseline_path = tmp_path / ".humanize-baseline.json"
        baseline = Baseline(baseline_path)

        # Add an issue
        issue = Issue(
            rule_id="V001",
            message="AI vocabulary: 'delve'",
            line=5,
            column=10,
            severity=Severity.WARNING,
        )
        content = "line1\nline2\nline3\nline4\nThis delves into topic\nline6"
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        baseline.add_issue(issue, file_path, content, tmp_path)
        assert baseline.count == 1

        baseline.save()
        assert baseline_path.exists()

        # Load in new instance
        baseline2 = Baseline(baseline_path)
        assert baseline2.load()
        assert baseline2.is_loaded
        assert baseline2.count == 1

    def test_is_new_issue(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / ".humanize-baseline.json")

        issue = Issue(
            rule_id="V001",
            message="AI vocabulary: 'delve'",
            line=5,
            column=10,
            severity=Severity.WARNING,
        )
        content = "line1\nline2\nline3\nline4\nThis delves into topic\nline6"
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        # Issue is new initially
        assert baseline.is_new_issue(issue, file_path, content, tmp_path)

        # Add to baseline
        baseline.add_issue(issue, file_path, content, tmp_path)

        # Issue is no longer new
        assert not baseline.is_new_issue(issue, file_path, content, tmp_path)

    def test_different_issues_are_new(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / ".humanize-baseline.json")

        issue1 = Issue(
            rule_id="V001",
            message="AI vocabulary: 'delve'",
            line=5,
            column=10,
            severity=Severity.WARNING,
        )
        issue2 = Issue(
            rule_id="V002",
            message="Collaborative phrase: 'I hope this helps'",
            line=10,
            column=1,
            severity=Severity.WARNING,
        )
        content = "line1\nline2\nline3\nline4\nThis delves into topic\nline6\n" * 3
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        baseline.add_issue(issue1, file_path, content, tmp_path)

        # Different issue is still new
        assert baseline.is_new_issue(issue2, file_path, content, tmp_path)


class TestFilterNewIssues:
    """Tests for filter_new_issues function."""

    def test_filter_removes_known_issues(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / ".humanize-baseline.json")

        issue1 = Issue(
            rule_id="V001",
            message="AI vocabulary: 'delve'",
            line=5,
            column=10,
            severity=Severity.WARNING,
        )
        issue2 = Issue(
            rule_id="V002",
            message="Collaborative phrase",
            line=10,
            column=1,
            severity=Severity.WARNING,
        )

        file_path = tmp_path / "test.md"
        content = "line1\nline2\nline3\nline4\nThis delves into topic\nline6\n" * 3
        file_path.write_text(content)

        # Add issue1 to baseline
        baseline.add_issue(issue1, file_path, content, tmp_path)

        results = {file_path: [issue1, issue2]}
        filtered = filter_new_issues(results, baseline, tmp_path)

        # Only issue2 should remain
        assert file_path in filtered
        assert len(filtered[file_path]) == 1
        assert filtered[file_path][0].rule_id == "V002"

    def test_filter_empty_when_all_known(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / ".humanize-baseline.json")

        issue = Issue(
            rule_id="V001",
            message="AI vocabulary: 'delve'",
            line=5,
            column=10,
            severity=Severity.WARNING,
        )

        file_path = tmp_path / "test.md"
        content = "line1\nline2\nline3\nline4\nThis delves into topic\nline6"
        file_path.write_text(content)

        baseline.add_issue(issue, file_path, content, tmp_path)

        results = {file_path: [issue]}
        filtered = filter_new_issues(results, baseline, tmp_path)

        # No issues should remain
        assert len(filtered) == 0
