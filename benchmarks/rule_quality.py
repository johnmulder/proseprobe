#!/usr/bin/env python3
"""Measure rule precision and recall on the reviewed quality corpus."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from proseprobe.config import Config
from proseprobe.core.linter import Linter
from proseprobe.rules import get_all_rules

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "quality" / "annotations.json"


class AnnotationError(ValueError):
    """Raised when quality-corpus annotations are invalid."""


@dataclass(frozen=True, order=True)
class ExpectedFinding:
    """A finding expected at an exact source location."""

    path: str
    rule_id: str
    line: int
    column: int
    note: str = field(default="", compare=False)


@dataclass(frozen=True, order=True)
class ActualFinding:
    """A finding emitted by the linter."""

    path: str
    rule_id: str
    line: int
    column: int
    message: str = field(default="", compare=False)


@dataclass(frozen=True, order=True)
class NegativeCase:
    """A source line on which a rule must not emit a finding."""

    path: str
    rule_id: str
    line: int
    note: str = field(compare=False)


@dataclass(frozen=True)
class Annotations:
    """Validated quality-corpus annotations."""

    files: tuple[Path, ...]
    expected: tuple[ExpectedFinding, ...]
    negative_cases: tuple[NegativeCase, ...]


@dataclass
class RuleMetrics:
    """Quality counts for one rule."""

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    negatives_passed: int = 0
    negatives_total: int = 0


@dataclass(frozen=True)
class FalsePositive:
    """An unexpected finding, optionally tied to an explicit negative case."""

    finding: ActualFinding
    negative_note: str = ""


@dataclass(frozen=True)
class QualityScore:
    """Per-rule metrics and mismatch details."""

    metrics: dict[str, RuleMetrics]
    false_positives: tuple[FalsePositive, ...]
    false_negatives: tuple[ExpectedFinding, ...]


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise AnnotationError(f"{context} must be an object")
    return value


def _keys(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] = frozenset(),
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
) -> tuple[int, int | None]:
    line = _positive_int(data["line"], f"{context}.line")
    if line > len(lines):
        raise AnnotationError(f"{context}.line is outside the source file")

    column: int | None = None
    if column_required:
        column = _positive_int(data["column"], f"{context}.column")
        if column > len(lines[line - 1]) + 1:
            raise AnnotationError(f"{context}.column is outside the source line")

    if "end_line" in data:
        end_line = _positive_int(data["end_line"], f"{context}.end_line")
        if end_line < line or end_line > len(lines):
            raise AnnotationError(f"{context}.end_line is outside the source span")
    if "end_column" in data:
        end_column = _positive_int(data["end_column"], f"{context}.end_column")
        end_line = data.get("end_line", line)
        if not isinstance(end_line, int) or end_column > len(lines[end_line - 1]) + 1:
            raise AnnotationError(f"{context}.end_column is outside the source span")
    return line, column


def load_annotations(
    manifest_path: Path,
    repo_root: Path,
    rule_ids: set[str],
) -> Annotations:
    """Load and validate a quality-corpus manifest."""
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AnnotationError(f"{manifest_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AnnotationError(f"{manifest_path}: invalid JSON: {exc}") from exc

    root = _mapping(raw, "manifest")
    _keys(root, required={"version", "files"}, context="manifest")
    if root["version"] != 1:
        raise AnnotationError("manifest.version must be 1")
    files_data = _mapping(root["files"], "manifest.files")
    if not files_data:
        raise AnnotationError("manifest.files must not be empty")

    resolved_root = repo_root.resolve()
    files: list[Path] = []
    expected: list[ExpectedFinding] = []
    negative_cases: list[NegativeCase] = []
    expected_keys: set[tuple[str, str, int, int]] = set()
    negative_keys: set[tuple[str, str, int]] = set()

    for relative_path, file_value in sorted(files_data.items()):
        _text(relative_path, "manifest file path")
        source_path = (resolved_root / relative_path).resolve()
        try:
            source_path.relative_to(resolved_root)
        except ValueError as exc:
            raise AnnotationError(
                f"{relative_path}: path escapes the repository"
            ) from exc
        if not source_path.is_file():
            raise AnnotationError(f"{relative_path}: source file does not exist")

        entry = _mapping(file_value, relative_path)
        _keys(
            entry,
            required={"expected", "negative_cases"},
            context=relative_path,
        )
        if not isinstance(entry["expected"], list):
            raise AnnotationError(f"{relative_path}.expected must be a list")
        if not isinstance(entry["negative_cases"], list):
            raise AnnotationError(f"{relative_path}.negative_cases must be a list")

        lines = source_path.read_text(encoding="utf-8").splitlines()
        files.append(source_path)

        for index, item in enumerate(entry["expected"]):
            context = f"{relative_path}.expected[{index}]"
            data = _mapping(item, context)
            _keys(
                data,
                required={"rule_id", "line", "column"},
                optional={"note", "end_line", "end_column"},
                context=context,
            )
            rule_id = _text(data["rule_id"], f"{context}.rule_id").upper()
            if rule_id not in rule_ids:
                raise AnnotationError(f"{context}.rule_id is unknown: {rule_id}")
            line, column = _location(data, lines, context, column_required=True)
            assert column is not None
            key = (relative_path, rule_id, line, column)
            if key in expected_keys:
                raise AnnotationError(f"{context} duplicates an expected location")
            expected_keys.add(key)
            note = _text(data.get("note", ""), f"{context}.note", allow_empty=True)
            expected.append(ExpectedFinding(relative_path, rule_id, line, column, note))

        for index, item in enumerate(entry["negative_cases"]):
            context = f"{relative_path}.negative_cases[{index}]"
            data = _mapping(item, context)
            _keys(
                data,
                required={"rule_id", "line", "note"},
                context=context,
            )
            rule_id = _text(data["rule_id"], f"{context}.rule_id").upper()
            if rule_id not in rule_ids:
                raise AnnotationError(f"{context}.rule_id is unknown: {rule_id}")
            line, _ = _location(data, lines, context, column_required=False)
            note = _text(data["note"], f"{context}.note")
            key = (relative_path, rule_id, line)
            if key in negative_keys:
                raise AnnotationError(f"{context} duplicates a negative case")
            if any(
                path == relative_path
                and expected_rule == rule_id
                and expected_line == line
                for path, expected_rule, expected_line, _ in expected_keys
            ):
                raise AnnotationError(f"{context} conflicts with an expected finding")
            negative_keys.add(key)
            negative_cases.append(NegativeCase(relative_path, rule_id, line, note))

    expected_rules = {item.rule_id for item in expected}
    negative_rules = {item.rule_id for item in negative_cases}
    missing_expected = sorted(rule_ids - expected_rules)
    missing_negative = sorted(rule_ids - negative_rules)
    if missing_expected:
        raise AnnotationError(
            "rules missing expected findings: " + ", ".join(missing_expected)
        )
    if missing_negative:
        raise AnnotationError(
            "rules missing negative cases: " + ", ".join(missing_negative)
        )

    return Annotations(
        tuple(files),
        tuple(sorted(expected)),
        tuple(sorted(negative_cases)),
    )


def score_findings(
    expected: tuple[ExpectedFinding, ...],
    actual: tuple[ActualFinding, ...],
    negative_cases: tuple[NegativeCase, ...],
    rule_ids: set[str],
) -> QualityScore:
    """Score actual findings against reviewed expectations."""
    metrics = {rule_id: RuleMetrics() for rule_id in sorted(rule_ids)}
    remaining = {
        (item.path, item.rule_id, item.line, item.column): item for item in expected
    }
    negative_by_line = {
        (item.path, item.rule_id, item.line): item for item in negative_cases
    }
    actual_negative_lines = {(item.path, item.rule_id, item.line) for item in actual}
    false_positives: list[FalsePositive] = []

    for item in sorted(actual):
        key = (item.path, item.rule_id, item.line, item.column)
        if key in remaining:
            metrics[item.rule_id].true_positives += 1
            del remaining[key]
            continue
        metrics[item.rule_id].false_positives += 1
        negative = negative_by_line.get((item.path, item.rule_id, item.line))
        false_positives.append(
            FalsePositive(item, negative.note if negative is not None else "")
        )

    false_negatives = tuple(sorted(remaining.values()))
    for item in false_negatives:
        metrics[item.rule_id].false_negatives += 1

    for item in negative_cases:
        rule_metrics = metrics[item.rule_id]
        rule_metrics.negatives_total += 1
        if (item.path, item.rule_id, item.line) not in actual_negative_lines:
            rule_metrics.negatives_passed += 1

    return QualityScore(metrics, tuple(false_positives), false_negatives)


def _percent(numerator: int, denominator: int) -> str:
    return "n/a" if denominator == 0 else f"{numerator / denominator:.1%}"


def format_report(score: QualityScore) -> str:
    """Format quality metrics and mismatch details as deterministic text."""
    lines = [
        "Rule    TP   FP   FN  Precision   Recall  Negatives",
        "-----  ---  ---  ---  ---------  -------  ---------",
    ]
    total = RuleMetrics()
    for rule_id, item in sorted(score.metrics.items()):
        precision = _percent(
            item.true_positives,
            item.true_positives + item.false_positives,
        )
        recall = _percent(
            item.true_positives,
            item.true_positives + item.false_negatives,
        )
        negatives = f"{item.negatives_passed}/{item.negatives_total}"
        lines.append(
            f"{rule_id:<5}  {item.true_positives:>3}  {item.false_positives:>3}  "
            f"{item.false_negatives:>3}  {precision:>9}  {recall:>7}  "
            f"{negatives:>9}"
        )
        total.true_positives += item.true_positives
        total.false_positives += item.false_positives
        total.false_negatives += item.false_negatives
        total.negatives_passed += item.negatives_passed
        total.negatives_total += item.negatives_total

    total_precision = _percent(
        total.true_positives,
        total.true_positives + total.false_positives,
    )
    total_recall = _percent(
        total.true_positives,
        total.true_positives + total.false_negatives,
    )
    total_negatives = f"{total.negatives_passed}/{total.negatives_total}"
    lines.extend(
        [
            "-----  ---  ---  ---  ---------  -------  ---------",
            f"TOTAL  {total.true_positives:>3}  {total.false_positives:>3}  "
            f"{total.false_negatives:>3}  {total_precision:>9}  "
            f"{total_recall:>7}  {total_negatives:>9}",
        ]
    )

    if score.false_positives:
        lines.append("\nFalse positives:")
        for mismatch in score.false_positives:
            item = mismatch.finding
            suffix = (
                f"; negative case: {mismatch.negative_note}"
                if mismatch.negative_note
                else ""
            )
            lines.append(
                f"  {item.path}:{item.line}:{item.column}: "
                f"{item.rule_id} {item.message}{suffix}"
            )
    if score.false_negatives:
        lines.append("\nFalse negatives:")
        for item in score.false_negatives:
            suffix = f"; {item.note}" if item.note else ""
            lines.append(
                f"  {item.path}:{item.line}:{item.column}: {item.rule_id}{suffix}"
            )
    return "\n".join(lines)


def collect_findings(
    annotations: Annotations, repo_root: Path
) -> tuple[ActualFinding, ...]:
    """Run all default rules against the annotated files."""
    config = Config()
    linter = Linter(config)
    for rule in get_all_rules(config):
        linter.register_rule(rule)
    results = linter.check(list(annotations.files)).issues_by_file

    findings: list[ActualFinding] = []
    resolved_root = repo_root.resolve()
    for path, issues in results.items():
        relative_path = path.resolve().relative_to(resolved_root).as_posix()
        findings.extend(
            ActualFinding(
                relative_path,
                issue.rule_id,
                issue.line,
                issue.column,
                issue.message,
            )
            for issue in issues
        )
    return tuple(sorted(findings))


def main() -> int:
    """Run the quality benchmark."""
    rules = get_all_rules(Config())
    rule_ids = {rule.id for rule in rules}
    try:
        annotations = load_annotations(DEFAULT_MANIFEST, REPO_ROOT, rule_ids)
        actual = collect_findings(annotations, REPO_ROOT)
    except (AnnotationError, OSError, UnicodeDecodeError) as exc:
        print(f"Rule quality error: {exc}", file=sys.stderr)
        return 2

    score = score_findings(
        annotations.expected,
        actual,
        annotations.negative_cases,
        rule_ids,
    )
    print(format_report(score))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
