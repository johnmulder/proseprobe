"""Exact reviewed mismatch gates keep raw quality measurements visible."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from benchmarks.evaluation_identity import rule_contract_snapshot, runtime_identity
from benchmarks.quality_scoring import (
    ActualFinding,
    AnnotationError,
    load_annotations,
    score_findings,
)
from benchmarks.rule_quality import prepare_evaluation_scan

from proseprobe.config import Config


def _inputs(root: Path):
    from benchmarks.regression_gate import policy_identity

    source = root / "doc.md"
    source.write_text("delve\nplain\n")
    manifest = root / "annotations.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "files": {
                    "doc.md": {
                        "expected": [
                            {"rule_id": "V001", "line": 1, "column": 1, "end_column": 6}
                        ],
                        "negative_cases": [
                            {
                                "rule_id": "V001",
                                "line": 2,
                                "note": "Legitimate fixture prose",
                            }
                        ],
                    }
                },
            }
        )
    )
    annotations = load_annotations(manifest, root, {"V001"})
    config, linter, rules = prepare_evaluation_scan(config=Config(select=["V001"]))
    record = {
        "version": 1,
        "name": "fixture-production",
        "mode": "production",
        "policy": policy_identity(config, root),
        "annotation_contract": "legacy-exhaustive-v1",
        "corpus": {
            "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "files": {"doc.md": hashlib.sha256(source.read_bytes()).hexdigest()},
        },
        "rule_contracts": rule_contract_snapshot({rule.id for rule in rules}),
        "created_runtime": runtime_identity(),
        "mismatches": [
            {
                "kind": "fp",
                "path": "doc.md",
                "rule_id": "V001",
                "line": 2,
                "column": 1,
                "end_line": 2,
                "end_column": 6,
                "label_id": "",
                "reason": "Known legitimate fixture prose",
            }
        ],
    }
    path = root / "gate.json"
    path.write_text(json.dumps(record))
    return annotations, config, linter, rules, manifest, path, record


def test_known_mismatch_record_is_validated_against_sources_policy_and_contracts(
    tmp_path: Path,
) -> None:
    from benchmarks.regression_gate import load_gate_record

    annotations, config, _linter, rules, manifest, path, record = _inputs(tmp_path)
    assert (
        load_gate_record(
            path, annotations, manifest, tmp_path, "production", config, rules
        )
        == record
    )


@pytest.mark.parametrize(
    "change",
    [
        "version",
        "duplicate",
        "span",
        "rule",
        "hash",
        "policy",
        "manifest",
        "contracts",
        "reason",
        "unknown-field",
        "kind-type",
        "rule-type",
        "path-type",
        "contract-type",
        "start-type",
        "runtime-count",
    ],
)
def test_invalid_or_stale_records_cannot_pass(tmp_path: Path, change: str) -> None:
    from benchmarks.regression_gate import load_gate_record

    annotations, config, _linter, rules, manifest, path, record = _inputs(tmp_path)
    if change == "version":
        record["version"] = 2
    elif change == "duplicate":
        record["mismatches"] *= 2
    elif change == "span":
        record["mismatches"][0]["end_column"] = 99
    elif change == "rule":
        record["mismatches"][0]["rule_id"] = "NOPE"
    elif change == "hash":
        (tmp_path / "doc.md").write_text("delve\nother\n")
    elif change == "policy":
        record["policy"]["min_confidence"] = "high"
    elif change == "manifest":
        record["corpus"]["manifest_sha256"] = "0" * 64
    elif change == "contracts":
        record["rule_contracts"]["rules"]["V001"]["description"] = (
            "Changed declared contract"
        )
    elif change == "reason":
        record["mismatches"][0]["reason"] = ""
    elif change.endswith("-type"):
        field = {
            "kind-type": "kind",
            "rule-type": "rule_id",
            "path-type": "path",
            "start-type": "line",
        }.get(change)
        if field:
            record["mismatches"][0][field] = []
        else:
            record["annotation_contract"] = []
    elif change == "runtime-count":
        record["created_runtime"]["source_files_count"] = "many"
    else:
        record["automatic_acceptance"] = True
    path.write_text(json.dumps(record))
    with pytest.raises(AnnotationError):
        load_gate_record(
            path, annotations, manifest, tmp_path, "production", config, rules
        )


def test_gate_compares_exact_mismatch_identities_without_hiding_raw_counts(
    tmp_path: Path,
) -> None:
    from benchmarks.regression_gate import compare_gate

    annotations, _config, _linter, _rules, _manifest, _path, record = _inputs(tmp_path)
    positive = ActualFinding("doc.md", "V001", 1, 1, end_column=6)
    known = ActualFinding("doc.md", "V001", 2, 1, end_column=6)
    score = score_findings(
        annotations.expected, (positive, known), annotations.negative_cases, {"V001"}
    )
    result = compare_gate(record, score)
    assert result["passed"] is True
    assert result["known_mismatches_count"] == 1
    assert score.metrics["V001"].false_positives == 1
    corrected = score_findings(
        annotations.expected, (positive,), annotations.negative_cases, {"V001"}
    )
    result = compare_gate(record, corrected)
    assert result["passed"] is True
    assert len(result["resolved_mismatches"]) == 1


@pytest.mark.parametrize(
    "regression", ["replacement-fp", "new-fn", "moved-span", "extra-identical-fp"]
)
def test_new_regressions_fail_even_when_false_positive_totals_stay_equal(
    tmp_path: Path, regression: str
) -> None:
    from benchmarks.regression_gate import compare_gate

    annotations, _config, _linter, _rules, _manifest, _path, record = _inputs(tmp_path)
    positive = ActualFinding("doc.md", "V001", 1, 1, end_column=6)
    known = ActualFinding("doc.md", "V001", 2, 1, end_column=6)
    predictions = {
        "replacement-fp": (positive, replace(known, column=2)),
        "new-fn": (known,),
        "moved-span": (positive, replace(known, end_column=5)),
        "extra-identical-fp": (positive, known, known),
    }[regression]
    score = score_findings(
        annotations.expected, predictions, annotations.negative_cases, {"V001"}
    )
    result = compare_gate(record, score)
    assert result["passed"] is False
    assert result["new_mismatches"]


@pytest.mark.parametrize("status", ["unreviewed", "unsupported", "context-dependent"])
def test_gate_refuses_unknown_coverage_without_emitted_findings(
    tmp_path: Path, status: str
) -> None:
    from benchmarks.quality_scoring import ReviewScope, SourceSpan
    from benchmarks.regression_gate import require_complete_review

    annotations, _config, linter, rules, _manifest, _path, _record = _inputs(tmp_path)
    sparse = replace(
        annotations,
        source_binding="sha256-utf8",
        scopes=(
            ReviewScope("doc.md", ("V001",)),
            ReviewScope("doc.md", ("V001",), status, SourceSpan(2, 1, 2, 6), status),
        ),
    )
    with pytest.raises(AnnotationError, match="coverage"):
        require_complete_review(sparse, tmp_path, linter, rules, "source-bound-v3")


def test_independent_legacy_sparse_labels_are_not_a_strict_gate(tmp_path: Path) -> None:
    from benchmarks.regression_gate import require_complete_review

    annotations, _config, linter, rules, _manifest, _path, _record = _inputs(tmp_path)
    with pytest.raises(AnnotationError, match="source-bound"):
        require_complete_review(
            replace(annotations, scopes=()), tmp_path, linter, rules, "source-bound-v3"
        )


def test_bound_gate_coverage_excludes_disabled_rules_and_accepts_clean_complete_prose(
    tmp_path: Path,
) -> None:
    from benchmarks.quality_scoring import ReviewScope
    from benchmarks.regression_gate import require_complete_review

    annotations, _config, linter, rules, _manifest, _path, _record = _inputs(tmp_path)
    bound = replace(
        annotations,
        source_binding="sha256-utf8",
        expected=(),
        negative_cases=(),
        scopes=(ReviewScope("doc.md", ("V001",)),),
    )
    require_complete_review(bound, tmp_path, linter, rules, "source-bound-v3")


def test_complete_explicit_region_can_supply_strict_coverage(tmp_path: Path) -> None:
    from benchmarks.quality_scoring import ReviewScope, SourceSpan
    from benchmarks.regression_gate import require_complete_review

    annotations, _config, linter, rules, _manifest, _path, _record = _inputs(tmp_path)
    bound = replace(
        annotations,
        source_binding="sha256-utf8",
        scopes=(ReviewScope("doc.md", ("V001",), span=SourceSpan(1, 1, 2, 6)),),
    )
    require_complete_review(bound, tmp_path, linter, rules, "source-bound-v3")


def test_empty_bound_source_requires_an_explicit_reviewed_scope(tmp_path: Path) -> None:
    from benchmarks.quality_scoring import ReviewScope
    from benchmarks.regression_gate import require_complete_review

    annotations, _config, linter, rules, _manifest, _path, _record = _inputs(tmp_path)
    (tmp_path / "doc.md").write_text("")
    unknown = replace(
        annotations,
        source_binding="sha256-utf8",
        scopes=(),
        expected=(),
        negative_cases=(),
    )
    with pytest.raises(AnnotationError, match="coverage"):
        require_complete_review(unknown, tmp_path, linter, rules, "source-bound-v3")
    reviewed = replace(unknown, scopes=(ReviewScope("doc.md", ("V001",)),))
    require_complete_review(reviewed, tmp_path, linter, rules, "source-bound-v3")


def test_string_project_root_policy_is_relocatable_when_inside_corpus_root(
    tmp_path: Path,
) -> None:
    from benchmarks.regression_gate import policy_identity

    a = tmp_path / "a"
    b = tmp_path / "b"
    first = Config()
    second = Config()
    first.project_root = str(a / "docs")
    second.project_root = str(b / "docs")
    assert policy_identity(first, a)["project_root"] == {"root_relative": "docs"}
    assert policy_identity(first, a) == policy_identity(second, b)


def test_gate_legacy_source_scan_consumes_immutable_ledger_verified_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from benchmarks.regression_gate import bind_gate_sources
    from benchmarks.rule_quality import collect_findings

    annotations, _config, linter, _rules, _manifest, _path, record = _inputs(tmp_path)
    bound = bind_gate_sources(annotations, record, tmp_path)
    original = Path.read_text

    def alternate(path: Path, *args: object, **kwargs: object):
        return (
            "plain\nplain\n"
            if path == tmp_path / "doc.md"
            else original(path, *args, **kwargs)
        )

    monkeypatch.setattr(Path, "read_text", alternate)
    assert [
        finding.rule_id for finding in collect_findings(bound, tmp_path, linter=linter)
    ] == ["V001"]


def test_report_only_cli_still_returns_success_with_raw_false_positive_and_negative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import benchmarks.rule_quality as evaluator

    _inputs(tmp_path)
    data = json.loads((tmp_path / "annotations.json").read_text())
    data["version"] = 2
    data["files"]["doc.md"]["reviewed_rules"] = ["V001"]
    (tmp_path / "annotations.json").write_text(json.dumps(data))
    monkeypatch.setattr(
        evaluator,
        "collect_findings",
        lambda *_args, **_kwargs: (
            ActualFinding("doc.md", "V001", 2, 1, end_column=6),
        ),
    )
    assert (
        evaluator.main(
            [
                "--manifest",
                str(tmp_path / "annotations.json"),
                "--root",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert (
        report["totals"]["false_positives"] == report["totals"]["false_negatives"] == 1
    )


def _cli_inputs(root: Path):
    from benchmarks.regression_gate import mismatch_row, policy_identity
    from benchmarks.rule_quality import collect_findings

    from proseprobe.rules import get_all_rules
    from tests.test_quality_scoring import _bound_manifest

    manifest = _bound_manifest(root)
    data = json.loads(manifest.read_text())
    ids = {rule.id for rule in get_all_rules()}
    data["files"]["doc.md"]["reviewed_rules"] = sorted(ids)
    contracts = root / "contracts.json"
    contracts.write_text(json.dumps(rule_contract_snapshot(ids)))
    data["review"]["rule_contracts"]["sha256"] = hashlib.sha256(
        contracts.read_bytes()
    ).hexdigest()
    manifest.write_text(json.dumps(data))
    annotations = load_annotations(manifest, root, ids)
    config, linter, rules = prepare_evaluation_scan(mode="production")
    actual = collect_findings(annotations, root, linter=linter)
    assert len(actual) == 1
    row = mismatch_row("fp", actual[0]) | {
        "reason": "Authored unit fixture, not a natural-text reviewer judgment"
    }
    record = {
        "version": 1,
        "name": "synthetic-cli-production",
        "mode": "production",
        "policy": policy_identity(config, root),
        "annotation_contract": "source-bound-v3",
        "corpus": {
            "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "files": {
                "doc.md": hashlib.sha256((root / "doc.md").read_bytes()).hexdigest()
            },
        },
        "rule_contracts": rule_contract_snapshot({rule.id for rule in rules}),
        "created_runtime": runtime_identity(),
        "mismatches": [row],
    }
    path = root / "gate.json"
    path.write_text(json.dumps(record))
    args = [
        "--mode",
        "production",
        "--manifest",
        str(manifest),
        "--root",
        str(root),
        "--format",
        "json",
        "--gate",
        str(path),
    ]
    return args, actual


def test_gate_cli_preserves_raw_metrics_and_returns_zero_for_exact_known_mismatches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from benchmarks.rule_quality import main

    args, _actual = _cli_inputs(tmp_path)
    assert main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["gate"]["passed"] is True
    assert report["totals"]["false_positives"] == 1
    assert len(report["false_positives"]) == 1


def test_gate_cli_returns_one_for_a_new_regression_and_keeps_raw_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import benchmarks.rule_quality as evaluator

    args, actual = _cli_inputs(tmp_path)
    monkeypatch.setattr(
        evaluator,
        "collect_findings",
        lambda *_args, **_kwargs: (replace(actual[0], column=2),),
    )
    assert evaluator.main(args) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["gate"]["passed"] is False
    assert report["totals"]["false_positives"] == 1
    assert len(report["gate"]["new_mismatches"]) == 1


@pytest.mark.parametrize("problem", ["policy", "coverage"])
def test_gate_cli_returns_two_for_invalid_policy_or_unknown_zero_finding_coverage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], problem: str
) -> None:
    from benchmarks.rule_quality import main

    args, _actual = _cli_inputs(tmp_path)
    if problem == "policy":
        args.extend(["--min-confidence", "high"])
    else:
        manifest = tmp_path / "annotations.json"
        data = json.loads(manifest.read_text())
        data["files"]["doc.md"]["reviewed_rules"] = []
        (tmp_path / "doc.md").write_text("plain cafe\n")
        digest = hashlib.sha256((tmp_path / "doc.md").read_bytes()).hexdigest()
        data["files"]["doc.md"]["sha256"] = digest
        index = tmp_path / "index.json"
        index_data = json.loads(index.read_text())
        index_data["files"]["doc.md"]["sha256"] = digest
        index.write_text(json.dumps(index_data))
        data["review"]["packet_index"]["sha256"] = hashlib.sha256(
            index.read_bytes()
        ).hexdigest()
        manifest.write_text(json.dumps(data))
        gate = tmp_path / "gate.json"
        record = json.loads(gate.read_text())
        record["corpus"]["manifest_sha256"] = hashlib.sha256(
            manifest.read_bytes()
        ).hexdigest()
        record["corpus"]["files"]["doc.md"] = digest
        gate.write_text(json.dumps(record))
    assert main(args) == 2
    assert "Rule quality error" in capsys.readouterr().err


def test_gate_text_output_prints_raw_mismatch_before_separate_gate_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from benchmarks.rule_quality import main

    args, _actual = _cli_inputs(tmp_path)
    args[args.index("json")] = "text"
    assert main(args) == 0
    output = capsys.readouterr().out
    assert "False positives:" in output
    assert "Regression gate: PASS" in output
    assert output.index("False positives:") < output.index("Regression gate: PASS")


def test_gate_cli_lost_expected_positive_is_a_new_false_negative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import benchmarks.rule_quality as evaluator

    args, _actual = _cli_inputs(tmp_path)
    manifest = tmp_path / "annotations.json"
    data = json.loads(manifest.read_text())
    data["files"]["doc.md"]["expected"] = [
        {
            "id": "expected-word",
            "rule_id": "V001",
            "line": 1,
            "column": 1,
            "end_column": 6,
        }
    ]
    manifest.write_text(json.dumps(data))
    gate = tmp_path / "gate.json"
    record = json.loads(gate.read_text())
    record["corpus"]["manifest_sha256"] = hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    record["mismatches"] = []
    gate.write_text(json.dumps(record))
    monkeypatch.setattr(evaluator, "collect_findings", lambda *_args, **_kwargs: ())
    assert evaluator.main(args) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["totals"]["false_negatives"] == 1
    assert report["gate"]["new_mismatches"][0]["kind"] == "fn"


def test_gate_refuses_an_annotation_snapshot_changed_during_scanning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import benchmarks.rule_quality as evaluator

    args, actual = _cli_inputs(tmp_path)

    def changed(*_args: object, **_kwargs: object):
        manifest = tmp_path / "annotations.json"
        manifest.write_text(manifest.read_text() + "\n")
        return actual

    monkeypatch.setattr(evaluator, "collect_findings", changed)
    assert evaluator.main(args) == 2
    assert "annotation snapshot SHA-256 differs" in capsys.readouterr().err
