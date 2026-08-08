"""Tests for the reporter module."""

import json
from pathlib import Path

from proseprobe import __version__
from proseprobe.core.reporter import format_results
from proseprobe.rules.base import Confidence, Issue, Severity


class TestTextFormat:
    """Tests for text output format."""

    def test_format_no_issues(self) -> None:
        """Test formatting with no issues."""
        output = format_results({})

        assert output == "No issues found!"

    def test_format_single_issue(self) -> None:
        """Test formatting a single issue."""
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

        output = format_results(results)

        assert output.splitlines()[0] == (
            "doc.md:10:5: V001 [warning] Overused word: 'delve'"
        )

    def test_format_multiple_issues(self) -> None:
        """Test formatting multiple issues."""
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

        output = format_results(results)

        assert "a.md" in output
        assert "b.md" in output


class TestJsonFormat:
    """Tests for JSON output format."""

    def test_json_no_issues(self) -> None:
        """Test JSON format with no issues."""
        output = format_results({}, "json", files_checked=3)

        assert json.loads(output) == {
            "schema_version": 1,
            "version": __version__,
            "files": [],
            "summary": {
                "total_issues": 0,
                "files_checked": 3,
                "errors": 0,
                "warnings": 0,
                "info": 0,
            },
        }

    def test_json_issue_contract(self) -> None:
        """Test the complete JSON issue and summary contract."""
        results = {
            Path("test.md"): [
                Issue(
                    rule_id="V001",
                    message="Test message",
                    line=5,
                    column=10,
                    end_line=5,
                    end_column=15,
                    severity=Severity.WARNING,
                    confidence=Confidence.HIGH,
                    suggestion="Explore",
                ),
                Issue(
                    rule_id="S001",
                    message="Second message",
                    line=8,
                    column=1,
                    severity=Severity.INFO,
                ),
            ]
        }

        output = format_results(results, "json")

        assert json.loads(output) == {
            "schema_version": 1,
            "version": __version__,
            "files": [
                {
                    "path": "test.md",
                    "issues": [
                        {
                            "rule_id": "V001",
                            "message": "Test message",
                            "line": 5,
                            "column": 10,
                            "end_line": 5,
                            "end_column": 15,
                            "severity": "warning",
                            "confidence": "high",
                            "suggestion": "Explore",
                        },
                        {
                            "rule_id": "S001",
                            "message": "Second message",
                            "line": 8,
                            "column": 1,
                            "end_line": None,
                            "end_column": None,
                            "severity": "info",
                            "confidence": "medium",
                            "suggestion": None,
                        },
                    ],
                }
            ],
            "summary": {
                "total_issues": 2,
                "files_checked": 1,
                "errors": 0,
                "warnings": 1,
                "info": 1,
            },
        }


class TestJsonLinesFormat:
    """Tests for JSON Lines output format."""

    def test_jsonl_no_issues_is_empty(self) -> None:
        """A clean JSONL report has no records."""
        assert format_results({}, "jsonl", files_checked=3) == ""

    def test_jsonl_issue_contract_and_order(self) -> None:
        """Each issue is one complete, deterministically ordered record."""
        results = {
            Path("z.md"): [
                Issue(
                    rule_id="S001",
                    message="Nullable fields",
                    line=8,
                    column=1,
                    severity=Severity.INFO,
                )
            ],
            Path("a.md"): [
                Issue(
                    rule_id="V001",
                    message="First issue",
                    line=5,
                    column=10,
                    end_line=5,
                    end_column=15,
                    severity=Severity.WARNING,
                    confidence=Confidence.HIGH,
                    suggestion="Explore",
                ),
                Issue(
                    rule_id="G001",
                    message="Second issue",
                    line=6,
                    column=2,
                    severity=Severity.WARNING,
                ),
            ],
        }

        output = format_results(results, "jsonl")

        assert output.endswith("\n")
        assert output.count("\n") == 3
        assert [json.loads(line) for line in output.splitlines()] == [
            {
                "schema_version": 1,
                "version": __version__,
                "path": "a.md",
                "rule_id": "V001",
                "message": "First issue",
                "line": 5,
                "column": 10,
                "end_line": 5,
                "end_column": 15,
                "severity": "warning",
                "confidence": "high",
                "suggestion": "Explore",
            },
            {
                "schema_version": 1,
                "version": __version__,
                "path": "a.md",
                "rule_id": "G001",
                "message": "Second issue",
                "line": 6,
                "column": 2,
                "end_line": None,
                "end_column": None,
                "severity": "warning",
                "confidence": "medium",
                "suggestion": None,
            },
            {
                "schema_version": 1,
                "version": __version__,
                "path": "z.md",
                "rule_id": "S001",
                "message": "Nullable fields",
                "line": 8,
                "column": 1,
                "end_line": None,
                "end_column": None,
                "severity": "info",
                "confidence": "medium",
                "suggestion": None,
            },
        ]


class TestSarifFormat:
    """Tests for SARIF output format."""

    def test_sarif_schema(self) -> None:
        """Test SARIF output has correct schema."""
        output = format_results({}, "sarif")

        data = json.loads(output)
        assert "$schema" in data
        assert "runs" in data

    def test_sarif_with_issues(self) -> None:
        """Test SARIF output with issues."""
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

        output = format_results(results, "sarif")
        data = json.loads(output)

        assert len(data["runs"]) > 0
        run = data["runs"][0]
        assert "results" in run


class TestConfidenceOutput:
    """Tests for confidence in reporter output."""

    def test_text_annotates_non_medium_confidence(self) -> None:
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
        output = format_results(results)
        assert output.splitlines()[0] == (
            "doc.md:1:1: V001 [high] [warning] Overused word: 'delve'"
        )

    def test_text_no_tag_for_medium(self) -> None:
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
        output = format_results(results)
        assert "[high]" not in output
        assert "[low]" not in output

    def test_json_includes_confidence(self) -> None:
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
        data = json.loads(format_results(results, "json"))
        issue_data = data["files"][0]["issues"][0]
        assert issue_data["confidence"] == "low"

    def test_sarif_includes_confidence(self) -> None:
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
        data = json.loads(format_results(results, "sarif"))
        result_entry = data["runs"][0]["results"][0]
        assert result_entry["properties"]["confidence"] == "high"
        assert result_entry["rank"] == 90.0

    def test_text_confidence_summary(self) -> None:
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
        output = format_results(results)
        assert "Confidence:" in output
        assert "1 high" in output
        assert "1 low" in output


class TestQuietText:
    """Tests for reporter-owned quiet output."""

    def test_quiet_formats_only_errors_without_summary(self) -> None:
        results = {
            Path("doc.md"): [
                Issue(
                    rule_id="V001",
                    message="Warning",
                    line=1,
                    column=1,
                    severity=Severity.WARNING,
                ),
                Issue(
                    rule_id="V002",
                    message="Error",
                    line=2,
                    column=1,
                    severity=Severity.ERROR,
                ),
            ]
        }

        output = format_results(results, quiet=True)

        assert output == "doc.md:2:1: V002 [error] Error"
