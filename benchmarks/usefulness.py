"""Validate explicit human judgments and report them apart from rescan evidence."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from benchmarks.evaluation_identity import diagnostic_sha256
from benchmarks.quality_scoring import (
    ActualFinding,
    AnnotationError,
    Annotations,
    _keys,
    _location,
    _mapping,
    _sha256,
    _text,
)

QUESTIONS = (
    "finding_helpful",
    "suggestion_fits_sentence",
    "meaning_preserved",
    "reviewer_accepts",
)
ANSWERS = {"yes", "no", "context-dependent", "unresolved", "unreviewed"}
ISSUE_FIELDS = {
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


@dataclass(frozen=True)
class UsefulnessRating:
    identity: str
    path: str
    reviewer: str
    finding: dict[str, Any]
    diagnostic_sha256: str
    answers: dict[str, str]
    revision: dict[str, str] | None = None
    automatic_rescan: dict[str, Any] | None = None


def load_usefulness(
    value: Any,
    path: str,
    source_id: str,
    lines: list[str],
    root: Path,
    reviewers: list[str],
    rule_ids: set[str],
    pair_group: str | None,
) -> tuple[UsefulnessRating, ...]:
    """Accept ratings only for exact source-bound prompts and named review participants."""
    if not isinstance(value, list):
        raise AnnotationError(f"{path}.usefulness must be a list")
    result = []
    for index, item in enumerate(value):
        context = f"{path}.usefulness[{index}]"
        row = _mapping(item, context)
        _keys(
            row,
            required={
                "id",
                "reviewer",
                "finding",
                "diagnostic_sha256",
                "answers",
                "revision",
                "automatic_rescan",
            },
            context=context,
        )
        identity = _text(row["id"], f"{context}.id")
        reviewer = _text(row["reviewer"], f"{context}.reviewer")
        if reviewer not in reviewers:
            raise AnnotationError(
                f"{context}: reviewer is not declared by the review header"
            )
        finding = _mapping(row["finding"], f"{context}.finding")
        _keys(finding, required=ISSUE_FIELDS, context=f"{context}.finding")
        rule = _text(finding["rule_id"], f"{context}.rule_id")
        if rule not in rule_ids:
            raise AnnotationError(f"{context}: unknown rule")
        _text(finding["message"], f"{context}.message")
        if finding["severity"] not in ("info", "warning", "error") or finding[
            "confidence"
        ] not in ("low", "medium", "high"):
            raise AnnotationError(
                f"{context}: invalid diagnostic severity or confidence"
            )
        if finding["suggestion"] is not None:
            _text(finding["suggestion"], f"{context}.suggestion")
        location = {"line": finding["line"], "column": finding["column"]} | {
            key: finding[key]
            for key in ("end_line", "end_column")
            if finding[key] is not None
        }
        _location(
            location, lines, context, column_required=True, allow_zero=rule == "M004"
        )
        checksum = _sha256(row["diagnostic_sha256"], f"{context}.diagnostic_sha256")
        if diagnostic_sha256(finding) != checksum:
            raise AnnotationError(
                f"{context}: diagnostic SHA-256 differs from the rated prompt"
            )
        answers = _mapping(row["answers"], f"{context}.answers")
        _keys(
            answers,
            required=set(),
            optional=set(QUESTIONS),
            context=f"{context}.answers",
        )
        normalized = {
            question: answers.get(question, "unreviewed") for question in QUESTIONS
        }
        if any(
            not isinstance(answer, str) or answer not in ANSWERS
            for answer in normalized.values()
        ):
            raise AnnotationError(f"{context}: unknown human judgment value")
        if finding["suggestion"] is None and any(
            normalized[question] in {"yes", "no"} for question in QUESTIONS[1:]
        ):
            raise AnnotationError(
                f"{context}: absent suggestions cannot have binary suggestion judgments"
            )
        revision = None
        if row["revision"] is not None:
            if pair_group is None:
                raise AnnotationError(
                    f"{context}: revision ratings require the original packet's declared pair_group"
                )
            revision = _mapping(row["revision"], f"{context}.revision")
            _keys(
                revision,
                required={
                    "path",
                    "source_id",
                    "sha256",
                    "original_source_id",
                    "pair_group",
                },
                context=f"{context}.revision",
            )
            for key in ("path", "source_id", "original_source_id", "pair_group"):
                _text(revision[key], f"{context}.revision.{key}")
            if (
                revision["original_source_id"] != source_id
                or revision["source_id"] == source_id
                or (pair_group is not None and revision["pair_group"] != pair_group)
            ):
                raise AnnotationError(
                    f"{context}: revision origin or pair identity differs"
                )
            target = (root / revision["path"]).resolve()
            if Path(revision["path"]).is_absolute() or not target.is_relative_to(
                root.resolve()
            ):
                raise AnnotationError(f"{context}: revision escapes the corpus root")
            raw = target.read_bytes()
            if hashlib.sha256(raw).hexdigest() != _sha256(
                revision["sha256"], f"{context}.revision.sha256"
            ):
                raise AnnotationError(f"{context}: reviewed revision SHA-256 differs")
            raw.decode("utf-8")
        rescan = None
        if row["automatic_rescan"] is not None:
            if revision is None:
                raise AnnotationError(
                    f"{context}: automatic rescans require a bound revision"
                )
            rescan = _mapping(row["automatic_rescan"], f"{context}.automatic_rescan")
            _keys(
                rescan,
                required={
                    "targeted_issue_resolved",
                    "new_warning_count",
                    "policy_sha256",
                    "runtime_source_sha256",
                },
                context=f"{context}.automatic_rescan",
            )
            if (
                type(rescan["targeted_issue_resolved"]) is not bool
                or type(rescan["new_warning_count"]) is not int
                or rescan["new_warning_count"] < 0
            ):
                raise AnnotationError(
                    f"{context}: invalid automatic rescan observation"
                )
            for key in ("policy_sha256", "runtime_source_sha256"):
                _sha256(rescan[key], f"{context}.automatic_rescan.{key}")
        result.append(
            UsefulnessRating(
                identity,
                path,
                reviewer,
                finding,
                checksum,
                normalized,
                revision,
                rescan,
            )
        )
    return tuple(result)


def usefulness_report(
    annotations: Annotations, actual: tuple[ActualFinding, ...]
) -> dict[str, Any]:
    """Report current-linked human responses with explicit missing/stale coverage."""
    current = {}
    for finding in actual:
        record = {key: getattr(finding, key) for key in ISSUE_FIELDS}
        current[(finding.path, diagnostic_sha256(record))] = finding
    linked = [
        rating
        for rating in annotations.usefulness
        if (rating.path, rating.diagnostic_sha256) in current
    ]
    linked_prompts = {(rating.path, rating.diagnostic_sha256) for rating in linked}
    unreviewed = len(current) - len(linked_prompts)
    dimensions = {}
    for question in QUESTIONS:
        counts = {
            answer: sum(rating.answers[question] == answer for rating in linked)
            for answer in ANSWERS
        }
        counts["unreviewed"] += unreviewed
        denominator = counts["yes"] + counts["no"]
        dimensions[question] = {
            "yes_count": counts["yes"],
            "no_count": counts["no"],
            "context_dependent_count": counts["context-dependent"],
            "unresolved_count": counts["unresolved"],
            "unreviewed_count": counts["unreviewed"],
            "binary_denominator": denominator,
            "positive_rate": counts["yes"] / denominator if denominator else None,
        }
    rescans = [
        rating.automatic_rescan
        for rating in linked
        if rating.automatic_rescan is not None
    ]
    return {
        "emitted_findings_count": len(actual),
        "distinct_prompts_count": len(current),
        "linked_findings_count": len(linked_prompts),
        "unreviewed_findings_count": unreviewed,
        "linked_ratings_count": len(linked),
        "unlinked_ratings_count": len(annotations.usefulness) - len(linked),
        "responding_reviewers_count": len(
            {
                rating.reviewer
                for rating in linked
                if any(answer != "unreviewed" for answer in rating.answers.values())
            }
        ),
        "dimensions": dimensions,
        "automatic_rescan": {
            "evidence_kind": "recorded observations with declared policy/runtime hashes; no current run verified",
            "observations_count": len(rescans),
            "targeted_issue_resolved_count": sum(
                item["targeted_issue_resolved"] for item in rescans
            ),
            "new_warning_count": sum(item["new_warning_count"] for item in rescans),
            "semantic_usefulness_inferred": False,
        },
        "ratings": [asdict(rating) for rating in linked],
        "unavailable_reason": None
        if linked
        else "no current-linked source-bound human ratings",
    }
