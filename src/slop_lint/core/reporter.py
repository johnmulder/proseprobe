"""Output formatting for lint results."""

import json
from pathlib import Path
from typing import Any

from slop_lint.rules.base import Confidence, Issue, Severity

__all__ = ["Reporter"]


class Reporter:
    """Formats and outputs lint results."""

    def __init__(self, format: str = "text") -> None:
        """Initialize reporter.

        Args:
            format: Output format (text, json, sarif).
        """
        self.format = format

    def report(self, results: dict[Path, list[Issue]]) -> str:
        """Format results for output.

        Args:
            results: Mapping of file paths to issues.

        Returns:
            Formatted output string.
        """
        if self.format == "json":
            return self._format_json(results)
        elif self.format == "sarif":
            return self._format_sarif(results)
        else:
            return self._format_text(results)

    def _format_text(self, results: dict[Path, list[Issue]]) -> str:
        """Format results as text."""
        lines: list[str] = []

        for path, issues in sorted(results.items()):
            for issue in issues:
                severity_char = issue.severity.value[0].upper()
                conf_tag = f" [{issue.confidence.value}]" if issue.confidence != Confidence.MEDIUM else ""
                lines.append(
                    f"{path}:{issue.line}:{issue.column}: "
                    f"{severity_char}{issue.rule_id[1:]} {issue.message}{conf_tag}"
                )

        # Summary
        total = sum(len(issues) for issues in results.values())
        file_count = len(results)

        if total > 0:
            errors = sum(
                1
                for issues in results.values()
                for issue in issues
                if issue.severity == Severity.ERROR
            )
            warnings = sum(
                1
                for issues in results.values()
                for issue in issues
                if issue.severity == Severity.WARNING
            )
            info = sum(
                1
                for issues in results.values()
                for issue in issues
                if issue.severity == Severity.INFO
            )
            high_conf = sum(
                1
                for issues in results.values()
                for issue in issues
                if issue.confidence == Confidence.HIGH
            )
            medium_conf = sum(
                1
                for issues in results.values()
                for issue in issues
                if issue.confidence == Confidence.MEDIUM
            )
            low_conf = sum(
                1
                for issues in results.values()
                for issue in issues
                if issue.confidence == Confidence.LOW
            )
            lines.append("")
            lines.append(
                f"Found {total} issue(s) "
                f"({errors} error, {warnings} warning, {info} info) "
                f"in {file_count} file(s)"
            )
            if high_conf or low_conf:
                lines.append(
                    f"Confidence: {high_conf} high, "
                    f"{medium_conf} medium, {low_conf} low"
                )

        return "\n".join(lines)

    def _format_json(self, results: dict[Path, list[Issue]]) -> str:
        """Format results as JSON."""
        from slop_lint import __version__

        output: dict[str, Any] = {
            "version": __version__,
            "files": [],
            "summary": {
                "total_issues": 0,
                "files_checked": len(results),
                "errors": 0,
                "warnings": 0,
                "info": 0,
            },
        }

        for path, issues in sorted(results.items()):
            file_entry = {
                "path": str(path),
                "issues": [
                    {
                        "rule_id": issue.rule_id,
                        "message": issue.message,
                        "line": issue.line,
                        "column": issue.column,
                        "end_line": issue.end_line,
                        "end_column": issue.end_column,
                        "severity": issue.severity.value,
                        "confidence": issue.confidence.value,
                        "suggestion": issue.suggestion,
                    }
                    for issue in issues
                ],
            }
            output["files"].append(file_entry)

            for issue in issues:
                output["summary"]["total_issues"] += 1
                if issue.severity == Severity.ERROR:
                    output["summary"]["errors"] += 1
                elif issue.severity == Severity.WARNING:
                    output["summary"]["warnings"] += 1
                else:
                    output["summary"]["info"] += 1

        return json.dumps(output, indent=2)

    def _format_sarif(self, results: dict[Path, list[Issue]]) -> str:
        """Format results as SARIF 2.1.0."""
        from slop_lint import __version__
        from slop_lint.rules import get_all_rules

        # Build rule definitions
        rule_definitions = []
        for rule in get_all_rules():
            rule_definitions.append(
                {
                    "id": rule.id,
                    "name": rule.name,
                    "shortDescription": {"text": rule.description},
                    "defaultConfiguration": {
                        "level": self._sarif_level(rule.severity),
                    },
                    "properties": {
                        "category": self._rule_category(rule.id),
                    },
                }
            )

        sarif: dict[str, Any] = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "slop-lint",
                            "version": __version__,
                            "informationUri": "https://github.com/slop-lint/slop-lint",
                            "rules": rule_definitions,
                        }
                    },
                    "results": [],
                }
            ],
        }

        for path, issues in results.items():
            for issue in issues:
                result_entry: dict[str, Any] = {
                    "ruleId": issue.rule_id,
                    "level": self._sarif_level(issue.severity),
                    "message": {"text": issue.message},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": str(path)},
                                "region": {
                                    "startLine": issue.line,
                                    "startColumn": issue.column,
                                    "endLine": issue.end_line or issue.line,
                                    "endColumn": issue.end_column or issue.column,
                                },
                            }
                        }
                    ],
                    "properties": {
                        "confidence": issue.confidence.value,
                    },
                }
                # Map confidence to SARIF rank (0.0-100.0)
                rank_map = {
                    Confidence.HIGH: 90.0,
                    Confidence.MEDIUM: 50.0,
                    Confidence.LOW: 10.0,
                }
                result_entry["rank"] = rank_map.get(issue.confidence, 50.0)
                sarif["runs"][0]["results"].append(result_entry)

        return json.dumps(sarif, indent=2)

    def _sarif_level(self, severity: Severity) -> str:
        """Convert severity to SARIF level."""
        mapping = {
            Severity.ERROR: "error",
            Severity.WARNING: "warning",
            Severity.INFO: "note",
            Severity.OFF: "none",
        }
        return mapping.get(severity, "warning")

    def _rule_category(self, rule_id: str) -> str:
        """Get category name from rule ID prefix."""
        categories = {
            "V": "Vocabulary",
            "S": "Structure",
            "T": "Style",
            "G": "Grammar",
            "C": "Code",
            "M": "Markup",
        }
        return categories.get(rule_id[0], "Other")
