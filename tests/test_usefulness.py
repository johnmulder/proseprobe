"""Source-bound human ratings remain separate from automatic rescan observations."""

import hashlib
import json
from pathlib import Path

import pytest
from benchmarks.evaluation_identity import diagnostic_sha256, rule_contract_snapshot
from benchmarks.quality_scoring import AnnotationError, load_annotations
from benchmarks.rule_quality import collect_findings, prepare_evaluation_scan

from proseprobe.core.reporter import _serialize_issue
from tests.test_quality_scoring import _bound_manifest


def _rated_manifest(root: Path, answers: dict[str, str] | None = None) -> Path:
    manifest = _bound_manifest(root)
    _config, linter, _rules = prepare_evaluation_scan(mode="production")
    [issue] = linter.check_content((root / "doc.md").read_text(), root / "doc.md")
    finding = _serialize_issue(issue)
    data = json.loads(manifest.read_text())
    data["files"]["doc.md"]["usefulness"] = [
        {
            "id": "fixture-rating",
            "reviewer": "reviewer-fixture",
            "finding": finding,
            "diagnostic_sha256": diagnostic_sha256(finding),
            "answers": answers
            if answers is not None
            else {
                "finding_helpful": "yes",
                "suggestion_fits_sentence": "yes",
                "meaning_preserved": "yes",
                "reviewer_accepts": "yes",
            },
            "revision": None,
            "automatic_rescan": None,
        }
    ]
    manifest.write_text(json.dumps(data))
    return manifest


def _declare_pair(manifest: Path, root: Path) -> None:
    index = root / "index.json"
    data = json.loads(index.read_text())
    data["context"] = {
        "doc.md": {
            "source_group": "fixture-repository",
            "pair_group": "fixture-pair",
            "split": "development",
            "format": "markdown",
        }
    }
    index.write_text(json.dumps(data))
    annotation = json.loads(manifest.read_text())
    annotation["review"]["packet_index"]["sha256"] = hashlib.sha256(
        index.read_bytes()
    ).hexdigest()
    manifest.write_text(json.dumps(annotation))


