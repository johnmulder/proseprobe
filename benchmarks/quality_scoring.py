"""Validate reviewed annotations and separate detection from location metrics."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Set
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from proseprobe.parsers.prose import ProseBlock, iter_prose_blocks


class AnnotationError(ValueError):
    """An annotation violates its schema or review contract."""


@dataclass(frozen=True, order=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int

    def contains(self, line: int, column: int) -> bool:
        return (
            (self.line, self.column)
            <= (line, column)
            < (self.end_line, self.end_column)
        )

    def contains_span(self, other: SourceSpan) -> bool:
        return self.contains(other.line, other.column) and (
            other.end_line,
            other.end_column,
        ) <= (self.end_line, self.end_column)

    def overlaps(self, other: SourceSpan) -> bool:
        return (self.line, self.column) < (other.end_line, other.end_column) and (
            other.line,
            other.column,
        ) < (self.end_line, self.end_column)


@dataclass(frozen=True, order=True)
class ExpectedFinding:
    path: str
    rule_id: str
    line: int
    column: int
    note: str = field(default="", compare=False)
    end_line: int | None = field(default=None, compare=False)
    end_column: int | None = field(default=None, compare=False)
    identity: str = field(default="", compare=False)
    match_region: SourceSpan | None = field(default=None, compare=False)
    severity: str = field(default="", compare=False)
    context: str = field(default="", compare=False)


@dataclass(frozen=True, order=True)
class ActualFinding:
    path: str
    rule_id: str
    line: int
    column: int
    message: str = field(default="", compare=False)
    end_line: int | None = field(default=None, compare=False)
    end_column: int | None = field(default=None, compare=False)
    severity: str = field(default="warning", compare=False)
    confidence: str = field(default="medium", compare=False)
    context: str = field(default="", compare=False)


@dataclass(frozen=True, order=True)
class NegativeCase:
    path: str
    rule_id: str
    line: int
    note: str = field(compare=False)
    column: int | None = field(default=None, compare=False)
    end_line: int | None = field(default=None, compare=False)
    end_column: int | None = field(default=None, compare=False)


@dataclass(frozen=True)
class ReviewScope:
    path: str
    rules: tuple[str, ...]
    status: str = "reviewed"
    span: SourceSpan | None = None
    note: str = ""


@dataclass(frozen=True)
class Annotations:
    files: tuple[Path, ...]
    expected: tuple[ExpectedFinding, ...]
    negative_cases: tuple[NegativeCase, ...]
    scopes: tuple[ReviewScope, ...] | None = None
    source_groups: dict[str, str] = field(default_factory=dict)


@dataclass
class RuleMetrics:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    negatives_passed: int = 0
    negatives_total: int = 0


@dataclass
class LocationMetrics:
    matches: int = 0
    exact_starts: int = 0
    exact_spans: int = 0
    span_total: int = 0
    expected_spans: int = 0
    missing_actual_spans: int = 0


@dataclass(frozen=True)
class FalsePositive:
    finding: ActualFinding
    negative_note: str = ""


@dataclass(frozen=True)
class QualityScore:
    metrics: dict[str, RuleMetrics]
    false_positives: tuple[FalsePositive, ...]
    false_negatives: tuple[ExpectedFinding, ...]
    exact_start_metrics: dict[str, RuleMetrics] = field(default_factory=dict)
    locations: dict[str, LocationMetrics] = field(default_factory=dict)
    matches: tuple[tuple[ExpectedFinding, ActualFinding], ...] = ()
    unreviewed: tuple[ActualFinding, ...] = ()
    unsupported: tuple[ActualFinding, ...] = ()
    context_dependent: tuple[ActualFinding, ...] = ()
    unscored_expected: tuple[tuple[ExpectedFinding, str], ...] = ()


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise AnnotationError(f"{context} must be an object")
    return value


def _keys(
    value: dict[str, Any],
    *,
    required: Set[str],
    optional: Set[str] = frozenset(),
    context: str,
) -> None:
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing:
        raise AnnotationError(f"{context} missing key(s): {', '.join(sorted(missing))}")
    if unknown:
        raise AnnotationError(f"{context} unknown key(s): {', '.join(sorted(unknown))}")


def _positive_int(value: Any, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise AnnotationError(f"{context} must be a positive integer")
    return value


def _text(value: Any, context: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise AnnotationError(f"{context} must be a non-empty string")
    return value


def _location(
    data: dict[str, Any],
    lines: list[str],
    context: str,
    *,
    column_required: bool,
    allow_zero: bool = False,
) -> tuple[int, int | None, int | None, int | None]:
    line = _positive_int(data["line"], f"{context}.line")
    if line > len(lines):
        raise AnnotationError(f"{context}.line is outside the source file")
    column = (
        _positive_int(data["column"], f"{context}.column") if column_required else None
    )
    if column is not None and column > len(lines[line - 1]) + 1:
        raise AnnotationError(f"{context}.column is outside the source line")
    if "end_line" in data and "end_column" not in data:
        raise AnnotationError(f"{context}.end_line requires end_column")
    end_line = (
        _positive_int(data["end_line"], f"{context}.end_line")
        if "end_line" in data
        else None
    )
    end_column = (
        _positive_int(data["end_column"], f"{context}.end_column")
        if "end_column" in data
        else None
    )
    if end_column is not None:
        if column is None:
            raise AnnotationError(f"{context}.end_column requires column")
        last_line = end_line or line
        if last_line > len(lines) or end_column > len(lines[last_line - 1]) + 1:
            raise AnnotationError(f"{context}.end_column is outside the source span")
        if (last_line, end_column) < (line, column) or (
            (last_line, end_column) == (line, column) and not allow_zero
        ):
            raise AnnotationError(f"{context} must have an ordered nonempty span")
    return line, column, end_line, end_column


def _span(data: dict[str, Any], lines: list[str], context: str) -> SourceSpan:
    _keys(
        data,
        required={"line", "column", "end_column"},
        optional={"end_line"},
        context=context,
    )
    line, column, end_line, end_column = _location(
        data, lines, context, column_required=True
    )
    assert column is not None
    assert end_column is not None
    return SourceSpan(line, column, end_line or line, end_column)


def _rule_tokens(value: Any, rule_ids: set[str], context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise AnnotationError(f"{context} must be a list")
    result: set[str] = set()
    for token_value in value:
        token = _text(token_value, context).upper()
        matches = {
            rule
            for rule in rule_ids
            if rule == token or (len(token) == 1 and rule.startswith(token))
        }
        if not matches:
            raise AnnotationError(f"{context} contains unknown rule: {token}")
        result.update(matches)
    return tuple(sorted(result))


def finding_span(item: ExpectedFinding | ActualFinding) -> SourceSpan | None:
    if item.end_column is None:
        return None
    return SourceSpan(
        item.line, item.column, item.end_line or item.line, item.end_column
    )


def _status(
    path: str,
    rule_id: str,
    line: int,
    column: int,
    scopes: tuple[ReviewScope, ...] | None,
    span: SourceSpan | None = None,
) -> str:
    if scopes is None:
        return "reviewed"
    relevant = [
        scope for scope in scopes if scope.path == path and rule_id in scope.rules
    ]
    for scope in relevant:
        if scope.span is not None and scope.span.contains(line, column):
            if span is not None and not scope.span.contains_span(span):
                return "unreviewed"
            return scope.status
        if scope.span is not None and span is not None and scope.span.overlaps(span):
            return "unreviewed"
    return next(
        (scope.status for scope in relevant if scope.span is None), "unreviewed"
    )


def _negative_matches(
    negative: NegativeCase, actual: ExpectedFinding | ActualFinding
) -> bool:
    if (negative.path, negative.rule_id) != (actual.path, actual.rule_id):
        return False
    if negative.column is None:
        return negative.line == actual.line
    assert negative.end_column is not None
    return SourceSpan(
        negative.line,
        negative.column,
        negative.end_line or negative.line,
        negative.end_column,
    ).contains(actual.line, actual.column)


def _negative_conflicts(negative: NegativeCase, expected: ExpectedFinding) -> bool:
    if (negative.path, negative.rule_id) != (expected.path, expected.rule_id):
        return False
    if _negative_matches(negative, expected):
        return True
    positive_span = finding_span(expected)
    if positive_span is None or negative.column is None or negative.end_column is None:
        return False
    return SourceSpan(
        negative.line,
        negative.column,
        negative.end_line or negative.line,
        negative.end_column,
    ).overlaps(positive_span)


def load_annotations(
    manifest_path: Path, repo_root: Path, rule_ids: set[str]
) -> Annotations:
    """Load exhaustive legacy annotations or explicit sparse version-two scopes."""
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnnotationError(
            f"{manifest_path}: invalid JSON or unreadable manifest: {exc}"
        ) from exc
    root = _mapping(raw, "manifest")
    _keys(root, required={"version", "files"}, context="manifest")
    version = root["version"]
    if type(version) is not int or version not in {1, 2}:
        raise AnnotationError("manifest.version must be 1 or 2")
    files_data = _mapping(root["files"], "manifest.files")
    if not files_data:
        raise AnnotationError("manifest.files must not be empty")
    resolved_root = repo_root.resolve()
    files: list[Path] = []
    expected: list[ExpectedFinding] = []
    negative_cases: list[NegativeCase] = []
    scopes: list[ReviewScope] = []
    source_groups: dict[str, str] = {}
    expected_keys: set[tuple[str, str, int, int]] = set()
    identities: set[str] = set()
    negative_keys: set[tuple[str, str, int, int | None, int | None, int | None]] = set()
    for relative_path, file_value in sorted(files_data.items()):
        _text(relative_path, "manifest file path")
        source_path = (resolved_root / relative_path).resolve()
        if not source_path.is_relative_to(resolved_root):
            raise AnnotationError(f"{relative_path}: path escapes the repository")
        if not source_path.is_file():
            raise AnnotationError(f"{relative_path}: source file does not exist")
        entry = _mapping(file_value, relative_path)
        _keys(
            entry,
            required={"expected", "negative_cases"}
            | ({"reviewed_rules"} if version == 2 else set()),
            optional={"regions", "source_group"} if version == 2 else set(),
            context=relative_path,
        )
        if not isinstance(entry["expected"], list) or not isinstance(
            entry["negative_cases"], list
        ):
            raise AnnotationError(
                f"{relative_path}.expected and negative_cases must be lists"
            )
        source_text = source_path.read_text(encoding="utf-8")
        lines = source_text.splitlines()
        files.append(source_path)
        if version == 2:
            reviewed = _rule_tokens(
                entry["reviewed_rules"], rule_ids, f"{relative_path}.reviewed_rules"
            )
            if reviewed:
                scopes.append(ReviewScope(relative_path, reviewed))
            if "source_group" in entry:
                source_groups[relative_path] = _text(
                    entry["source_group"], f"{relative_path}.source_group"
                )
            regions = entry.get("regions", [])
            if not isinstance(regions, list):
                raise AnnotationError(f"{relative_path}.regions must be a list")
            for index, value in enumerate(regions):
                context = f"{relative_path}.regions[{index}]"
                region = _mapping(value, context)
                _keys(
                    region,
                    required={"rules", "status", "line", "column", "end_column"},
                    optional={"end_line", "note"},
                    context=context,
                )
                status = _text(region["status"], context)
                if status not in {
                    "reviewed",
                    "unreviewed",
                    "unsupported",
                    "context-dependent",
                }:
                    raise AnnotationError(f"{context}: invalid review status")
                rules = _rule_tokens(region["rules"], rule_ids, context)
                if not rules:
                    raise AnnotationError(f"{context}.rules must not be empty")
                span = _span(
                    {
                        key: region[key]
                        for key in ("line", "column", "end_line", "end_column")
                        if key in region
                    },
                    lines,
                    context,
                )
                if any(
                    scope.path == relative_path
                    and scope.span is not None
                    and set(scope.rules) & set(rules)
                    and scope.span.overlaps(span)
                    for scope in scopes
                ):
                    raise AnnotationError(f"{context}: overlapping review regions")
                scopes.append(
                    ReviewScope(
                        relative_path,
                        rules,
                        status,
                        span,
                        _text(
                            region.get("note", ""),
                            context,
                            allow_empty=status in {"reviewed", "unreviewed"},
                        ),
                    )
                )
        for index, value in enumerate(entry["expected"]):
            context = f"{relative_path}.expected[{index}]"
            data = _mapping(value, context)
            _keys(
                data,
                required={"rule_id", "line", "column"},
                optional={"note", "end_line", "end_column"}
                | ({"id", "match_region"} if version == 2 else set()),
                context=context,
            )
            rule_id = _text(data["rule_id"], context).upper()
            if rule_id not in rule_ids:
                raise AnnotationError(f"{context}.rule_id is unknown: {rule_id}")
            line, column, end_line, end_column = _location(
                data, lines, context, column_required=True, allow_zero=rule_id == "M004"
            )
            assert column is not None
            key = (relative_path, rule_id, line, column)
            if key in expected_keys:
                raise AnnotationError(f"{context} duplicates an expected location")
            expected_keys.add(key)
            identity = _text(data["id"], context) if "id" in data else ""
            if identity:
                if identity in identities:
                    raise AnnotationError(f"{context}: duplicate expected identity")
                identities.add(identity)
            match_region = None
            if "match_region" in data:
                if not identity:
                    raise AnnotationError(f"{context}.match_region requires id")
                match_region = _span(
                    _mapping(data["match_region"], context), lines, context
                )
                current_span = (
                    SourceSpan(line, column, end_line or line, end_column)
                    if end_column is not None
                    else None
                )
                if not match_region.contains(line, column) or (
                    current_span is not None
                    and not match_region.contains_span(current_span)
                ):
                    raise AnnotationError(
                        f"{context}: expected span outside match_region"
                    )
                if any(
                    item.path == relative_path
                    and item.rule_id == rule_id
                    and item.match_region is not None
                    and item.match_region.overlaps(match_region)
                    for item in expected
                ):
                    raise AnnotationError(f"{context}: ambiguous semantic regions")
            expected.append(
                ExpectedFinding(
                    relative_path,
                    rule_id,
                    line,
                    column,
                    _text(data.get("note", ""), context, allow_empty=True),
                    end_line,
                    end_column,
                    identity,
                    match_region,
                    context=prose_context(source_text, str(source_path), line, column),
                )
            )
        for index, value in enumerate(entry["negative_cases"]):
            context = f"{relative_path}.negative_cases[{index}]"
            data = _mapping(value, context)
            _keys(
                data,
                required={"rule_id", "line", "note"},
                optional={"column", "end_line", "end_column"}
                if version == 2
                else set(),
                context=context,
            )
            rule_id = _text(data["rule_id"], context).upper()
            if rule_id not in rule_ids:
                raise AnnotationError(f"{context}.rule_id is unknown: {rule_id}")
            if "column" in data and "end_column" not in data:
                raise AnnotationError(f"{context}.column requires end_column")
            line, column, end_line, end_column = _location(
                data, lines, context, column_required="column" in data
            )
            negative = NegativeCase(
                relative_path,
                rule_id,
                line,
                _text(data["note"], context),
                column,
                end_line,
                end_column,
            )
            negative_key = (relative_path, rule_id, line, column, end_line, end_column)
            if negative_key in negative_keys:
                raise AnnotationError(f"{context} duplicates a negative case")
            negative_keys.add(negative_key)
            if any(_negative_conflicts(negative, item) for item in expected):
                raise AnnotationError(f"{context} conflicts with an expected finding")
            negative_cases.append(negative)
    for target in expected:
        match_span = target.match_region
        if match_span is not None and any(
            other is not target
            and (other.path, other.rule_id) == (target.path, target.rule_id)
            and match_span.contains(other.line, other.column)
            for other in expected
        ):
            raise AnnotationError(
                "ambiguous semantic region covers another expected issue"
            )
    if version == 1:
        for label, items in (
            ("expected findings", expected),
            ("negative cases", negative_cases),
        ):
            missing = sorted(rule_ids - {item.rule_id for item in items})
            if missing:
                raise AnnotationError(f"rules missing {label}: " + ", ".join(missing))
    return Annotations(
        tuple(files),
        tuple(sorted(expected)),
        tuple(sorted(negative_cases)),
        tuple(scopes) if version == 2 else None,
        source_groups,
    )


def _start(item: ExpectedFinding | ActualFinding) -> tuple[str, str, int, int]:
    return item.path, item.rule_id, item.line, item.column


def _actual_key(
    item: ActualFinding,
) -> tuple[str, str, int, int, int, int, str, str, str, str]:
    return (
        *_start(item),
        item.end_line or item.line,
        item.end_column or item.column,
        item.message,
        item.severity,
        item.confidence,
        item.context,
    )


def _exact_span(expected: ExpectedFinding, actual: ActualFinding) -> bool:
    return expected.end_column is not None and finding_span(expected) == finding_span(
        actual
    )


def score_findings(
    expected: tuple[ExpectedFinding, ...],
    actual: tuple[ActualFinding, ...],
    negative_cases: tuple[NegativeCase, ...],
    rule_ids: set[str],
    *,
    scopes: tuple[ReviewScope, ...] | None = None,
) -> QualityScore:
    """Score one-to-one reviewed matches while keeping unreviewed material separate."""
    metrics = {rule: RuleMetrics() for rule in sorted(rule_ids)}
    strict = {rule: RuleMetrics() for rule in sorted(rule_ids)}
    locations = {rule: LocationMetrics() for rule in sorted(rule_ids)}
    unscored = tuple(
        (
            item,
            _status(
                item.path,
                item.rule_id,
                item.line,
                item.column,
                scopes,
                finding_span(item),
            ),
        )
        for item in sorted(expected)
        if _status(
            item.path, item.rule_id, item.line, item.column, scopes, finding_span(item)
        )
        != "reviewed"
    )
    eligible = tuple(
        item
        for item in sorted(expected)
        if _status(
            item.path, item.rule_id, item.line, item.column, scopes, finding_span(item)
        )
        == "reviewed"
    )
    ordered = tuple(sorted(actual, key=_actual_key))
    used: set[int] = set()
    matched: dict[tuple[str, str, int, int], tuple[ExpectedFinding, ActualFinding]] = {}
    all_items: tuple[ExpectedFinding | ActualFinding | NegativeCase, ...] = (
        *expected,
        *actual,
        *negative_cases,
    )
    for item in all_items:
        if item.rule_id not in rule_ids:
            raise AnnotationError(f"scoring unknown rule: {item.rule_id}")
    for target in eligible:
        candidates = [
            index
            for index, prediction in enumerate(ordered)
            if index not in used and _start(prediction) == _start(target)
        ]
        if candidates:
            index = min(
                candidates,
                key=lambda index: (
                    not _exact_span(target, ordered[index]),
                    _actual_key(ordered[index]),
                ),
            )
            used.add(index)
            matched[_start(target)] = (target, ordered[index])
    for target in eligible:
        if _start(target) in matched or target.match_region is None:
            continue
        for index, prediction in enumerate(ordered):
            if index in used or (prediction.path, prediction.rule_id) != (
                target.path,
                target.rule_id,
            ):
                continue
            span = finding_span(prediction)
            if (
                _status(
                    prediction.path,
                    prediction.rule_id,
                    prediction.line,
                    prediction.column,
                    scopes,
                    span,
                )
                != "reviewed"
            ):
                continue
            if target.match_region.contains(prediction.line, prediction.column) and (
                span is None or target.match_region.contains_span(span)
            ):
                used.add(index)
                matched[_start(target)] = (target, prediction)
                break
    false_negatives = tuple(item for item in eligible if _start(item) not in matched)
    for target in eligible:
        if target.end_column is not None:
            locations[target.rule_id].expected_spans += 1
        pair = matched.get(_start(target))
        if pair is None:
            metrics[target.rule_id].false_negatives += 1
            strict[target.rule_id].false_negatives += 1
            continue
        prediction = pair[1]
        metrics[target.rule_id].true_positives += 1
        location = locations[target.rule_id]
        location.matches += 1
        if _start(prediction) == _start(target):
            location.exact_starts += 1
            strict[target.rule_id].true_positives += 1
        else:
            strict[target.rule_id].false_positives += 1
            strict[target.rule_id].false_negatives += 1
        if target.end_column is not None:
            location.span_total += 1
            location.exact_spans += int(_exact_span(target, prediction))
            location.missing_actual_spans += int(prediction.end_column is None)
    false_positives: list[FalsePositive] = []
    categories: dict[str, list[ActualFinding]] = {
        "unreviewed": [],
        "unsupported": [],
        "context-dependent": [],
    }
    for index, prediction in enumerate(ordered):
        if index in used:
            continue
        negative = next(
            (item for item in negative_cases if _negative_matches(item, prediction)),
            None,
        )
        status = (
            "reviewed"
            if negative
            else _status(
                prediction.path,
                prediction.rule_id,
                prediction.line,
                prediction.column,
                scopes,
                finding_span(prediction),
            )
        )
        if status != "reviewed":
            categories[status].append(prediction)
            continue
        metrics[prediction.rule_id].false_positives += 1
        strict[prediction.rule_id].false_positives += 1
        false_positives.append(
            FalsePositive(prediction, negative.note if negative else "")
        )
    for negative in negative_cases:
        for table in (metrics, strict):
            table[negative.rule_id].negatives_total += 1
            table[negative.rule_id].negatives_passed += int(
                not any(
                    _negative_matches(negative, prediction) for prediction in ordered
                )
            )
    return QualityScore(
        metrics,
        tuple(false_positives),
        false_negatives,
        strict,
        locations,
        tuple(matched[key] for key in sorted(matched)),
        tuple(categories["unreviewed"]),
        tuple(categories["unsupported"]),
        tuple(categories["context-dependent"]),
        unscored,
    )


def wilson_interval(successes: int, total: int) -> tuple[float, float] | None:
    """Return a 95% Wilson interval under independent sample observations."""
    if not 0 <= successes <= total:
        raise ValueError("successes must be between zero and total")
    if total == 0:
        return None
    z = 1.959963984540054
    estimate = successes / total
    divisor = 1 + z * z / total
    center = (estimate + z * z / (2 * total)) / divisor
    radius = (
        z
        * math.sqrt(estimate * (1 - estimate) / total + z * z / (4 * total * total))
        / divisor
    )
    return max(0, center - radius), min(1, center + radius)


def metric_summary(
    metrics: RuleMetrics,
    *,
    prose_words: int | None = None,
    false_warnings: int | None = None,
) -> dict[str, object]:
    """Expose denominators; intervals describe this sample, not generalization."""
    precision_total = metrics.true_positives + metrics.false_positives
    recall_total = metrics.true_positives + metrics.false_negatives
    return {
        "precision": metrics.true_positives / precision_total
        if precision_total
        else None,
        "precision_denominator": precision_total,
        "recall": metrics.true_positives / recall_total if recall_total else None,
        "recall_denominator": recall_total,
        "precision_interval_95": wilson_interval(
            metrics.true_positives, precision_total
        ),
        "recall_interval_95": wilson_interval(metrics.true_positives, recall_total),
        "prose_words": prose_words,
        "false_warnings_per_1000_prose_words": false_warnings * 1000 / prose_words
        if prose_words and false_warnings is not None
        else None,
        "uncertainty_scope": "reviewed sample; independence assumed, no population or cluster inference",
    }


def total_metrics(table: dict[str, RuleMetrics]) -> RuleMetrics:
    return RuleMetrics(
        **{
            name: sum(getattr(metrics, name) for metrics in table.values())
            for name in asdict(RuleMetrics())
        }
    )


def score_breakdowns(
    score: QualityScore, annotations: Annotations, profile: str
) -> dict[str, dict[str, dict[str, object]]]:
    """Partition counts without assigning a predicted confidence to missed labels."""
    tables: dict[str, dict[str, RuleMetrics]] = {
        name: {}
        for name in (
            "severity",
            "confidence",
            "format",
            "context",
            "profile",
            "source_group",
        )
    }

    def keys(item: ExpectedFinding | ActualFinding) -> dict[str, str]:
        return {
            "severity": item.severity or "unassigned",
            "confidence": item.confidence
            if isinstance(item, ActualFinding)
            else "unassigned",
            "format": "python" if item.path.endswith(".py") else "markdown",
            "context": item.context or "unassigned",
            "profile": profile,
            "source_group": annotations.source_groups.get(item.path, "unspecified"),
        }

    def add(item: ExpectedFinding | ActualFinding, field: str) -> None:
        for dimension, key in keys(item).items():
            bucket = tables[dimension].setdefault(key, RuleMetrics())
            setattr(bucket, field, getattr(bucket, field) + 1)

    for _target, prediction in score.matches:
        add(prediction, "true_positives")
    for unexpected in score.false_positives:
        add(unexpected.finding, "false_positives")
    for missing in score.false_negatives:
        add(missing, "false_negatives")
    for value in ("high", "medium", "low", "unassigned"):
        tables["confidence"].setdefault(value, RuleMetrics())
    result: dict[str, dict[str, dict[str, object]]] = {}
    for dimension, table in tables.items():
        result[dimension] = {}
        for key, metrics in sorted(table.items()):
            summary = {
                "true_positives": metrics.true_positives,
                "false_positives": metrics.false_positives,
                "false_negatives": metrics.false_negatives,
                **metric_summary(metrics),
            }
            if dimension == "confidence":
                summary.update(
                    {
                        "recall": None,
                        "recall_denominator": None,
                        "recall_interval_95": None,
                        "recall_unavailable_reason": "missed expectations have no predicted confidence; use policy-threshold recall",
                    }
                )
            result[dimension][key] = summary
    return result


def _context_blocks(source: str, filename: str) -> list[tuple[ProseBlock, str]]:
    docstrings: set[tuple[tuple[int, str], ...]] = set()
    python = Path(filename).suffix.lower() == ".py"
    if python:
        from proseprobe.parsers.python import _get_cached_parser

        docstrings = {
            block.lines
            for block in _get_cached_parser(source).get_docstring_prose_blocks()
        }
    return [
        (
            block,
            "markdown"
            if not python
            else "docstring"
            if block.lines in docstrings
            else "comment",
        )
        for block in iter_prose_blocks(source, filename)
    ]


def prose_context(source: str, filename: str, line: int, column: int) -> str:
    """Classify a source anchor using extraction records, independently of detection."""
    if Path(filename).suffix.lower() != ".py":
        return "markdown"
    candidates = set()
    for block, context in _context_blocks(source, filename):
        for number, text in block.lines:
            if number == line:
                candidates.add(context)
                if 0 < column <= len(text) and not text[column - 1].isspace():
                    return context
    return next(iter(candidates)) if len(candidates) == 1 else "python"


def count_prose_words(
    annotations: Annotations, repo_root: Path, rule_ids: set[str]
) -> dict[str, int]:
    """Count words once in extracted prose covered by an evaluated reviewed rule."""
    totals = {"markdown": 0, "docstring": 0, "comment": 0}
    for path in annotations.files:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
        source = path.read_text(encoding="utf-8")
        for block, context in _context_blocks(source, str(path)):
            for line, text in block.lines:
                for match in re.finditer(r"\b\w+(?:['\u2019-]\w+)*\b", text):
                    span = SourceSpan(line, match.start() + 1, line, match.end() + 1)
                    if any(
                        _status(
                            relative,
                            rule,
                            line,
                            match.start() + 1,
                            annotations.scopes,
                            span,
                        )
                        == "reviewed"
                        for rule in rule_ids
                    ):
                        totals[context] += 1
    return totals
