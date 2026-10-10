"""Report reviewed revision correspondence separately from warning changes."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from benchmarks.evaluation_identity import diagnostic_sha256

HUMAN_FIELDS = (
    "finding_helpful",
    "suggestion_fits_sentence",
    "meaning_preserved",
    "reviewer_accepts",
)
HUMAN_ANSWERS = ("yes", "no", "context-dependent", "unresolved", "unreviewed")
JUDGMENTS = {"valid", "incorrect", "context-dependent", "unresolved", "unreviewed"}
FINDING_FIELDS = {
    "rule_id",
    "message",
    "line",
    "column",
    "end_line",
    "end_column",
    "severity",
    "confidence",
    "suggestion",
}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} requires a nonempty string")
    return value


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} requires an object")
    return value


def _evaluation(
    record: dict[str, Any], raw: bytes, side: str
) -> dict[str, dict[str, Any]]:
    if record.get("source_binding") != "sha256-utf8":
        raise ValueError(f"{side} requires sha256-utf8 source binding")
    source = _object(record.get("source"), f"{side} source")
    for field in ("source_id", "path", "sha256", "source_group", "pair_group"):
        _text(source.get(field), f"{side} source {field}")
    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise ValueError(f"{side} source bytes differ from the bound SHA-256")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ValueError(f"{side} source bytes must be UTF-8") from error
    runtime = _object(record.get("runtime"), f"{side} runtime")
    for field in ("package_version", "source_sha256"):
        _text(runtime.get(field), f"{side} runtime {field}")
    digest = runtime["source_sha256"]
    if len(digest) != 64 or set(digest) - set("0123456789abcdef"):
        raise ValueError(f"{side} runtime source_sha256 must be a SHA-256 digest")
    if not isinstance(record.get("policy"), dict):
        raise ValueError(f"{side} requires an effective policy")
    findings = record.get("findings")
    if not isinstance(findings, list):
        raise ValueError(f"{side} findings must be a list")
    indexed = {}
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != FINDING_FIELDS:
            raise ValueError(f"{side} requires complete Issue-shaped finding records")
        _text(finding["rule_id"], f"{side} finding rule_id")
        _text(finding["message"], f"{side} finding message")
        if finding["severity"] not in {"info", "warning", "error"}:
            raise ValueError(f"{side} finding has invalid severity")
        if finding["confidence"] not in {"low", "medium", "high"}:
            raise ValueError(f"{side} finding has invalid confidence")
        if finding["suggestion"] is not None and not isinstance(
            finding["suggestion"], str
        ):
            raise ValueError(f"{side} finding has invalid suggestion")
        if finding["end_line"] is not None and finding["end_column"] is None:
            raise ValueError(f"{side} finding end_line requires end_column")
        start = (finding["line"], finding["column"])
        end = None
        if finding["end_column"] is not None:
            last_line = (
                finding["line"] if finding["end_line"] is None else finding["end_line"]
            )
            end = (last_line, finding["end_column"])
        for line, column in (start,) if end is None else (start, end):
            if (
                type(line) is not int
                or type(column) is not int
                or not 1 <= line <= len(lines)
                or not 1 <= column <= len(lines[line - 1]) + 1
            ):
                raise ValueError(
                    f"{side} finding coordinates fall outside source bytes"
                )
        if end is not None and end < start:
            raise ValueError(f"{side} finding end precedes its start")
        if end == start and finding["rule_id"] != "M004":
            raise ValueError(f"{side} finding has a zero-width span")
        identity = diagnostic_sha256(finding)
        if identity in indexed:
            raise ValueError(f"{side} has a duplicate diagnostic identity")
        indexed[identity] = finding
    return indexed


def paired_report(
    original: dict[str, Any],
    revision: dict[str, Any],
    original_bytes: bytes,
    revision_bytes: bytes,
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Report an exact source pair using only explicitly reviewed correspondence.

    Each evaluation supplies source_binding, source, findings, policy and runtime.
    A revision's source declares original_source_id. Optional review records bind
    both sources and name a reviewer and correspondence IDs. Endpoints refer to
    complete diagnostic SHA-256 identities; no automatic alignment is attempted.
    """
    originals = _evaluation(original, original_bytes, "original")
    revisions = _evaluation(revision, revision_bytes, "revision")
    original_source, revision_source = original["source"], revision["source"]
    for field in ("pair_group", "source_group"):
        if original_source[field] != revision_source[field]:
            raise ValueError(f"revision {field} differs from original")
    if revision_source.get("original_source_id") != original_source["source_id"]:
        raise ValueError("revision original_source_id differs from original")
    if revision_source["source_id"] == original_source["source_id"]:
        raise ValueError("original and revision require distinct source_id values")
    if original["policy"] != revision["policy"]:
        raise ValueError("paired evaluations require the same effective policy")
    for field in ("package_version", "source_sha256"):
        if original["runtime"][field] != revision["runtime"][field]:
            raise ValueError(f"paired evaluations differ in actual runtime {field}")

    used: dict[str, set[str]] = {"original": set(), "revision": set()}
    rows = []
    transitions = {"removed": 0, "retained": 0, "new": 0}
    judgments = {"removed_valid": 0, "retained_valid": 0, "new_incorrect": 0}
    if review is not None:
        _text(review.get("review_id"), "review_id")
        _text(review.get("reviewer"), "reviewer")
        for side, source in (
            ("original", original_source),
            ("revision", revision_source),
        ):
            if review.get(f"{side}_source") != source:
                raise ValueError(f"{side} review source differs from evaluated source")
        if not isinstance(review.get("correspondence"), list):
            raise ValueError("review requires an explicit correspondence list")
        correspondence_ids = set()
        for record in review["correspondence"]:
            row = deepcopy(_object(record, "correspondence"))
            identity = _text(row.get("correspondence_id"), "correspondence_id")
            if identity in correspondence_ids:
                raise ValueError("duplicate correspondence_id")
            correspondence_ids.add(identity)
            endpoints = []
            for side, findings in (("original", originals), ("revision", revisions)):
                endpoint = row.get(f"{side}_diagnostic_sha256")
                endpoints.append(endpoint)
                judgment = row.get(f"{side}_judgment")
                if endpoint is not None:
                    if not isinstance(endpoint, str):
                        raise ValueError(f"invalid {side} diagnostic identity")
                    if endpoint not in findings:
                        raise ValueError(f"unknown {side} diagnostic in correspondence")
                    if endpoint in used[side]:
                        raise ValueError(
                            f"repeated {side} diagnostic in correspondence"
                        )
                    used[side].add(endpoint)
                    judgment = "unreviewed" if judgment is None else judgment
                    if not isinstance(judgment, str) or judgment not in JUDGMENTS:
                        raise ValueError(f"invalid {side}_judgment")
                elif judgment is not None:
                    raise ValueError(f"{side}_judgment requires a diagnostic endpoint")
                row[f"{side}_judgment"] = judgment
            if endpoints == [None, None]:
                raise ValueError("correspondence requires at least one diagnostic")
            transition = (
                "new"
                if endpoints[0] is None
                else "removed"
                if endpoints[1] is None
                else "retained"
            )
            row["transition"] = transition
            transitions[transition] += 1
            judgments["removed_valid"] += int(
                transition == "removed" and row["original_judgment"] == "valid"
            )
            judgments["retained_valid"] += int(
                transition == "retained"
                and row["original_judgment"] == row["revision_judgment"] == "valid"
            )
            judgments["new_incorrect"] += int(
                transition == "new" and row["revision_judgment"] == "incorrect"
            )
            for field in HUMAN_FIELDS:
                answer = row.get(field)
                answer = "unreviewed" if answer is None else answer
                if answer not in HUMAN_ANSWERS:
                    raise ValueError(f"invalid human answer for {field}")
                row[field] = answer
            rows.append(row)

    human_outcomes = {}
    for field in HUMAN_FIELDS:
        counts = {
            answer: sum(row[field] == answer for row in rows)
            for answer in HUMAN_ANSWERS
        }
        answered = counts["yes"] + counts["no"]
        human_outcomes[field] = {
            "status_counts": counts,
            "rows_count": len(rows),
            "answered_count": answered,
            "yes_rate": counts["yes"] / answered if answered else None,
        }
    unmatched_original = [
        identity for identity in originals if identity not in used["original"]
    ]
    unmatched_revision = [
        identity for identity in revisions if identity not in used["revision"]
    ]
    original_warnings = sum(
        item["severity"] in {"warning", "error"} for item in originals.values()
    )
    revision_warnings = sum(
        item["severity"] in {"warning", "error"} for item in revisions.values()
    )
    return {
        "schema_version": 1,
        "source_binding": "sha256-utf8",
        "original": deepcopy(original),
        "revision": deepcopy(revision),
        "automatic": {
            "original_findings": len(originals),
            "revision_findings": len(revisions),
            "findings_delta": len(revisions) - len(originals),
            "original_warnings": original_warnings,
            "revision_warnings": revision_warnings,
            "warnings_delta": revision_warnings - original_warnings,
        },
        "reviewed": {
            "status": "unavailable"
            if review is None
            else "partial"
            if unmatched_original or unmatched_revision
            else "reviewed",
            "record": deepcopy(review),
            "rows": rows,
            "transitions": transitions if review is not None else None,
            "judgments": judgments if review is not None else None,
            "unmatched_original": unmatched_original,
            "unmatched_revision": unmatched_revision,
        },
        "human_outcomes": human_outcomes,
    }
