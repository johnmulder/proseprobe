"""Output formatting for lint results."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from slop_lint.rules.base import Confidence, Issue, Severity

__all__ = ["JSON_SCHEMA_VERSION", "format_results"]

# ---------------------------------------------------------------------------
# Format-specific helpers (each has a single reason to change)
# ---------------------------------------------------------------------------

_Results = dict[Path, list[Issue]]
JSON_SCHEMA_VERSION = 1


def _serialize_issue(issue: Issue) -> dict[str, Any]:
    """Serialize an issue for machine-readable output."""
    return {
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


def _format_text(results: _Results, *, quiet: bool = False) -> str:
    """Format results as human-readable text."""
    lines: list[str] = []

    for path, issues in sorted(results.items()):
        for issue in issues:
            if quiet and issue.severity != Severity.ERROR:
                continue
            conf_tag = (
                f" [{issue.confidence.value}]"
                if issue.confidence != Confidence.MEDIUM
                else ""
            )
            lines.append(
                f"{path}:{issue.line}:{issue.column}: "
                f"{issue.rule_id}{conf_tag} [{issue.severity.value}] {issue.message}"
            )

    if quiet:
        return "\n".join(lines)

    total = sum(len(issues) for issues in results.values())
    if total == 0:
        return "No issues found!"

    file_count = len(results)
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


def _format_json(results: _Results, files_checked: int | None = None) -> str:
    """Format results as JSON."""
    from slop_lint import __version__

    output: dict[str, Any] = {
        "schema_version": JSON_SCHEMA_VERSION,
        "version": __version__,
        "files": [],
        "summary": {
            "total_issues": 0,
            "files_checked": files_checked
            if files_checked is not None
            else len(results),
            "errors": 0,
            "warnings": 0,
            "info": 0,
        },
    }

    for path, issues in sorted(results.items()):
        file_entry = {
            "path": str(path),
            "issues": [_serialize_issue(issue) for issue in issues],
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


def _format_jsonl(results: _Results) -> str:
    """Format each issue as one JSON Lines record."""
    from slop_lint import __version__

    return "".join(
        json.dumps(
            {
                "schema_version": JSON_SCHEMA_VERSION,
                "version": __version__,
                "path": str(path),
                **_serialize_issue(issue),
            }
        )
        + "\n"
        for path, issues in sorted(results.items())
        for issue in issues
    )


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


def format_results(
    results: _Results,
    format: str = "text",
    rules: list[Any] | None = None,
    files_checked: int | None = None,
    *,
    quiet: bool = False,
) -> str:
    """Format lint results as text, JSON, JSON Lines, or SARIF."""
    if format == "sarif":
        return _format_sarif(results, rules)
    if format == "json":
        return _format_json(results, files_checked)
    if format == "jsonl":
        return _format_jsonl(results)
    return _format_text(results, quiet=quiet)
