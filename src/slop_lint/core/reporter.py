"""Output formatting for lint results."""

import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from slop_lint.rules.base import Confidence, Issue, Severity

__all__ = ["Reporter"]

# ---------------------------------------------------------------------------
# Format-specific helpers (each has a single reason to change)
# ---------------------------------------------------------------------------

_Results = dict[Path, list[Issue]]


def _format_text(results: _Results) -> str:
    """Format results as human-readable text."""
    lines: list[str] = []

    for path, issues in sorted(results.items()):
        for issue in issues:
            severity_char = issue.severity.value[0].upper()
            conf_tag = (
                f" [{issue.confidence.value}]"
                if issue.confidence != Confidence.MEDIUM
                else ""
            )
            lines.append(
                f"{path}:{issue.line}:{issue.column}: "
                f"{severity_char}{issue.rule_id[1:]} {issue.message}{conf_tag}"
            )

    # Summary — single pass over all issues
    total = sum(len(issues) for issues in results.values())
    file_count = len(results)

    if total > 0:
        sev_counts: Counter[Severity] = Counter()
        conf_counts: Counter[Confidence] = Counter()
        for issues in results.values():
            for issue in issues:
                sev_counts[issue.severity] += 1
                conf_counts[issue.confidence] += 1

        lines.append("")
        lines.append(
            f"Found {total} issue(s) "
            f"({sev_counts[Severity.ERROR]} error, "
            f"{sev_counts[Severity.WARNING]} warning, "
            f"{sev_counts[Severity.INFO]} info) "
            f"in {file_count} file(s)"
        )
        if conf_counts[Confidence.HIGH] or conf_counts[Confidence.LOW]:
            lines.append(
                f"Confidence: {conf_counts[Confidence.HIGH]} high, "
                f"{conf_counts[Confidence.MEDIUM]} medium, "
                f"{conf_counts[Confidence.LOW]} low"
            )

    return "\n".join(lines)


def _format_json(results: _Results) -> str:
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


_SARIF_LEVEL = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
    Severity.OFF: "none",
}

_SARIF_RANK = {
    Confidence.HIGH: 90.0,
    Confidence.MEDIUM: 50.0,
    Confidence.LOW: 10.0,
}


def _format_sarif(results: _Results, rules: list[Any] | None = None) -> str:
    """Format results as SARIF 2.1.0."""
    from slop_lint import __version__

    if rules is None:
        from slop_lint.rules import get_all_rules

        rules = list(get_all_rules())

    rule_definitions = [
        {
            "id": rule.id,
            "name": rule.name,
            "shortDescription": {"text": rule.description},
            "defaultConfiguration": {
                "level": _SARIF_LEVEL.get(rule.severity, "warning"),
            },
            "properties": {
                "category": rule.category,
            },
        }
        for rule in rules
    ]

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
                "level": _SARIF_LEVEL.get(issue.severity, "warning"),
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
                "rank": _SARIF_RANK.get(issue.confidence, 50.0),
            }
            sarif["runs"][0]["results"].append(result_entry)

    return json.dumps(sarif, indent=2)


# ---------------------------------------------------------------------------
# Public facade (preserves existing API)
# ---------------------------------------------------------------------------

_Formatter = Callable[[_Results], str]

_FORMATTERS: dict[str, _Formatter] = {
    "text": _format_text,
    "json": _format_json,
    "sarif": _format_sarif,
}


class Reporter:
    """Formats and outputs lint results."""

    def __init__(
        self,
        format: str = "text",
        rules: list[Any] | None = None,
    ) -> None:
        """Initialize reporter.

        Args:
            format: Output format (text, json, sarif).
            rules: Optional list of Rule instances for SARIF metadata.
                   When *None*, SARIF will discover rules lazily.
        """
        self.format = format
        self._rules = rules

    def report(self, results: dict[Path, list[Issue]]) -> str:
        """Format results for output.

        Args:
            results: Mapping of file paths to issues.

        Returns:
            Formatted output string.
        """
        if self.format == "sarif":
            return _format_sarif(results, rules=self._rules)
        formatter = _FORMATTERS.get(self.format, _format_text)
        return formatter(results)
