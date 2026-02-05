"""Tests for the reporter module."""

import json
from pathlib import Path

from slop_lint.core.reporter import Reporter
from slop_lint.rules.base import Issue, Severity


class TestReporter:
    """Tests for the Reporter class."""

    def test_reporter_creation(self) -> None:
        """Test creating a Reporter."""
        reporter = Reporter()
        assert reporter is not None
        assert reporter.format == "text"

    def test_reporter_with_format(self) -> None:
        """Test creating a Reporter with format."""
        reporter = Reporter(format="json")
        assert reporter.format == "json"


class TestTextFormat:
    """Tests for text output format."""

    def test_format_no_issues(self) -> None:
        """Test formatting with no issues."""
        reporter = Reporter(format="text")
        output = reporter.report({})

        # No issues means empty or minimal output
        assert isinstance(output, str)

    def test_format_single_issue(self) -> None:
        """Test formatting a single issue."""
        reporter = Reporter(format="text")
        results = {
            Path("doc.md"): [
                Issue(
                    rule_id="V001",
                    message="Overused word: 'delve'",
                    line=10,
                    column=5,
                    severity=Severity.WARNING,
                )
            ]
        }

        output = reporter.report(results)

        assert "V001" in output or "001" in output
        assert "doc.md" in output
        assert "10" in output

    def test_format_multiple_issues(self) -> None:
        """Test formatting multiple issues."""
        reporter = Reporter(format="text")
        results = {
            Path("a.md"): [
                Issue(
                    rule_id="V001",
                    message="Issue 1",
                    line=1,
                    column=1,
                    severity=Severity.WARNING,
                ),
            ],
            Path("b.md"): [
                Issue(
                    rule_id="V002",
                    message="Issue 2",
                    line=2,
                    column=1,
                    severity=Severity.WARNING,
                ),
            ],
        }

        output = reporter.report(results)

        assert "a.md" in output
        assert "b.md" in output


class TestJsonFormat:
    """Tests for JSON output format."""

    def test_json_no_issues(self) -> None:
        """Test JSON format with no issues."""
        reporter = Reporter(format="json")
        output = reporter.report({})

        data = json.loads(output)
        assert isinstance(data, dict)

    def test_json_single_issue(self) -> None:
        """Test JSON format with single issue."""
        reporter = Reporter(format="json")
        results = {
            Path("test.md"): [
                Issue(
                    rule_id="V001",
                    message="Test message",
                    line=5,
                    column=10,
                    severity=Severity.WARNING,
                )
            ]
        }

        output = reporter.report(results)
        data = json.loads(output)

        assert isinstance(data, dict)
        # Verify the JSON contains issue information
        output_str = json.dumps(data)
        assert "V001" in output_str


class TestSarifFormat:
    """Tests for SARIF output format."""

    def test_sarif_schema(self) -> None:
        """Test SARIF output has correct schema."""
        reporter = Reporter(format="sarif")
        output = reporter.report({})

        data = json.loads(output)
        assert "$schema" in data
        assert "runs" in data

    def test_sarif_with_issues(self) -> None:
        """Test SARIF output with issues."""
        reporter = Reporter(format="sarif")
        results = {
            Path("test.md"): [
                Issue(
                    rule_id="V001",
                    message="Test",
                    line=1,
                    column=1,
                    severity=Severity.WARNING,
                )
            ]
        }

        output = reporter.report(results)
        data = json.loads(output)

        assert len(data["runs"]) > 0
        run = data["runs"][0]
        assert "results" in run
