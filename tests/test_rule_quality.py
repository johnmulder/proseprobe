"""Tests for the reviewed-corpus quality evaluator."""

import json
from pathlib import Path

import pytest
from benchmarks.rule_quality import (
    ActualFinding,
    AnnotationError,
    ExpectedFinding,
    NegativeCase,
    format_report,
    load_annotations,
    score_findings,
)


def test_scores_matches_mismatches_and_negative_cases() -> None:
    """Scoring should distinguish each quality outcome."""
    expected = (
        ExpectedFinding("doc.md", "V001", 1, 1, "expected word"),
        ExpectedFinding("doc.md", "V001", 2, 1, "missed word"),
    )
    actual = (
        ActualFinding("doc.md", "V001", 1, 1, "matched"),
        ActualFinding("doc.md", "V001", 3, 1, "unexpected"),
    )
    negatives = (NegativeCase("doc.md", "V001", 3, "legitimate usage"),)

    score = score_findings(expected, actual, negatives, {"V001"})

    metrics = score.metrics["V001"]
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.negatives_passed == 0
    assert metrics.negatives_total == 1
    assert score.false_positives[0].negative_note == "legitimate usage"
    assert score.false_negatives == (expected[1],)


def test_duplicate_actual_location_is_not_double_counted() -> None:
    """One expected location should match only one actual finding."""
    expected = (ExpectedFinding("doc.md", "V001", 1, 1),)
    actual = (
        ActualFinding("doc.md", "V001", 1, 1, "first"),
        ActualFinding("doc.md", "V001", 1, 1, "duplicate"),
    )

    score = score_findings(expected, actual, (), {"V001"})

    assert score.metrics["V001"].true_positives == 1
    assert score.metrics["V001"].false_positives == 1


def test_report_is_sorted_and_handles_empty_denominators() -> None:
    """Reports should be deterministic and show n/a for absent observations."""
    score = score_findings((), (), (), {"V002", "V001"})

    report = format_report(score)

    assert report.index("V001") < report.index("V002")
    assert "n/a" in report


def _write_manifest(root: Path, data: object) -> Path:
    manifest = root / "annotations.json"
    manifest.write_text(json.dumps(data))
    return manifest


def _valid_manifest() -> dict[str, object]:
    return {
        "version": 1,
        "files": {
            "doc.md": {
                "expected": [{"rule_id": "V001", "line": 1, "column": 1}],
                "negative_cases": [{"rule_id": "V001", "line": 2, "note": "near miss"}],
            }
        },
    }


def test_loads_valid_annotations(tmp_path: Path) -> None:
    """A complete manifest should resolve its corpus files."""
    source = tmp_path / "doc.md"
    source.write_text("delve\nplain\n")
    manifest = _write_manifest(tmp_path, _valid_manifest())

    annotations = load_annotations(manifest, tmp_path, {"V001"})

    assert annotations.files == (source,)
    assert annotations.expected[0].rule_id == "V001"
    assert annotations.negative_cases[0].note == "near miss"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data.update({"extra": True}), "unknown key"),
        (lambda data: data.update({"version": 2}), "version must be 1"),
        (
            lambda data: data["files"]["doc.md"]["expected"][0].update(
                {"rule_id": "NOPE"}
            ),
            "rule_id is unknown",
        ),
        (
            lambda data: data["files"]["doc.md"]["expected"][0].update({"line": 99}),
            "outside the source file",
        ),
        (
            lambda data: data["files"]["doc.md"].update({"negative_cases": []}),
            "rules missing negative cases",
        ),
    ],
)
def test_rejects_invalid_annotations(
    tmp_path: Path,
    mutate: object,
    message: str,
) -> None:
    """Invalid schema, locations, and coverage should fail clearly."""
    (tmp_path / "doc.md").write_text("delve\nplain\n")
    data = _valid_manifest()
    mutate(data)  # type: ignore[operator]
    manifest = _write_manifest(tmp_path, data)

    with pytest.raises(AnnotationError, match=message):
        load_annotations(manifest, tmp_path, {"V001"})


def test_rejects_path_outside_repository(tmp_path: Path) -> None:
    """Corpus paths may not escape the declared repository root."""
    outside = tmp_path.parent / "outside.md"
    outside.write_text("text")
    data = _valid_manifest()
    data["files"] = {  # type: ignore[index]
        "../outside.md": {
            "expected": [{"rule_id": "V001", "line": 1, "column": 1}],
            "negative_cases": [{"rule_id": "V001", "line": 1, "note": "outside"}],
        }
    }
    manifest = _write_manifest(tmp_path, data)

    with pytest.raises(AnnotationError, match="escapes the repository"):
        load_annotations(manifest, tmp_path, {"V001"})