def test_trigger_only_rating_requires_a_reviewed_rule_contract(tmp_path: Path) -> None:
    manifest = _rated_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    data["files"]["doc.md"]["reviewed_rules"] = []
    contracts = tmp_path / "contracts.json"
    contracts.write_text(json.dumps(rule_contract_snapshot(set())))
    data["review"]["rule_contracts"]["sha256"] = hashlib.sha256(
        contracts.read_bytes()
    ).hexdigest()
    manifest.write_text(json.dumps(data))
    with pytest.raises(AnnotationError, match="contract snapshot"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_revision_rating_requires_original_packet_pair_identity(tmp_path: Path) -> None:
    manifest = _rated_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    (tmp_path / "revision.md").write_text("inspect café\n")
    data["files"]["doc.md"]["usefulness"][0]["revision"] = {
        "path": "revision.md",
        "source_id": "revision-fixture",
        "sha256": hashlib.sha256((tmp_path / "revision.md").read_bytes()).hexdigest(),
        "original_source_id": "fixture-1",
        "pair_group": "fixture-pair",
    }
    manifest.write_text(json.dumps(data))
    with pytest.raises(AnnotationError, match="declared pair_group"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_individual_human_questions_keep_actual_denominators_and_unknown_answers(
    tmp_path: Path,
) -> None:
    from benchmarks.usefulness import usefulness_report

    manifest = _rated_manifest(
        tmp_path,
        {
            "finding_helpful": "yes",
            "suggestion_fits_sentence": "context-dependent",
            "meaning_preserved": "unresolved",
        },
    )
    annotations = load_annotations(manifest, tmp_path, {"V001"})
    actual = collect_findings(annotations, tmp_path)
    report = usefulness_report(annotations, actual)
    assert report["linked_findings_count"] == 1
    assert report["dimensions"]["finding_helpful"]["positive_rate"] == 1
    assert report["dimensions"]["finding_helpful"]["binary_denominator"] == 1
    assert (
        report["dimensions"]["suggestion_fits_sentence"]["context_dependent_count"] == 1
    )
    assert report["dimensions"]["meaning_preserved"]["unresolved_count"] == 1
    assert report["dimensions"]["reviewer_accepts"]["positive_rate"] is None
    assert report["dimensions"]["reviewer_accepts"]["binary_denominator"] == 0


def test_missing_ratings_do_not_count_as_useful_suggestions(tmp_path: Path) -> None:
    from benchmarks.usefulness import usefulness_report

    annotations = load_annotations(_bound_manifest(tmp_path), tmp_path, {"V001"})
    report = usefulness_report(annotations, collect_findings(annotations, tmp_path))
    assert report["linked_findings_count"] == 0
    assert report["unreviewed_findings_count"] == 1
    assert all(
        row["binary_denominator"] == 0 and row["positive_rate"] is None
        for row in report["dimensions"].values()
    )


@pytest.mark.parametrize(
    "change",
    [
        "reviewer",
        "answer",
        "duplicate",
        "digest",
        "span",
        "revision-hash",
        "revision-origin",
        "rescan-without-revision",
    ],
)
def test_invalid_human_or_pair_provenance_is_rejected(
    tmp_path: Path, change: str
) -> None:
    manifest = _rated_manifest(tmp_path)
    if change in {"revision-hash", "revision-origin"}:
        _declare_pair(manifest, tmp_path)
    data = json.loads(manifest.read_text())
    row = data["files"]["doc.md"]["usefulness"][0]
    if change == "reviewer":
        row["reviewer"] = "undeclared-reviewer"
    elif change == "answer":
        row["answers"]["meaning_preserved"] = True
    elif change == "duplicate":
        data["files"]["doc.md"]["usefulness"] *= 2
    elif change == "digest":
        row["diagnostic_sha256"] = "0" * 64
    elif change == "span":
        row["finding"]["end_column"] = 999
        row["diagnostic_sha256"] = diagnostic_sha256(row["finding"])
    elif change == "rescan-without-revision":
        row["automatic_rescan"] = {
            "targeted_issue_resolved": True,
            "new_warning_count": 0,
            "policy_sha256": "1" * 64,
            "runtime_source_sha256": "2" * 64,
        }
    else:
        (tmp_path / "revision.md").write_text("inspect café\n")
        row["revision"] = {
            "path": "revision.md",
            "source_id": "revision-fixture",
            "sha256": hashlib.sha256(
                (tmp_path / "revision.md").read_bytes()
            ).hexdigest(),
            "original_source_id": "fixture-1",
            "pair_group": "fixture-pair",
        }
        if change == "revision-hash":
            row["revision"]["sha256"] = "0" * 64
        else:
            row["revision"]["original_source_id"] = "other-original"
    manifest.write_text(json.dumps(data))
    with pytest.raises(AnnotationError):
        load_annotations(manifest, tmp_path, {"V001"})


def test_renamed_duplicate_rating_cannot_inflate_response_denominators(
    tmp_path: Path,
) -> None:
    manifest = _rated_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    duplicate = dict(data["files"]["doc.md"]["usefulness"][0]) | {
        "id": "renamed-rating"
    }
    data["files"]["doc.md"]["usefulness"].append(duplicate)
    manifest.write_text(json.dumps(data))
    with pytest.raises(AnnotationError, match=r"duplicate.*reviewer"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_two_declared_reviewers_can_rate_the_same_prompt_independently(
    tmp_path: Path,
) -> None:
    from benchmarks.usefulness import usefulness_report

    manifest = _rated_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    data["review"]["reviewers"].append("second-fixture-reviewer")
    duplicate = dict(data["files"]["doc.md"]["usefulness"][0]) | {
        "id": "second-rating",
        "reviewer": "second-fixture-reviewer",
    }
    data["files"]["doc.md"]["usefulness"].append(duplicate)
    manifest.write_text(json.dumps(data))
    annotations = load_annotations(manifest, tmp_path, {"V001"})
    report = usefulness_report(annotations, collect_findings(annotations, tmp_path))
    assert report["linked_findings_count"] == 1
    assert report["dimensions"]["finding_helpful"]["binary_denominator"] == 2
    assert report["responding_reviewers_count"] == 2


def test_quality_json_reports_human_usefulness_without_changing_accuracy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from benchmarks.rule_quality import main

    manifest = _rated_manifest(tmp_path)
    assert (
        main(
            [
                "--mode",
                "production",
                "--manifest",
                str(manifest),
                "--root",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["usefulness"]["dimensions"]["finding_helpful"]["positive_rate"] == 1
    assert report["totals"]["false_positives"] == 1


def test_ratings_are_not_reused_for_a_different_current_suggestion(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from benchmarks.usefulness import usefulness_report

    annotations = load_annotations(_rated_manifest(tmp_path), tmp_path, {"V001"})
    [finding] = collect_findings(annotations, tmp_path)
    report = usefulness_report(
        annotations, (replace(finding, suggestion="different proposal"),)
    )
    assert report["linked_findings_count"] == 0
    assert report["unlinked_ratings_count"] == 1
    assert report["dimensions"]["meaning_preserved"]["positive_rate"] is None


def test_automatic_rescan_outcome_does_not_supply_a_human_meaning_judgment(
    tmp_path: Path,
) -> None:
    from benchmarks.usefulness import usefulness_report

    manifest = _rated_manifest(tmp_path, {})
    _declare_pair(manifest, tmp_path)
    data = json.loads(manifest.read_text())
    (tmp_path / "revision.md").write_text("inspect café\n")
    row = data["files"]["doc.md"]["usefulness"][0]
    row["revision"] = {
        "path": "revision.md",
        "source_id": "revision-fixture",
        "sha256": hashlib.sha256((tmp_path / "revision.md").read_bytes()).hexdigest(),
        "original_source_id": "fixture-1",
        "pair_group": "fixture-pair",
    }
    row["automatic_rescan"] = {
        "targeted_issue_resolved": True,
        "new_warning_count": 0,
        "policy_sha256": "1" * 64,
        "runtime_source_sha256": "2" * 64,
    }
    manifest.write_text(json.dumps(data))
    annotations = load_annotations(manifest, tmp_path, {"V001"})
    report = usefulness_report(annotations, collect_findings(annotations, tmp_path))
    assert report["automatic_rescan"]["observations_count"] == 1
    assert report["automatic_rescan"]["targeted_issue_resolved_count"] == 1
    assert report["dimensions"]["meaning_preserved"]["positive_rate"] is None
