"""Tests for the reporter module."""

import json
from pathlib import Path

from slop_lint.core.reporter import Reporter
from slop_lint.rules.base import Confidence, Issue, Severity


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

    def test_json_reports_files_checked_from_metadata(self) -> None:
        """JSON summary should distinguish checked files from files with issues."""
        reporter = Reporter(format="json", files_checked=3)

        output = reporter.report({})

        data = json.loads(output)
        assert data["summary"]["files_checked"] == 3

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


class TestConfidenceOutput:
    """Tests for confidence in reporter output."""

    def test_text_annotates_non_medium_confidence(self) -> None:
        reporter = Reporter(format="text")
        results = {
            Path("doc.md"): [
                Issue(
                    rule_id="V001",
                    message="Overused word: 'delve'",
                    line=1,
                    column=1,
                    severity=Severity.WARNING,
                    confidence=Confidence.HIGH,
                )
            ]
        }
        output = reporter.report(results)
        assert "[high]" in output

    def test_text_no_tag_for_medium(self) -> None:
        reporter = Reporter(format="text")
        results = {
            Path("doc.md"): [
                Issue(
                    rule_id="V001",
                    message="Overused word",
                    line=1,
                    column=1,
                    severity=Severity.WARNING,
                    confidence=Confidence.MEDIUM,
                )
            ]
        }
        output = reporter.report(results)
        assert "[high]" not in output
        assert "[low]" not in output

    def test_json_includes_confidence(self) -> None:
        reporter = Reporter(format="json")
        results = {
            Path("doc.md"): [
                Issue(
                    rule_id="V001",
                    message="Test",
                    line=1,
                    column=1,
                    severity=Severity.WARNING,
                    confidence=Confidence.LOW,
                )
            ]
        }
        data = json.loads(reporter.report(results))
        issue_data = data["files"][0]["issues"][0]
        assert issue_data["confidence"] == "low"

    def test_sarif_includes_confidence(self) -> None:
        reporter = Reporter(format="sarif")
        results = {
            Path("doc.md"): [
                Issue(
                    rule_id="V001",
                    message="Test",
                    line=1,
                    column=1,
                    severity=Severity.WARNING,
                    confidence=Confidence.HIGH,
                )
            ]
        }
        data = json.loads(reporter.report(results))
        result_entry = data["runs"][0]["results"][0]
        assert result_entry["properties"]["confidence"] == "high"
        assert result_entry["rank"] == 90.0

    def test_text_confidence_summary(self) -> None:
        reporter = Reporter(format="text")
        results = {
            Path("doc.md"): [
                Issue(
                    rule_id="V001",
                    message="A",
                    line=1,
                    column=1,
                    severity=Severity.WARNING,
                    confidence=Confidence.HIGH,
                ),
                Issue(
                    rule_id="V002",
                    message="B",
                    line=2,
                    column=1,
                    severity=Severity.WARNING,
                    confidence=Confidence.LOW,
                ),
            ]
        }
        output = reporter.report(results)
        assert "Confidence:" in output
        assert "1 high" in output
        assert "1 low" in output
