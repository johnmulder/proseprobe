#!/usr/bin/env python3
"""Measure rule precision and recall on the reviewed quality corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

from benchmarks.evaluation_identity import runtime_identity
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
    reviewed_coverage,
    score_breakdowns,
    score_findings,
    total_metrics,
    validate_source_bindings,
    wilson_interval,
)
from benchmarks.regression_gate import (
    bind_gate_sources,
    compare_gate,
    load_gate_record,
    require_complete_review,
)
from benchmarks.usefulness import usefulness_report
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
    project_root: Path | None = None,
) -> tuple[Config, Linter, list[Rule]]:
    """Construct isolated legacy or production policy without config discovery."""
    overrides = (config is not None, profile, select, ignore, severity, min_confidence)
    mode = mode or (
        "production" if any(overrides) or project_root is not None else "all-rules"
    )
    if mode == "all-rules":
        if any(overrides):
            raise ValueError("all-rules mode cannot be combined with policy overrides")
        base = Config(markdown_anchor_style="github")
        if project_root is not None:
            base.local_links = True
            base.project_root = str(project_root.resolve())
        return prepare_scan(
            base,
            severity="info",
            min_confidence="low",
        )
    if mode != "production":
        raise ValueError(f"unknown evaluation mode: {mode}")
    base = config if config is not None else Config()
    if project_root is not None:
        base.local_links = True
        base.project_root = str(project_root.resolve())
    return prepare_scan(
        base,
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
    return replace(
        annotations,
        expected=tuple(
            replace(item, severity=rules_by_id[item.rule_id].severity.value)
            for item in annotations.expected
            if eligible(item)
        ),
        negative_cases=tuple(
            item for item in annotations.negative_cases if eligible(item)
        ),
        scopes=scopes,
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
    validate_source_bindings(annotations, repo_root)
    verified = dict(annotations.verified_sources)
    if annotations.verified_sources:
        issues_by_file = {}
        for path in linter.discover_files(list(annotations.files)):
            relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
            source_bytes = verified[relative]
            if (
                hashlib.sha256(source_bytes).hexdigest()
                != annotations.source_identities[relative]["sha256"]
            ):
                raise AnnotationError(
                    f"{relative}: cached reviewed source SHA-256 differs"
                )
            issues = linter.check_content(source_bytes.decode("utf-8"), path)
            if issues:
                issues_by_file[path] = issues
    else:
        issues_by_file = linter.check(list(annotations.files)).issues_by_file
    validate_source_bindings(annotations, repo_root)
    results = filter_by_confidence(issues_by_file, min_confidence)

    findings: list[ActualFinding] = []
    resolved_root = repo_root.resolve()
    for path, issues in results.items():
        relative_path = path.resolve().relative_to(resolved_root).as_posix()
        source = (
            verified[relative_path].decode("utf-8")
            if verified
            else path.read_text(encoding="utf-8")
        )
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
                suggestion=issue.suggestion,
            )
            for issue in issues
        )
    validate_source_bindings(annotations, repo_root)
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
    gate: dict[str, object] | None = None,
) -> str:
    """Report counts with explicit policy and reproducible corpus provenance."""
    root = repo_root.resolve()
    validate_source_bindings(annotations, repo_root)
    hashes = {
        path.resolve().relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(annotations.files)
    }
    runtime = runtime_identity()
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
    coverage = reviewed_coverage(eligible, repo_root, set(score.metrics))
    reviewed_groups = set(coverage) - {"unspecified"}
    precision_groups = {
        eligible.source_groups[item.path]
        for item in (
            *[prediction for _expected, prediction in score.matches],
            *[fp.finding for fp in score.false_positives],
        )
        if item.path in eligible.source_groups
    }
    recall_groups = {
        eligible.source_groups[item.path]
        for item in (
            *[target for target, _prediction in score.matches],
            *score.false_negatives,
        )
        if item.path in eligible.source_groups
    }
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
            "schema_version": 3,
            "version": __version__,
            "revision": runtime["git"]["head"],
            "runtime": runtime,
            "mode": mode,
            "gate": gate,
            "usefulness": usefulness_report(
                annotations,
                tuple(item for _expected, item in score.matches)
                + tuple(item.finding for item in score.false_positives)
                + score.unreviewed
                + score.unsupported
                + score.context_dependent,
            ),
            "scoring": "reviewed-semantic"
            if any(item.match_region is not None for item in eligible.expected)
            else "exact-start",
            "policy": policy,
            "local_link_context": {
                "root": config.project_root,
                "enabled": config.local_links,
                "target_binding": "unavailable"
                if config.local_links
                else "not-required",
                "reason": "native-context-not-bound" if config.local_links else None,
            },
            "corpus": {
                "manifest_sha256": hashlib.sha256(
                    manifest_path.read_bytes()
                ).hexdigest(),
                "files": hashes,
                "files_count": len(annotations.files),
                "expected_count": len(annotations.expected),
                "negative_count": len(annotations.negative_cases),
                "reviewed_source_identities": annotations.source_identities or None,
            },
            "annotation_completeness": "legacy-exhaustive"
            if annotations.scopes is None
            else "explicit-scopes",
            "source_binding": annotations.source_binding,
            "review_provenance": annotations.review_provenance or "unavailable",
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
            "reviewed_coverage": coverage,
            "metric_source_group_counts": {
                "precision": len(precision_groups),
                "recall": len(recall_groups),
                "density": len(reviewed_groups),
            },
            "cluster_interval": None,
            "cluster_interval_reason": "too few contributing precision or recall source groups; sample-only intervals"
            if len(precision_groups) < 2 or len(recall_groups) < 2
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
    parser.add_argument(
        "--project-root",
        type=Path,
        help="explicitly enable local links under this project directory",
    )
    parser.add_argument(
        "--gate",
        type=Path,
        help="check an explicitly reviewed exact-mismatch regression ledger",
    )
    parser.add_argument(
        "--require-bound",
        action="store_true",
        help="require version-three source-bound annotations",
    )
    args = parser.parse_args(argv)
    mode = args.mode or (
        "production"
        if any((args.profile, args.severity, args.min_confidence, args.project_root))
        else "all-rules"
    )
    try:
        config, linter, rules = prepare_evaluation_scan(
            mode=mode,
            profile=args.profile,
            severity=args.severity,
            min_confidence=args.min_confidence,
            project_root=args.project_root,
        )
    except ValueError as exc:
        parser.error(str(exc))
    rule_ids = {rule.id for rule in rules}
    try:
        registry_ids = {rule.id for rule in get_all_rules()}
        annotations = load_annotations(args.manifest, args.root, registry_ids)
        if args.require_bound and config.local_links:
            raise AnnotationError(
                "strict source-bound evaluation cannot enable local_links: native target paths/bytes are not bound"
            )
        if args.require_bound and annotations.source_binding != "sha256-utf8":
            raise AnnotationError(
                "strict independent evaluation requires source-bound version-three annotations"
            )
        gate_record = None
        if args.gate:
            gate_record = load_gate_record(
                args.gate, annotations, args.manifest, args.root, mode, config, rules
            )
            require_complete_review(
                annotations,
                args.root,
                linter,
                rules,
                gate_record["annotation_contract"],
            )
            annotations = bind_gate_sources(annotations, gate_record, args.root)
        eligible = eligible_annotations(annotations, args.root, linter, rules)
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
        gate_result = (
            compare_gate(gate_record, score) if gate_record is not None else None
        )
        if args.gate:
            load_gate_record(
                args.gate, annotations, args.manifest, args.root, mode, config, rules
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
                gate=gate_result,
            )
            if args.format == "json"
            else format_report(score)
        )
    except (AnnotationError, ConfigError, OSError, UnicodeDecodeError) as exc:
        print(f"Rule quality error: {exc}", file=sys.stderr)
        return 2
    if args.format == "text":
        if config.local_links:
            print(
                f"Local link context: {config.project_root}; target binding: unavailable (native-context-not-bound)"
            )
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
    if args.format == "text" and gate_result is not None:
        print(
            f"\nRegression gate: {'PASS' if gate_result['passed'] else 'FAIL'}; exact known mismatches: {gate_result['known_mismatches_count']}; resolved: {len(gate_result['resolved_mismatches'])}"
        )
        for mismatch in gate_result["new_mismatches"]:
            print(
                f"  New {mismatch['kind'].upper()}: {mismatch['path']}:{mismatch['line']}:{mismatch['column']} {mismatch['rule_id']}"
            )
    return 0 if gate_result is None or gate_result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
