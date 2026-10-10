"""Deterministic authored toys for the paired warning report contract."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from benchmarks.evaluation_identity import diagnostic_sha256
from benchmarks.paired_quality import paired_report

from proseprobe.config import Config
from proseprobe.core.policy import prepare_scan
from tests.test_cli import run_cli

ORIGINAL = b"Notable ideas need context.\n"
REVISION = b"Specific ideas need context.\n"


def finding(**changes: Any) -> dict[str, Any]:
    record = {
        "rule_id": "V001",
        "message": "Toy vocabulary warning",
        "line": 1,
        "column": 1,
        "end_line": 1,
        "end_column": 8,
        "severity": "warning",
        "confidence": "medium",
        "suggestion": "Use a specific description",
    }
    record.update(changes)
    return record


def evaluation(raw: bytes, role: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    source = {
        "source_id": f"toy:one:{role}",
        "path": f"{role}.md",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "source_group": "authored-toy-group",
        "pair_group": "toy:one",
    }
    if role != "original":
        source["original_source_id"] = "toy:one:original"
    return {
        "source_binding": "sha256-utf8",
        "source": source,
        "findings": findings,
        "policy": {"select": ["V001"], "min_confidence": "medium"},
        "runtime": {
            "package_version": "toy-version",
            "source_sha256": "a" * 64,
            "source_roots": {"package": "/toy/first-checkout"},
            "git": {"head": "toy-revision"},
        },
        "provenance": {"kind": "authored deterministic toy"},
    }


def review(
    original: dict[str, Any], revision: dict[str, Any], **row: Any
) -> dict[str, Any]:
    return {
        "review_id": "authored-toy-review",
        "reviewer": "authored-toy-reviewer",
        "original_source": deepcopy(original["source"]),
        "revision_source": deepcopy(revision["source"]),
        "correspondence": [{"correspondence_id": "toy-change", **row}],
        "provenance": {"kind": "toy judgments; no real reviewer evidence"},
    }


def test_resolved_useful_finding_reports_explicit_human_answers() -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=diagnostic_sha256(finding()),
        revision_diagnostic_sha256=None,
        original_judgment="valid",
        finding_helpful="yes",
        suggestion_fits_sentence="yes",
        meaning_preserved="yes",
        reviewer_accepts="yes",
    )
    report = paired_report(original, revision, ORIGINAL, REVISION, reviewed)
    assert report["automatic"] == {
        "original_findings": 1,
        "revision_findings": 0,
        "findings_delta": -1,
        "original_warnings": 1,
        "revision_warnings": 0,
        "warnings_delta": -1,
    }
    assert report["reviewed"]["transitions"] == {
        "removed": 1,
        "retained": 0,
        "new": 0,
    }
    assert report["reviewed"]["judgments"]["removed_valid"] == 1
    assert report["reviewed"]["rows"][0]["meaning_preserved"] == "yes"
    assert report["human_outcomes"]["meaning_preserved"]["yes_rate"] == 1
    assert "semantic_success" not in report


def test_retained_legitimate_warning_uses_reviewed_correspondence() -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision_finding = finding(end_column=9)
    revision = evaluation(REVISION, "revision", [revision_finding])
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=diagnostic_sha256(finding()),
        revision_diagnostic_sha256=diagnostic_sha256(revision_finding),
        original_judgment="valid",
        revision_judgment="valid",
        finding_helpful="yes",
        reviewer_accepts="no",
    )
    report = paired_report(original, revision, ORIGINAL, REVISION, reviewed)
    assert report["automatic"]["warnings_delta"] == 0
    assert report["reviewed"]["transitions"]["retained"] == 1
    assert report["reviewed"]["judgments"]["retained_valid"] == 1
    assert report["human_outcomes"]["reviewer_accepts"]["yes_rate"] == 0


def test_new_incorrect_warning_requires_explicit_incorrect_judgment() -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [finding(end_column=9)])
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=None,
        revision_diagnostic_sha256=diagnostic_sha256(finding(end_column=9)),
        revision_judgment="incorrect",
        finding_helpful="no",
        meaning_preserved="yes",
    )
    report = paired_report(original, revision, ORIGINAL, REVISION, reviewed)
    assert report["automatic"]["warnings_delta"] == 1
    assert report["reviewed"]["judgments"]["new_incorrect"] == 1
    assert report["human_outcomes"]["finding_helpful"]["yes_rate"] == 0


def test_unavailable_correspondence_does_not_infer_resolution_or_quality() -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(REVISION, "revision", [])
    revision["native_edit_labels"] = ["simplification", "grammatical correction"]
    report = paired_report(original, revision, ORIGINAL, REVISION)
    assert report["automatic"]["warnings_delta"] == -1
    assert report["reviewed"]["status"] == "unavailable"
    assert report["reviewed"]["transitions"] is None
    assert report["reviewed"]["unmatched_original"] == [diagnostic_sha256(finding())]
    assert report["human_outcomes"]["meaning_preserved"]["yes_rate"] is None
    assert report["revision"]["native_edit_labels"] == revision["native_edit_labels"]


@pytest.mark.parametrize(
    "answer", [None, "context-dependent", "unresolved", "unreviewed"]
)
def test_missing_or_dependent_meaning_judgment_is_unavailable(
    answer: str | None,
) -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(REVISION, "revision", [])
    row = {
        "original_diagnostic_sha256": diagnostic_sha256(finding()),
        "revision_diagnostic_sha256": None,
        "original_judgment": "valid",
        "finding_helpful": "yes",
    }
    if answer is not None:
        row["meaning_preserved"] = answer
    report = paired_report(
        original, revision, ORIGINAL, REVISION, review(original, revision, **row)
    )
    meaning = report["human_outcomes"]["meaning_preserved"]
    assert meaning["yes_rate"] is None
    assert meaning["answered_count"] == 0
    assert meaning["status_counts"][answer or "unreviewed"] == 1
    assert report["human_outcomes"]["finding_helpful"]["yes_rate"] == 1


def test_identical_diagnostics_without_correspondence_are_not_aligned() -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(ORIGINAL, "revision", [finding()])
    reviewed = review(original, revision)
    reviewed["correspondence"] = []
    report = paired_report(original, revision, ORIGINAL, ORIGINAL, reviewed)
    assert report["reviewed"]["transitions"]["retained"] == 0
    assert report["reviewed"]["unmatched_original"] == [diagnostic_sha256(finding())]
    assert report["reviewed"]["unmatched_revision"] == [diagnostic_sha256(finding())]


def test_policy_runtime_and_all_provenance_are_retained_without_mutation() -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    revision["runtime"]["source_roots"] = {"package": "/toy/second-checkout"}
    revision["runtime"]["git"] = {"head": "different-git-only-revision"}
    before = deepcopy((original, revision))
    report = paired_report(original, revision, ORIGINAL, REVISION)
    assert report["original"] == original
    assert report["revision"] == revision
    assert (original, revision) == before
    report["original"]["policy"]["select"].append("V002")
    assert original["policy"]["select"] == ["V001"]


@pytest.mark.parametrize("side", ["original", "revision"])
def test_exact_changed_source_bytes_are_rejected(side: str) -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    with pytest.raises(ValueError, match="source bytes"):
        paired_report(
            original,
            revision,
            ORIGINAL + b"\r" if side == "original" else ORIGINAL,
            REVISION + b"\r" if side == "revision" else REVISION,
        )


@pytest.mark.parametrize("field", ["pair_group", "source_group", "original_source_id"])
def test_cross_pair_or_group_evaluation_is_rejected(field: str) -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    revision["source"][field] = "another-source"
    with pytest.raises(ValueError, match=field):
        paired_report(original, revision, ORIGINAL, REVISION)


@pytest.mark.parametrize("side", ["original_source", "revision_source"])
@pytest.mark.parametrize(
    "field", ["source_id", "sha256", "path", "pair_group", "source_group"]
)
def test_stale_review_source_identity_is_rejected(side: str, field: str) -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(original, revision)
    reviewed["correspondence"] = []
    reviewed[side][field] = "stale-source"
    with pytest.raises(ValueError, match="review source"):
        paired_report(original, revision, ORIGINAL, REVISION, reviewed)


@pytest.mark.parametrize("field", ["package_version", "source_sha256"])
def test_different_actual_runtime_identity_is_rejected(field: str) -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    revision["runtime"][field] = "b" * 64
    with pytest.raises(ValueError, match="runtime"):
        paired_report(original, revision, ORIGINAL, REVISION)


def test_different_effective_policy_is_rejected() -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    revision["policy"]["min_confidence"] = "low"
    with pytest.raises(ValueError, match="policy"):
        paired_report(original, revision, ORIGINAL, REVISION)


@pytest.mark.parametrize("reviewer", [None, "", " "])
def test_correspondence_requires_explicit_reviewer_identity(
    reviewer: str | None,
) -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(original, revision)
    reviewed["correspondence"] = []
    reviewed["reviewer"] = reviewer
    with pytest.raises(ValueError, match="reviewer"):
        paired_report(original, revision, ORIGINAL, REVISION, reviewed)


@pytest.mark.parametrize("side", ["original", "revision"])
def test_duplicate_diagnostic_identity_is_rejected(side: str) -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(REVISION, "revision", [finding()])
    (original if side == "original" else revision)["findings"].append(finding())
    with pytest.raises(ValueError, match="duplicate diagnostic"):
        paired_report(original, revision, ORIGINAL, REVISION)


def test_stale_full_diagnostic_record_cannot_match_by_location() -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=diagnostic_sha256(finding(suggestion="Old advice")),
        revision_diagnostic_sha256=None,
    )
    with pytest.raises(ValueError, match="unknown original diagnostic"):
        paired_report(original, revision, ORIGINAL, REVISION, reviewed)


def test_repeated_correspondence_endpoint_is_rejected() -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=diagnostic_sha256(finding()),
        revision_diagnostic_sha256=None,
    )
    repeated = deepcopy(reviewed["correspondence"][0])
    repeated["correspondence_id"] = "another-toy-change"
    reviewed["correspondence"].append(repeated)
    with pytest.raises(ValueError, match="repeated original diagnostic"):
        paired_report(original, revision, ORIGINAL, REVISION, reviewed)


def test_native_edit_label_is_not_a_human_outcome() -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=diagnostic_sha256(finding()),
        revision_diagnostic_sha256=None,
        meaning_preserved="simplification",
    )
    with pytest.raises(ValueError, match="meaning_preserved"):
        paired_report(original, revision, ORIGINAL, REVISION, reviewed)


def test_info_findings_are_separate_from_warning_changes() -> None:
    original = evaluation(ORIGINAL, "original", [finding(severity="info")])
    revision = evaluation(REVISION, "revision", [])
    report = paired_report(original, revision, ORIGINAL, REVISION)
    assert report["automatic"]["findings_delta"] == -1
    assert report["automatic"]["warnings_delta"] == 0


@pytest.mark.parametrize("side", ["original", "revision"])
def test_legacy_unbound_evaluation_is_rejected(side: str) -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    (original if side == "original" else revision)["source_binding"] = "legacy-unbound"
    with pytest.raises(ValueError, match="source binding"):
        paired_report(original, revision, ORIGINAL, REVISION)


def test_invalid_utf8_bytes_do_not_claim_utf8_source_binding() -> None:
    original = evaluation(b"\xff", "original", [])
    revision = evaluation(REVISION, "revision", [])
    with pytest.raises(ValueError, match="UTF-8"):
        paired_report(original, revision, b"\xff", REVISION)


@pytest.mark.parametrize("field", ["source_id", "path", "source_group", "pair_group"])
def test_missing_source_identity_is_rejected(field: str) -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    del original["source"][field]
    with pytest.raises(ValueError, match=field):
        paired_report(original, revision, ORIGINAL, REVISION)


def test_reusing_original_source_identity_for_revision_is_rejected() -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    revision["source"]["source_id"] = original["source"]["source_id"]
    with pytest.raises(ValueError, match="distinct source_id"):
        paired_report(original, revision, ORIGINAL, REVISION)


@pytest.mark.parametrize(
    "changes",
    [
        {"line": 0},
        {"column": 100},
        {"end_line": 2},
        {"end_column": None},
        {"line": 1, "column": 9, "end_column": 8},
        {"end_line": None, "end_column": 100},
        {"column": 9, "end_line": None, "end_column": 8},
        {"severity": "success"},
        {"confidence": "certain"},
        {"suggestion": True},
    ],
)
def test_invalid_full_diagnostic_records_are_rejected(changes: dict[str, Any]) -> None:
    original = evaluation(ORIGINAL, "original", [finding(**changes)])
    revision = evaluation(REVISION, "revision", [])
    with pytest.raises(ValueError, match="finding"):
        paired_report(original, revision, ORIGINAL, REVISION)


def test_missing_diagnostic_field_is_rejected() -> None:
    incomplete = finding()
    del incomplete["suggestion"]
    original = evaluation(ORIGINAL, "original", [incomplete])
    revision = evaluation(REVISION, "revision", [])
    with pytest.raises(ValueError, match="complete Issue-shaped"):
        paired_report(original, revision, ORIGINAL, REVISION)


def test_summary_finding_without_end_coordinates_is_supported() -> None:
    original = evaluation(
        ORIGINAL, "original", [finding(end_line=None, end_column=None)]
    )
    revision = evaluation(REVISION, "revision", [])
    assert (
        paired_report(original, revision, ORIGINAL, REVISION)["automatic"][
            "original_findings"
        ]
        == 1
    )


def test_runtime_identity_requires_a_real_digest_shape() -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    original["runtime"]["source_sha256"] = "unavailable"
    revision["runtime"]["source_sha256"] = "unavailable"
    with pytest.raises(ValueError, match="SHA-256 digest"):
        paired_report(original, revision, ORIGINAL, REVISION)


def test_correspondence_cannot_judge_an_absent_endpoint() -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=diagnostic_sha256(finding()),
        revision_diagnostic_sha256=None,
        revision_judgment="valid",
    )
    with pytest.raises(ValueError, match="requires a diagnostic endpoint"):
        paired_report(original, revision, ORIGINAL, REVISION, reviewed)


def test_correspondence_cannot_have_no_diagnostic_endpoints() -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    with pytest.raises(ValueError, match="at least one diagnostic"):
        paired_report(
            original, revision, ORIGINAL, REVISION, review(original, revision)
        )


@pytest.mark.parametrize("answer", ["", False, "simpler"])
def test_explicit_invalid_human_answers_do_not_become_unreviewed(answer: Any) -> None:
    original = evaluation(ORIGINAL, "original", [finding()])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=diagnostic_sha256(finding()),
        revision_diagnostic_sha256=None,
        meaning_preserved=answer,
    )
    with pytest.raises(ValueError, match="meaning_preserved"):
        paired_report(original, revision, ORIGINAL, REVISION, reviewed)


@pytest.mark.parametrize("field", ["source", "runtime", "findings"])
def test_missing_evaluation_record_is_a_contract_error(field: str) -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    del original[field]
    with pytest.raises(ValueError, match=field):
        paired_report(original, revision, ORIGINAL, REVISION)


def test_malformed_correspondence_record_is_a_contract_error() -> None:
    original = evaluation(ORIGINAL, "original", [])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(original, revision)
    reviewed["correspondence"] = [None]
    with pytest.raises(ValueError, match="correspondence"):
        paired_report(original, revision, ORIGINAL, REVISION, reviewed)


def test_duplicate_correspondence_identity_is_rejected() -> None:
    first = finding()
    second = finding(column=9, end_column=14, message="Second toy warning")
    original = evaluation(ORIGINAL, "original", [first, second])
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=diagnostic_sha256(first),
        revision_diagnostic_sha256=None,
    )
    duplicate = deepcopy(reviewed["correspondence"][0])
    duplicate["original_diagnostic_sha256"] = diagnostic_sha256(second)
    reviewed["correspondence"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate correspondence_id"):
        paired_report(original, revision, ORIGINAL, REVISION, reviewed)


def test_human_rates_keep_each_dimension_and_its_denominator() -> None:
    findings = [finding(message=f"Toy warning {index}") for index in range(3)]
    original = evaluation(ORIGINAL, "original", findings)
    revision = evaluation(REVISION, "revision", [])
    reviewed = review(original, revision)
    reviewed["correspondence"] = [
        {
            "correspondence_id": f"toy-change-{index}",
            "original_diagnostic_sha256": diagnostic_sha256(item),
            "revision_diagnostic_sha256": None,
            "finding_helpful": "yes",
            "meaning_preserved": answer,
        }
        for index, (item, answer) in enumerate(
            zip(findings, ["yes", "no", "context-dependent"], strict=True)
        )
    ]
    report = paired_report(original, revision, ORIGINAL, REVISION, reviewed)
    meaning = report["human_outcomes"]["meaning_preserved"]
    assert meaning["rows_count"] == 3
    assert meaning["answered_count"] == 2
    assert meaning["yes_rate"] == 0.5
    assert meaning["status_counts"]["context-dependent"] == 1
    assert report["human_outcomes"]["finding_helpful"]["answered_count"] == 3
    assert report["human_outcomes"]["finding_helpful"]["yes_rate"] == 1
    assert report["human_outcomes"]["suggestion_fits_sentence"]["yes_rate"] is None
    assert report["reviewed"]["judgments"]["removed_valid"] == 0


@pytest.mark.parametrize("representation", ["asdict", "jsonl"])
def test_production_single_line_record_keeps_implicit_end_line_and_digest(
    tmp_path: Path, representation: str
) -> None:
    effective, linter, _rules = prepare_scan(
        Config(), select="V001", severity="info", min_confidence="low"
    )
    issues = linter.check_content(ORIGINAL.decode(), Path("original.md"))
    assert len(issues) == 1
    record = asdict(issues[0])
    record["severity"] = issues[0].severity.value
    record["confidence"] = issues[0].confidence.value
    if representation == "jsonl":
        config = tmp_path / "config.toml"
        config.write_text("")
        result = run_cli(
            "check",
            "-",
            "--filename",
            "original.md",
            "--config",
            str(config),
            "--select",
            "V001",
            "--severity",
            "info",
            "--min-confidence",
            "low",
            "--format",
            "jsonl",
            stdin=ORIGINAL.decode(),
        )
        assert result.exit_code == 1
        assert result.stderr == ""
        lines = result.stdout.splitlines()
        assert len(lines) == 1
        output = json.loads(lines[0])
        assert {field: output[field] for field in record} == record
        record = {field: output[field] for field in record}
    assert record["end_line"] is None
    assert record["end_column"] == 8
    identity = diagnostic_sha256(record)
    original = evaluation(ORIGINAL, "original", [record])
    revision = evaluation(REVISION, "revision", [])
    original["policy"] = asdict(effective)
    revision["policy"] = asdict(effective)
    reviewed = review(
        original,
        revision,
        original_diagnostic_sha256=identity,
        revision_diagnostic_sha256=None,
    )
    report = paired_report(original, revision, ORIGINAL, REVISION, reviewed)
    assert report["original"]["findings"] == [record]
    assert report["original"]["findings"][0]["end_line"] is None
    assert diagnostic_sha256(report["original"]["findings"][0]) == identity
    assert report["reviewed"]["rows"][0]["original_diagnostic_sha256"] == identity
    assert record["end_line"] is None


@pytest.mark.parametrize("end_line", [None, 1])
def test_zero_width_ordinary_finding_is_rejected(end_line: int | None) -> None:
    original = evaluation(
        ORIGINAL, "original", [finding(end_line=end_line, end_column=1)]
    )
    revision = evaluation(REVISION, "revision", [])
    with pytest.raises(ValueError, match="zero-width"):
        paired_report(original, revision, ORIGINAL, REVISION)


@pytest.mark.parametrize("end_line", [None, 1])
def test_m004_zero_width_exception_preserves_exact_record(
    end_line: int | None,
) -> None:
    record = finding(rule_id="M004", end_line=end_line, end_column=1)
    original = evaluation(ORIGINAL, "original", [record])
    revision = evaluation(REVISION, "revision", [])
    report = paired_report(original, revision, ORIGINAL, REVISION)
    assert report["original"]["findings"] == [record]
    assert report["reviewed"]["unmatched_original"] == [diagnostic_sha256(record)]
