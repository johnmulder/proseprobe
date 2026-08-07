"""Tests for baseline functionality."""

import json
import os
from pathlib import Path

import pytest

from slop_lint.config import ConfigError
from slop_lint.core.baseline import (
    Baseline,
    filter_new_issues,
    resolve_workspace,
)
from slop_lint.rules.base import Confidence, Issue, Severity


class TestBaseline:
    """Tests for Baseline class."""

    def test_empty_baseline(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / ".slop-lint-baseline.json")
        assert baseline.count == 0
        assert not baseline.is_loaded

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / "nonexistent.json")
        assert not baseline.load()
        assert not baseline.is_loaded

    def test_save_and_load(self, tmp_path: Path) -> None:
        baseline_path = tmp_path / ".slop-lint-baseline.json"
        baseline = Baseline(baseline_path)

        # Add an issue
        issue = Issue(
            rule_id="V001",
            message="Overused word: 'delve'",
            line=5,
            column=6,
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
        assert baseline2.format_version == 2

        data = json.loads(baseline_path.read_text())
        assert data == {
            "version": 2,
            "entries": [
                {
                    "path": "test.md",
                    "rule_id": "V001",
                    "match": "delves",
                    "context_hash": baseline2.entries[0].context_hash,
                }
            ],
        }

    def test_is_new_issue(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / ".slop-lint-baseline.json")

        issue = Issue(
            rule_id="V001",
            message="Overused word: 'delve'",
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
        baseline = Baseline(tmp_path / ".slop-lint-baseline.json")

        issue1 = Issue(
            rule_id="V001",
            message="Overused word: 'delve'",
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

    def test_v2_identity_ignores_presentation_and_adjacent_lines(
        self, tmp_path: Path
    ) -> None:
        """Diagnostic wording, policy, and neighboring lines are not identity."""
        baseline = Baseline(tmp_path / "baseline.json")
        original = Issue(
            rule_id="V001",
            message="Old message",
            line=2,
            column=6,
            end_column=11,
            severity=Severity.WARNING,
            confidence=Confidence.LOW,
            suggestion="old",
        )
        file_path = tmp_path / "doc.md"
        baseline.add_issue(
            original, file_path, "before\nThis delve stays.\nafter", tmp_path
        )

        changed = Issue(
            rule_id="V001",
            message="Completely new message",
            line=3,
            column=6,
            end_column=11,
            severity=Severity.ERROR,
            confidence=Confidence.HIGH,
            suggestion="new",
        )
        content = "inserted\nchanged before\nThis delve stays.\nchanged after"

        assert not baseline.is_new_issue(changed, file_path, content, tmp_path)

    @pytest.mark.parametrize(
        ("rule_id", "content", "file_name"),
        [
            ("V001", "This explore stays.", "doc.md"),
            ("V002", "This delve stays.", "doc.md"),
            ("V001", "This delve stays.", "other.md"),
            ("V001", "Other words: delve stays.", "doc.md"),
        ],
    )
    def test_v2_identity_detects_source_changes(
        self, tmp_path: Path, rule_id: str, content: str, file_name: str
    ) -> None:
        """Changed evidence, rule, path, or local context should be new."""
        baseline = Baseline(tmp_path / "baseline.json")
        original = Issue("V001", "message", 1, 6, end_column=11)
        baseline.add_issue(original, tmp_path / "doc.md", "This delve stays.", tmp_path)

        changed = Issue(rule_id, "message", 1, content.index(" ") + 2, end_column=11)

        assert baseline.is_new_issue(changed, tmp_path / file_name, content, tmp_path)

    def test_match_normalizes_case_and_whitespace(self, tmp_path: Path) -> None:
        """Cosmetic case and whitespace changes should preserve a span."""
        baseline = Baseline(tmp_path / "baseline.json")
        issue = Issue("S001", "message", 1, 1, end_column=14)
        baseline.add_issue(issue, tmp_path / "doc.md", "Alpha   BETA", tmp_path)

        assert not baseline.is_new_issue(
            Issue("S001", "changed", 1, 1, end_column=11),
            tmp_path / "doc.md",
            "alpha beta",
            tmp_path,
        )

    def test_match_falls_back_to_token_at_column(self, tmp_path: Path) -> None:
        """Rules without end columns should use the token at their location."""
        baseline = Baseline(tmp_path / "baseline.json")
        issue = Issue("S001", "message", 1, 7)

        baseline.add_issue(issue, tmp_path / "doc.md", "Start triad here", tmp_path)

        assert baseline.entries[0].match == "triad"

    def test_save_is_byte_stable_and_sorted(self, tmp_path: Path) -> None:
        """Repeated saves should produce one reviewable ordering."""
        baseline_path = tmp_path / "baseline.json"
        baseline = Baseline(baseline_path)
        issue = Issue("V001", "message", 1, 1, end_column=6)
        baseline.add_issue(issue, tmp_path / "z.md", "delve", tmp_path)
        baseline.add_issue(issue, tmp_path / "a.md", "delve", tmp_path)

        baseline.save()
        first = baseline_path.read_bytes()
        baseline.save()

        assert baseline_path.read_bytes() == first
        assert [entry["path"] for entry in json.loads(first)["entries"]] == [
            "a.md",
            "z.md",
        ]

    def test_loads_version_one_for_compatibility(self, tmp_path: Path) -> None:
        """Legacy files should continue filtering with their old identity."""
        baseline_path = tmp_path / "baseline.json"
        baseline = Baseline(baseline_path)
        issue = Issue("V001", "Old message", 1, 1)
        file_path = tmp_path / "doc.md"
        content = "delve here"
        fingerprint = baseline._compute_legacy_fingerprint(
            issue, file_path, content, tmp_path
        )
        baseline_path.write_text(
            json.dumps({"version": "1.0", "fingerprints": [fingerprint]})
        )

        assert baseline.load()
        assert baseline.format_version == 1
        assert not baseline.is_new_issue(issue, file_path, content, tmp_path)

    @pytest.mark.parametrize(
        "payload",
        [
            "not json",
            "[]",
            '{"version": 2}',
            '{"version": 3, "entries": []}',
            '{"version": 2, "entries": "bad"}',
            '{"version": 2, "entries": [], "extra": true}',
            (
                '{"version": 2, "entries": [{"path": "/tmp/doc.md", '
                '"rule_id": "V001", "match": "delve", '
                '"context_hash": "0123456789abcdef"}]}'
            ),
            (
                '{"version": 2, "entries": ['
                '{"path": "doc.md", "rule_id": "V001", "match": "delve", '
                '"context_hash": "0123456789abcdef"}, '
                '{"path": "doc.md", "rule_id": "V001", "match": "delve", '
                '"context_hash": "0123456789abcdef"}]}'
            ),
        ],
    )
    def test_rejects_malformed_baselines(self, tmp_path: Path, payload: str) -> None:
        """Baseline schema errors should be actionable configuration errors."""
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(payload)

        with pytest.raises(ConfigError, match=r"baseline\.json"):
            Baseline(baseline_path).load()

    def test_atomic_save_failure_preserves_existing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failed replacement must not truncate a usable baseline."""
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text("original\n")
        baseline = Baseline(baseline_path)
        baseline.add_issue(
            Issue("V001", "message", 1, 1, end_column=6),
            tmp_path / "doc.md",
            "delve",
            tmp_path,
        )

        def fail_replace(_source: object, _target: object) -> None:
            raise OSError("replace failed")

        monkeypatch.setattr(os, "replace", fail_replace)

        with pytest.raises(ConfigError, match="replace failed"):
            baseline.save()

        assert baseline_path.read_text() == "original\n"
        assert list(tmp_path.glob("*.tmp")) == []


class TestResolveWorkspace:
    """Tests for deterministic baseline workspace selection."""

    def test_uses_shared_git_root_independent_of_order(self, tmp_path: Path) -> None:
        """Mixed file and directory inputs in one repository share one root."""
        (tmp_path / ".git").mkdir()
        docs = tmp_path / "docs"
        docs.mkdir()
        readme = tmp_path / "README.md"
        readme.write_text("text")

        assert resolve_workspace([readme, docs]) == tmp_path
        assert resolve_workspace([docs, readme]) == tmp_path

    def test_uses_common_root_outside_git(self, tmp_path: Path) -> None:
        """Non-repository inputs should use their deterministic common root."""
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        assert resolve_workspace([left, right]) == tmp_path


class TestFilterNewIssues:
    """Tests for filter_new_issues function."""

    def test_filter_removes_known_issues(self, tmp_path: Path) -> None:
        baseline = Baseline(tmp_path / ".slop-lint-baseline.json")

        issue1 = Issue(
            rule_id="V001",
            message="Overused word: 'delve'",
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
        baseline = Baseline(tmp_path / ".slop-lint-baseline.json")

        issue = Issue(
            rule_id="V001",
            message="Overused word: 'delve'",
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
