#!/usr/bin/env python3
"""Measure rule precision and recall on the reviewed quality corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

from benchmarks.quality_scoring import (
    ActualFinding,
    AnnotationError,
    Annotations,
    ExpectedFinding,
    NegativeCase,
    QualityScore,
    ReviewScope,
    RuleMetrics,
    SourceSpan,
    count_prose_words,
    load_annotations,
    metric_summary,
    prose_context,
    score_breakdowns,
    score_findings,
    total_metrics,
    wilson_interval,
)
from proseprobe import __version__
from proseprobe.config import Config, ConfigError
from proseprobe.core.linter import Linter
from proseprobe.core.policy import filter_by_confidence, prepare_scan
from proseprobe.profiles import PROFILES
from proseprobe.rules import get_all_rules
from proseprobe.rules.base import Rule

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "quality" / "annotations.json"
__all__ = [
    "ActualFinding",
    "AnnotationError",
    "Annotations",
    "ExpectedFinding",
    "NegativeCase",
    "QualityScore",
    "ReviewScope",
    "RuleMetrics",
    "SourceSpan",
    "collect_findings",
    "count_prose_words",
    "eligible_annotations",
    "format_json_report",
    "format_report",
    "load_annotations",
    "main",
    "metric_summary",
    "prepare_evaluation_scan",
    "score_findings",
    "wilson_interval",
]


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
            finding = mismatch.finding
            suffix = (
                f"; negative case: {mismatch.negative_note}"
                if mismatch.negative_note
                else ""
            )
            lines.append(
                f"  {finding.path}:{finding.line}:{finding.column}: "
                f"{finding.rule_id} {finding.message}{suffix}"
            )
    if score.false_negatives:
        lines.append("\nFalse negatives:")
        for missing in score.false_negatives:
            suffix = f"; {missing.note}" if missing.note else ""
            lines.append(
                f"  {missing.path}:{missing.line}:{missing.column}: {missing.rule_id}{suffix}"
            )
    return "\n".join(lines)


def prepare_evaluation_scan(
    *,
    mode: str | None = None,
    config: Config | None = None,
    profile: str | None = None,
    select: str | None = None,
    ignore: str | None = None,
    severity: str | None = None,
    min_confidence: str | None = None,
) -> tuple[Config, Linter, list[Rule]]:
    """Construct isolated legacy or production policy without config discovery."""
    overrides = (config is not None, profile, select, ignore, severity, min_confidence)
    mode = mode or ("production" if any(overrides) else "all-rules")
    if mode == "all-rules":
        if any(overrides):
            raise ValueError("all-rules mode cannot be combined with policy overrides")
        return prepare_scan(
            Config(markdown_anchor_style="github"),
            severity="info",
            min_confidence="low",
        )
    if mode != "production":
        raise ValueError(f"unknown evaluation mode: {mode}")
    return prepare_scan(
        config if config is not None else Config(),
        profile=profile,
        select=select,
        ignore=ignore,
        severity=severity,
        min_confidence=min_confidence,
    )


def eligible_annotations(
    annotations: Annotations,
    repo_root: Path,
    linter: Linter,
    rules: list[Rule],
) -> Annotations:
    """Keep labels enabled by rule, severity, and file policy before confidence."""
    rules_by_id = {rule.id: rule for rule in rules}

    def eligible(item: ExpectedFinding | NegativeCase) -> bool:
        rule = rules_by_id.get(item.rule_id)
        return rule is not None and linter._rule_enabled(rule, repo_root / item.path)

    scopes = annotations.scopes
    if scopes is None:
        scopes = tuple(
            ReviewScope(
                path.resolve().relative_to(repo_root.resolve()).as_posix(),
                tuple(rule.id for rule in rules if linter._rule_enabled(rule, path)),
            )
            for path in annotations.files
        )
    else:
        scopes = tuple(
            replace(
                scope,
                rules=tuple(
                    rule_id
                    for rule_id in scope.rules
                    if rule_id in rules_by_id
                    and linter._rule_enabled(
                        rules_by_id[rule_id], repo_root / scope.path
                    )
                ),
            )
            for scope in scopes
        )
    return Annotations(
        annotations.files,
        tuple(
            replace(item, severity=rules_by_id[item.rule_id].severity.value)
            for item in annotations.expected
            if eligible(item)
        ),
        tuple(item for item in annotations.negative_cases if eligible(item)),
        scopes,
        annotations.source_groups,
    )


def collect_findings(
    annotations: Annotations,
    repo_root: Path,
    *,
    linter: Linter | None = None,
    min_confidence: str = "low",
) -> tuple[ActualFinding, ...]:
    """Collect findings under explicit policy or the legacy all-rules default."""
    if linter is None:
        _config, linter, _rules = prepare_evaluation_scan()
    raw = linter.check(list(annotations.files))
    results = filter_by_confidence(raw.issues_by_file, min_confidence)

    findings: list[ActualFinding] = []
    resolved_root = repo_root.resolve()
    for path, issues in results.items():
        relative_path = path.resolve().relative_to(resolved_root).as_posix()
        source = path.read_text(encoding="utf-8")
        findings.extend(
            ActualFinding(
                relative_path,
                issue.rule_id,
                issue.line,
                issue.column,
                issue.message,
                end_line=issue.end_line,
                end_column=issue.end_column,
                severity=issue.severity.value,
                confidence=issue.confidence.value,
                context=prose_context(source, str(path), issue.line, issue.column),
            )
            for issue in issues
        )
    return tuple(sorted(findings))


def format_json_report(
    score: QualityScore,
    *,
    mode: str,
    config: Config,
    annotations: Annotations,
    eligible: Annotations,
    manifest_path: Path,
    repo_root: Path,
) -> str:
    """Report counts with explicit policy and reproducible corpus provenance."""
    root = repo_root.resolve()
    hashes = {
        path.resolve().relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(annotations.files)
    }
    try:
        revision = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],  # noqa: S607 - installed Git
            capture_output=True,
            text=True,
            check=False,
        )
        commit = revision.stdout.strip() if revision.returncode == 0 else None
    except OSError:
        commit = None
    policy = asdict(config)
    policy["source_path"] = str(config.source_path) if config.source_path else None
    totals = {
        name: sum(getattr(metrics, name) for metrics in score.metrics.values())
        for name in asdict(RuleMetrics())
    }
    words = count_prose_words(eligible, repo_root, set(score.metrics))
    false_warnings = sum(
        item.finding.severity in {"warning", "error"} for item in score.false_positives
    )
    groups = set(annotations.source_groups.values())
    breakdowns = score_breakdowns(score, eligible, config.profile or "default")
    reviewed_groups = set(breakdowns["source_group"]) - {"unspecified"}
    span_total = sum(item.span_total for item in score.locations.values())
    exact_spans = sum(item.exact_spans for item in score.locations.values())
    metric_rows = {
        rule: metric_summary(metrics) for rule, metrics in score.metrics.items()
    }
    precision_values = [
        metrics.true_positives / (metrics.true_positives + metrics.false_positives)
        for metrics in score.metrics.values()
        if metrics.true_positives + metrics.false_positives
    ]
    recall_values = [
        metrics.true_positives / (metrics.true_positives + metrics.false_negatives)
        for metrics in score.metrics.values()
        if metrics.true_positives + metrics.false_negatives
    ]
    return json.dumps(
        {
            "schema_version": 2,
            "version": __version__,
            "revision": commit,
            "mode": mode,
            "scoring": "reviewed-semantic"
            if any(item.match_region is not None for item in eligible.expected)
            else "exact-start",
            "policy": policy,
            "corpus": {
                "manifest_sha256": hashlib.sha256(
                    manifest_path.read_bytes()
                ).hexdigest(),
                "files": hashes,
                "files_count": len(annotations.files),
                "expected_count": len(annotations.expected),
                "negative_count": len(annotations.negative_cases),
            },
            "annotation_completeness": "legacy-exhaustive"
            if annotations.scopes is None
            else "explicit-scopes",
            "annotation_scopes": [asdict(scope) for scope in annotations.scopes]
            if annotations.scopes is not None
            else None,
            "excluded_expected": len(annotations.expected) - len(eligible.expected),
            "excluded_negatives": len(annotations.negative_cases)
            - len(eligible.negative_cases),
            "rules": {
                rule_id: asdict(metrics)
                for rule_id, metrics in sorted(score.metrics.items())
            },
            "totals": totals,
            "metrics": metric_summary(
                total_metrics(score.metrics),
                prose_words=sum(words.values()),
                false_warnings=false_warnings,
            ),
            "rule_metrics": metric_rows,
            "macro_precision": sum(precision_values) / len(precision_values)
            if precision_values
            else None,
            "precision_rules_count": len(precision_values),
            "macro_recall": sum(recall_values) / len(recall_values)
            if recall_values
            else None,
            "recall_rules_count": len(recall_values),
            "exact_start_totals": asdict(total_metrics(score.exact_start_metrics)),
            "exact_start_rules": {
                rule: asdict(metrics)
                for rule, metrics in score.exact_start_metrics.items()
            },
            "locations": {
                rule: asdict(metrics) for rule, metrics in score.locations.items()
            },
            "span_accuracy": exact_spans / span_total if span_total else None,
            "span_accuracy_denominator": span_total,
            "prose_words_by_context": words,
            "breakdowns": breakdowns,
            "source_group_count": len(groups),
            "reviewed_source_group_count": len(reviewed_groups),
            "cluster_interval": None,
            "cluster_interval_reason": "too few identified source groups; sample-only intervals"
            if len(reviewed_groups) < 2
            else "source-level counts provided; no cluster interval or generalization claim calculated",
            "unreviewed_count": len(score.unreviewed),
            "unsupported_count": len(score.unsupported),
            "context_dependent_count": len(score.context_dependent),
            "unreviewed": [asdict(item) for item in score.unreviewed],
            "unsupported": [asdict(item) for item in score.unsupported],
            "context_dependent": [asdict(item) for item in score.context_dependent],
            "matches": [
                {"expected": asdict(target), "actual": asdict(prediction)}
                for target, prediction in score.matches
            ],
            "unscored_expected": [
                {"finding": asdict(item), "reason": reason}
                for item, reason in score.unscored_expected
            ],
            "false_positives": [asdict(item) for item in score.false_positives],
            "false_negatives": [asdict(item) for item in score.false_negatives],
        },
        sort_keys=True,
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    """Run legacy all-rules or isolated production-policy evaluation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("all-rules", "production"))
    parser.add_argument("--profile", choices=sorted(PROFILES))
    parser.add_argument("--severity", choices=("info", "warning", "error"))
    parser.add_argument("--min-confidence", choices=("low", "medium", "high"))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    mode = args.mode or (
        "production"
        if any((args.profile, args.severity, args.min_confidence))
        else "all-rules"
    )
    try:
        config, linter, rules = prepare_evaluation_scan(
            mode=mode,
            profile=args.profile,
            severity=args.severity,
            min_confidence=args.min_confidence,
        )
    except ValueError as exc:
        parser.error(str(exc))
    rule_ids = {rule.id for rule in rules}
    try:
        registry_ids = {rule.id for rule in get_all_rules()}
        annotations = load_annotations(args.manifest, args.root, registry_ids)
        eligible = (
            eligible_annotations(annotations, args.root, linter, rules)
            if mode == "production"
            else annotations
        )
        actual = collect_findings(
            annotations, args.root, linter=linter, min_confidence=config.min_confidence
        )
        if mode == "all-rules":
            by_id = {rule.id: rule for rule in rules}
            eligible = replace(
                eligible,
                expected=tuple(
                    replace(item, severity=by_id[item.rule_id].severity.value)
                    for item in eligible.expected
                ),
            )
        score = score_findings(
            eligible.expected,
            actual,
            eligible.negative_cases,
            rule_ids,
            scopes=eligible.scopes,
        )
        output = (
            format_json_report(
                score,
                mode=mode,
                config=config,
                annotations=annotations,
                eligible=eligible,
                manifest_path=args.manifest,
                repo_root=args.root,
            )
            if args.format == "json"
            else format_report(score)
        )
    except (AnnotationError, ConfigError, OSError, UnicodeDecodeError) as exc:
        print(f"Rule quality error: {exc}", file=sys.stderr)
        return 2
    if args.format == "text":
        print(
            f"Mode: {mode}; severity: {config.severity}; minimum confidence: {config.min_confidence}"
        )
        print(
            f"Unscored findings: {len(score.unreviewed)} unreviewed, {len(score.unsupported)} unsupported, {len(score.context_dependent)} context-dependent; unscored expected labels: {len(score.unscored_expected)}"
        )
        print(
            f"Policy exclusions: {len(annotations.expected) - len(eligible.expected)} expected, {len(annotations.negative_cases) - len(eligible.negative_cases)} negatives"
        )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
