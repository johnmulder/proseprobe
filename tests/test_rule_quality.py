"""Tests for the reviewed-corpus quality evaluator."""

import json
from pathlib import Path

import pytest
from benchmarks.rule_quality import (
    DEFAULT_MANIFEST,
    REPO_ROOT,
    ActualFinding,
    AnnotationError,
    ExpectedFinding,
    NegativeCase,
    collect_findings,
    format_report,
    load_annotations,
    score_findings,
)

from proseprobe.config import Config
from proseprobe.core.linter import Linter
from proseprobe.rules import get_all_rules

_EXACT_SPAN_RULE_IDS = frozenset(
    {
        "C001",
        "C002",
        "C003",
        "C004",
        "G004",
        "G005",
        "G006",
        "G007",
        "G008",
        "G009",
        "G017",
        "G024",
        "G029",
        "M001",
        "M008",
        "M009",
        "M010",
        "S001",
        "S008",
        "S009",
        "S014",
        "S015",
        "S016",
        "S021",
        "S022",
        "S025",
        "S028",
        "T001",
        "T004",
        "T005",
        "T006",
        "T008",
        "T010",
        "T012",
        "T014",
        "T015",
        "V006",
        "V007",
        "V009",
        "V010",
        "V011",
        "V013",
        "V014",
        "V016",
    }
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


def test_rejects_malformed_json(tmp_path: Path) -> None:
    """Invalid JSON should retain the manifest path in its error."""
    manifest = tmp_path / "annotations.json"
    manifest.write_text("{")

    with pytest.raises(AnnotationError, match=r"annotations\.json: invalid JSON"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_rejects_missing_corpus_file(tmp_path: Path) -> None:
    """Every manifest path should resolve to a real source file."""
    manifest = _write_manifest(tmp_path, _valid_manifest())

    with pytest.raises(AnnotationError, match="source file does not exist"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_rejects_duplicate_expected_location(tmp_path: Path) -> None:
    """One source location may be expected only once per rule."""
    (tmp_path / "doc.md").write_text("delve\nplain\n")
    data = _valid_manifest()
    expected = data["files"]["doc.md"]["expected"]  # type: ignore[index]
    expected.append(dict(expected[0]))  # type: ignore[union-attr]
    manifest = _write_manifest(tmp_path, data)

    with pytest.raises(AnnotationError, match="duplicates an expected location"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_rejects_conflicting_negative_case(tmp_path: Path) -> None:
    """A location cannot assert that the same rule is present and absent."""
    (tmp_path / "doc.md").write_text("delve\nplain\n")
    data = _valid_manifest()
    negative = data["files"]["doc.md"]["negative_cases"][0]  # type: ignore[index]
    negative["line"] = 1  # type: ignore[index]
    manifest = _write_manifest(tmp_path, data)

    with pytest.raises(AnnotationError, match="conflicts with an expected finding"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_reviewed_corpus_covers_every_registered_rule() -> None:
    """The committed manifest should cover the live rule registry."""
    rule_ids = {rule.id for rule in get_all_rules(Config())}

    annotations = load_annotations(DEFAULT_MANIFEST, REPO_ROOT, rule_ids)

    assert {item.rule_id for item in annotations.expected} == rule_ids
    assert {item.rule_id for item in annotations.negative_cases} == rule_ids


def test_reviewed_findings_have_unique_rule_source_starts() -> None:
    """One rule should not emit two findings at one reviewed source start."""
    rule_ids = {rule.id for rule in get_all_rules(Config())}
    annotations = load_annotations(DEFAULT_MANIFEST, REPO_ROOT, rule_ids)

    findings = collect_findings(annotations, REPO_ROOT)
    locations = [(item.path, item.rule_id, item.line, item.column) for item in findings]

    assert len(locations) == len(set(locations))


def test_reviewed_concrete_spans_are_complete_and_in_bounds() -> None:
    config = Config()
    rules = get_all_rules(config)
    annotations = load_annotations(DEFAULT_MANIFEST, REPO_ROOT, {r.id for r in rules})
    linter = Linter(config)
    for rule in rules:
        linter.register_rule(rule)

    results = linter.check(list(annotations.files)).issues_by_file

    for path, issues in results.items():
        lines = path.read_text(encoding="utf-8").splitlines()
        for issue in issues:
            if issue.rule_id in _EXACT_SPAN_RULE_IDS:
                assert issue.end_column is not None, issue.rule_id
            if issue.end_column is None:
                assert issue.end_line is None
                continue
            end_line = issue.end_line or issue.line
            assert issue.line <= end_line <= len(lines)
            assert 1 <= issue.column <= len(lines[issue.line - 1]) + 1
            assert 1 <= issue.end_column <= len(lines[end_line - 1]) + 1
            if issue.line == end_line:
                assert issue.column <= issue.end_column
                if issue.column == issue.end_column:
                    assert issue.rule_id == "M004"
