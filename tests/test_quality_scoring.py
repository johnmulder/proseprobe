"""Scoring contracts for source spans and independently reviewed regions."""

import hashlib
import json
from pathlib import Path

import pytest
from benchmarks.rule_quality import (
    ActualFinding,
    AnnotationError,
    Annotations,
    ExpectedFinding,
    collect_findings,
    load_annotations,
    score_findings,
)


def _manifest(root: Path, entry: dict[str, object], version: int = 2) -> Path:
    path = root / "annotations.json"
    path.write_text(json.dumps({"version": version, "files": {"doc.md": entry}}))
    return path


def _entry() -> dict[str, object]:
    return {
        "expected": [],
        "negative_cases": [],
        "reviewed_rules": [],
        "regions": [],
        "source_group": "fixture-repository",
    }


def _bound_manifest(root: Path, *, reviewed: bool = True) -> Path:
    from benchmarks.evaluation_identity import rule_contract_snapshot

    source = root / "doc.md"
    source.write_bytes("delve café\n".encode())
    binding = {
        "source_id": "fixture-1",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    index = root / "index.json"
    index.write_text(json.dumps({"version": 1, "files": {"doc.md": binding}}))
    contracts = root / "contracts.json"
    contracts.write_text(json.dumps(rule_contract_snapshot({"V001"})))
    entry = _entry() | binding
    entry["reviewed_rules"] = ["V001"] if reviewed else []
    review = {
        "packet_index": {
            "path": "index.json",
            "sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
        },
        "rule_contracts": {
            "path": "contracts.json",
            "sha256": hashlib.sha256(contracts.read_bytes()).hexdigest(),
        },
        "protocol_revision": "fixture-protocol-1",
        "policy": {
            "mode": "production",
            "profile": "default",
            "severity": "warning",
            "min_confidence": "low",
        },
        "reviewers": ["reviewer-fixture"] if reviewed else [],
    }
    manifest = root / "annotations.json"
    manifest.write_text(
        json.dumps({"version": 3, "review": review, "files": {"doc.md": entry}})
    )
    return manifest


@pytest.mark.parametrize(
    "replacement", [b"plain cafe\n", "delve café\r\n".encode(), "delve cafè\n".encode()]
)
def test_bound_annotations_reject_changed_raw_source_bytes(
    tmp_path: Path, replacement: bytes
) -> None:
    manifest = _bound_manifest(tmp_path)
    load_annotations(manifest, tmp_path, {"V001"})
    (tmp_path / "doc.md").write_bytes(replacement)
    with pytest.raises(AnnotationError, match=r"doc\.md.*SHA-256"):
        load_annotations(manifest, tmp_path, {"V001"})


@pytest.mark.parametrize(
    ("field", "value"), [("source_id", ""), ("sha256", "bad"), ("extra", "unknown")]
)
def test_bound_annotation_fields_are_strict(
    tmp_path: Path, field: str, value: str
) -> None:
    manifest = _bound_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    data["files"]["doc.md"][field] = value
    manifest.write_text(json.dumps(data))
    with pytest.raises(AnnotationError):
        load_annotations(manifest, tmp_path, {"V001"})


@pytest.mark.parametrize("artifact", ["index.json", "contracts.json"])
def test_bound_annotations_verify_referenced_artifacts(
    tmp_path: Path, artifact: str
) -> None:
    manifest = _bound_manifest(tmp_path)
    (tmp_path / artifact).write_text("{}")
    with pytest.raises(AnnotationError, match="SHA-256"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_bound_annotation_reviewers_cannot_be_invented_for_unreviewed_template(
    tmp_path: Path,
) -> None:
    manifest = _bound_manifest(tmp_path, reviewed=False)
    annotations = load_annotations(manifest, tmp_path, {"V001"})
    assert annotations.source_binding == "sha256-utf8"
    assert annotations.review_provenance["reviewers"] == []
    data = json.loads(manifest.read_text())
    data["files"]["doc.md"]["reviewed_rules"] = ["V001"]
    manifest.write_text(json.dumps(data))
    with pytest.raises(AnnotationError, match="reviewer"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_bound_source_mutation_during_collection_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from benchmarks.rule_quality import prepare_evaluation_scan

    annotations = load_annotations(_bound_manifest(tmp_path), tmp_path, {"V001"})
    _config, linter, _rules = prepare_evaluation_scan()
    original = linter.check_content

    def changing_check(source: str, path: Path):
        results = original(source, path)
        (tmp_path / "doc.md").write_text("plain cafe\n")
        return results

    monkeypatch.setattr(linter, "check_content", changing_check)
    with pytest.raises(AnnotationError, match="SHA-256"):
        collect_findings(annotations, tmp_path, linter=linter)


def test_bound_collection_uses_verified_bytes_despite_a_different_second_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    annotations = load_annotations(_bound_manifest(tmp_path), tmp_path, {"V001"})
    original = Path.read_text

    def different_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == tmp_path / "doc.md":
            return "plain\n"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", different_read)
    findings = collect_findings(annotations, tmp_path)
    assert [finding.rule_id for finding in findings] == ["V001"]
    from benchmarks.quality_scoring import count_prose_words

    assert count_prose_words(annotations, tmp_path, {"V001"})["markdown"] == 2
    assert (tmp_path / "doc.md").read_bytes() == "delve café\n".encode()


def test_bound_collection_preserves_discovery_and_per_file_policy(
    tmp_path: Path,
) -> None:
    from benchmarks.rule_quality import prepare_evaluation_scan

    from proseprobe.config import Config, PerFileIgnore

    annotations = load_annotations(_bound_manifest(tmp_path), tmp_path, {"V001"})
    for config in (
        Config(select=["V001"], exclude=["doc.md"]),
        Config(select=["V001"], per_file_ignores=[PerFileIgnore("doc.md", ["V001"])]),
    ):
        _config, linter, _rules = prepare_evaluation_scan(config=config)
        assert collect_findings(annotations, tmp_path, linter=linter) == ()


@pytest.mark.parametrize(
    "change",
    [
        "missing-review",
        "missing-source-id",
        "duplicate-source-id",
        "empty-protocol",
        "unknown-review-key",
        "duplicate-reviewer",
        "index-mismatch",
        "contract-change",
        "unknown-profile",
        "impossible-all-rules-policy",
        "invented-context-source",
        "wrong-context-group",
    ],
)
def test_bound_annotations_reject_inconsistent_review_metadata(
    tmp_path: Path, change: str
) -> None:
    manifest = _bound_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    if change == "missing-review":
        del data["review"]
    elif change == "missing-source-id":
        del data["files"]["doc.md"]["source_id"]
    elif change == "duplicate-source-id":
        (tmp_path / "other.md").write_bytes((tmp_path / "doc.md").read_bytes())
        data["files"]["other.md"] = data["files"]["doc.md"]
    elif change == "empty-protocol":
        data["review"]["protocol_revision"] = ""
    elif change == "unknown-review-key":
        data["review"]["certified"] = True
    elif change == "duplicate-reviewer":
        data["review"]["reviewers"] *= 2
    elif change == "unknown-profile":
        data["review"]["policy"]["profile"] = "imaginary-profile"
    elif change == "impossible-all-rules-policy":
        data["review"]["policy"]["mode"] = "all-rules"
    else:
        artifact = "contracts.json" if change == "contract-change" else "index.json"
        content = json.loads((tmp_path / artifact).read_text())
        if change == "index-mismatch":
            content["files"]["doc.md"]["source_id"] = "different-packet"
        elif change == "contract-change":
            content["rules"]["V001"]["description"] = "Different declared contract"
        else:
            path = "invented.md" if change == "invented-context-source" else "doc.md"
            content["context"] = {
                path: {
                    "source_group": "wrong-group",
                    "pair_group": "fixture-1",
                    "split": "development",
                    "format": "markdown",
                }
            }
        (tmp_path / artifact).write_text(json.dumps(content))
        reference = "rule_contracts" if change == "contract-change" else "packet_index"
        data["review"][reference]["sha256"] = hashlib.sha256(
            (tmp_path / artifact).read_bytes()
        ).hexdigest()
    manifest.write_text(json.dumps(data))
    with pytest.raises(AnnotationError):
        load_annotations(manifest, tmp_path, {"V001"})


def test_legacy_reports_explicitly_identify_unbound_labels(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from benchmarks.rule_quality import main

    (tmp_path / "doc.md").write_text("plain\n")
    manifest = _manifest(tmp_path, _entry())
    args = ["--manifest", str(manifest), "--root", str(tmp_path), "--format", "json"]
    assert main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["source_binding"] == "legacy-unbound"
    assert report["review_provenance"] == "unavailable"
    assert main([*args, "--require-bound"]) == 2
    assert "source-bound" in capsys.readouterr().err


def test_bound_manifest_strict_cli_success_preserves_review_identity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from benchmarks.rule_quality import main

    manifest = _bound_manifest(tmp_path, reviewed=False)
    assert (
        main(
            [
                "--manifest",
                str(manifest),
                "--root",
                str(tmp_path),
                "--format",
                "json",
                "--require-bound",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["source_binding"] == "sha256-utf8"
    assert report["review_provenance"]["reviewers"] == []


def test_expected_and_actual_endpoints_survive_collection(tmp_path: Path) -> None:
    source = tmp_path / "doc.md"
    source.write_text("delve\nplain\n")
    entry = {
        "expected": [{"rule_id": "V001", "line": 1, "column": 1, "end_column": 6}],
        "negative_cases": [{"rule_id": "V001", "line": 2, "note": "plain"}],
    }
    annotations = load_annotations(_manifest(tmp_path, entry, 1), tmp_path, {"V001"})

    assert annotations.expected[0].end_column == 6
    assert annotations.expected[0].end_line is None
    [actual] = [
        item
        for item in collect_findings(annotations, tmp_path)
        if item.rule_id == "V001"
    ]
    assert actual.end_column == 6
    assert actual.severity == "warning"
    assert actual.confidence == "high"


@pytest.mark.parametrize(
    "endpoints",
    [
        {"end_line": 1},
        {"end_column": 1},
        {"end_column": 0},
        {"end_line": True, "end_column": 2},
        {"end_line": 2, "end_column": 100},
    ],
)
def test_rejects_invalid_or_empty_positive_spans(
    tmp_path: Path, endpoints: dict[str, object]
) -> None:
    (tmp_path / "doc.md").write_text("delve\nplain\n")
    entry = {
        "expected": [{"rule_id": "V001", "line": 1, "column": 1, **endpoints}],
        "negative_cases": [{"rule_id": "V001", "line": 2, "note": "plain"}],
    }

    with pytest.raises(AnnotationError):
        load_annotations(_manifest(tmp_path, entry, 1), tmp_path, {"V001"})


def test_m004_may_have_an_explicit_zero_width_positive(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("text\n")
    entry = _entry()
    entry["reviewed_rules"] = ["M004"]
    entry["expected"] = [{"rule_id": "M004", "line": 1, "column": 1, "end_column": 1}]

    annotations = load_annotations(_manifest(tmp_path, entry), tmp_path, {"M004"})
    assert annotations.expected[0].end_column == 1


def test_reviewed_semantic_match_keeps_location_mismatch_separate() -> None:
    from benchmarks.rule_quality import SourceSpan

    expected = (
        ExpectedFinding(
            "doc.md",
            "V001",
            1,
            1,
            end_column=6,
            identity="word-1",
            match_region=SourceSpan(1, 1, 1, 8),
        ),
    )
    actual = (ActualFinding("doc.md", "V001", 1, 2, end_column=6),)

    score = score_findings(expected, actual, (), {"V001"})

    assert score.metrics["V001"].true_positives == 1
    assert score.exact_start_metrics["V001"].true_positives == 0
    assert score.exact_start_metrics["V001"].false_positives == 1
    assert score.exact_start_metrics["V001"].false_negatives == 1
    assert score.locations["V001"].matches == 1
    assert score.locations["V001"].exact_starts == 0
    assert score.locations["V001"].span_total == 1
    assert score.locations["V001"].exact_spans == 0


@pytest.mark.parametrize("end_column", [None, 5])
def test_exact_start_with_missing_or_wrong_end_fails_only_full_span(
    end_column: int | None,
) -> None:
    expected = (ExpectedFinding("doc.md", "V001", 1, 1, end_column=6),)
    actual = (ActualFinding("doc.md", "V001", 1, 1, end_column=end_column),)

    score = score_findings(expected, actual, (), {"V001"})

    assert score.metrics["V001"].true_positives == 1
    assert score.locations["V001"].exact_starts == 1
    assert score.locations["V001"].exact_spans == 0
    assert score.locations["V001"].span_total == 1


def test_duplicate_matching_is_one_to_one_and_order_independent() -> None:
    expected = (ExpectedFinding("doc.md", "V001", 1, 1, end_column=6),)
    actual = (
        ActualFinding("doc.md", "V001", 1, 1, end_column=5),
        ActualFinding("doc.md", "V001", 1, 1, end_column=6),
    )

    first = score_findings(expected, actual, (), {"V001"})
    second = score_findings(expected, tuple(reversed(actual)), (), {"V001"})

    assert first == second
    assert first.metrics["V001"].true_positives == 1
    assert first.metrics["V001"].false_positives == 1
    assert first.locations["V001"].exact_spans == 1


def test_partial_regions_keep_unknown_and_unsupported_predictions_out_of_precision(
    tmp_path: Path,
) -> None:
    (tmp_path / "doc.md").write_text("delve\ndelve\ndelve\ndelve\n")
    entry = _entry()
    entry["expected"] = [{"rule_id": "V001", "line": 1, "column": 1}]
    entry["regions"] = [
        {
            "rules": ["V001"],
            "status": status,
            "line": line,
            "column": 1,
            "end_column": 6,
            "note": status,
        }
        for line, status in (
            (1, "reviewed"),
            (3, "unsupported"),
            (4, "context-dependent"),
        )
    ]
    annotations = load_annotations(
        _manifest(tmp_path, entry), tmp_path, {"V001", "M007"}
    )
    actual = tuple(
        ActualFinding("doc.md", "V001", line, 1, end_column=6) for line in range(1, 5)
    )

    score = score_findings(
        annotations.expected, actual, (), {"V001"}, scopes=annotations.scopes
    )

    assert score.metrics["V001"].true_positives == 1
    assert score.metrics["V001"].false_positives == 0
    assert (
        len(score.unreviewed)
        == len(score.unsupported)
        == len(score.context_dependent)
        == 1
    )
    assert annotations.source_groups == {"doc.md": "fixture-repository"}


def test_negative_span_can_share_a_line_with_a_disjoint_positive(
    tmp_path: Path,
) -> None:
    (tmp_path / "doc.md").write_text("delve plain\n")
    entry = _entry()
    entry["reviewed_rules"] = ["V001"]
    entry["expected"] = [{"rule_id": "V001", "line": 1, "column": 1, "end_column": 6}]
    entry["negative_cases"] = [
        {
            "rule_id": "V001",
            "line": 1,
            "column": 7,
            "end_column": 12,
            "note": "plain word",
        }
    ]
    annotations = load_annotations(_manifest(tmp_path, entry), tmp_path, {"V001"})
    actual = (
        ActualFinding("doc.md", "V001", 1, 1, end_column=6),
        ActualFinding("doc.md", "V001", 1, 7, end_column=12),
    )

    score = score_findings(
        annotations.expected,
        actual,
        annotations.negative_cases,
        {"V001"},
        scopes=annotations.scopes,
    )

    assert score.metrics["V001"].true_positives == 1
    assert score.metrics["V001"].false_positives == 1
    assert score.metrics["V001"].negatives_passed == 0
    assert score.false_positives[0].negative_note == "plain word"


@pytest.mark.parametrize("duplicate_identity", [False, True])
def test_rejects_ambiguous_semantic_regions_and_identities(
    tmp_path: Path, duplicate_identity: bool
) -> None:
    (tmp_path / "doc.md").write_text("delve delve\n")
    entry = _entry()
    entry["reviewed_rules"] = ["V001"]
    entry["expected"] = [
        {
            "rule_id": "V001",
            "line": 1,
            "column": 1,
            "id": "same",
            "match_region": {"line": 1, "column": 1, "end_column": 9},
        },
        {
            "rule_id": "V001",
            "line": 1,
            "column": 7,
            "id": "same" if duplicate_identity else "second",
            "match_region": {"line": 1, "column": 7, "end_column": 12},
        },
    ]

    with pytest.raises(AnnotationError):
        load_annotations(_manifest(tmp_path, entry), tmp_path, {"V001"})


def test_metrics_use_real_denominators_and_sample_only_wilson_intervals() -> None:
    from benchmarks.rule_quality import metric_summary, wilson_interval

    expected = (
        ExpectedFinding("doc.md", "V001", 1, 1),
        ExpectedFinding("doc.md", "V001", 2, 1),
    )
    actual = (
        ActualFinding("doc.md", "V001", 1, 1),
        ActualFinding("doc.md", "V001", 3, 1),
    )
    score = score_findings(expected, actual, (), {"V001"})
    result = metric_summary(score.metrics["V001"], prose_words=4, false_warnings=1)

    assert result["precision"] == result["recall"] == 0.5
    assert result["precision_denominator"] == result["recall_denominator"] == 2
    assert result["false_warnings_per_1000_prose_words"] == 250
    assert (
        result["uncertainty_scope"]
        == "reviewed sample; independence assumed, no population or cluster inference"
    )
    assert wilson_interval(0, 0) is None
    low, high = wilson_interval(1, 1)
    assert low == pytest.approx(0.20655, abs=0.00001)
    assert high == pytest.approx(1)


def test_prose_word_counts_exclude_code_and_count_python_contexts(
    tmp_path: Path,
) -> None:
    from benchmarks.rule_quality import count_prose_words

    markdown = tmp_path / "doc.md"
    markdown.write_text("one two\n\n```python title=example\nignored words\n```\n")
    python = tmp_path / "doc.py"
    python.write_text('"""three four"""\n# five six\nvalue = "ignored words"\n')
    annotations = Annotations((markdown, python), (), ())

    words = count_prose_words(annotations, tmp_path, {"V001"})

    assert words == {"markdown": 2, "docstring": 2, "comment": 2}


def test_json_breakdowns_keep_confidence_recall_unassigned_and_show_sample_limits(
    tmp_path: Path,
) -> None:
    from benchmarks.rule_quality import format_json_report

    from proseprobe.config import Config

    source = tmp_path / "doc.md"
    source.write_text("one two\nthree four\n")
    expected = (
        ExpectedFinding("doc.md", "V001", 1, 1, severity="warning"),
        ExpectedFinding("doc.md", "V001", 2, 1, severity="warning"),
    )
    actual = (
        ActualFinding("doc.md", "V001", 1, 1, confidence="high"),
        ActualFinding("doc.md", "V001", 1, 5, confidence="low"),
    )
    annotations = Annotations(
        (source,), expected, (), source_groups={"doc.md": "one-repository"}
    )
    manifest = _manifest(tmp_path, _entry())
    score = score_findings(expected, actual, (), {"V001"})

    report = json.loads(
        format_json_report(
            score,
            mode="production",
            config=Config(),
            annotations=annotations,
            eligible=annotations,
            manifest_path=manifest,
            repo_root=tmp_path,
        )
    )

    assert report["metrics"]["precision"] == report["metrics"]["recall"] == 0.5
    assert report["metrics"]["false_warnings_per_1000_prose_words"] == 250
    assert report["breakdowns"]["severity"]["warning"]["false_negatives"] == 1
    assert report["breakdowns"]["format"]["markdown"]["recall_denominator"] == 2
    assert report["breakdowns"]["confidence"]["high"]["true_positives"] == 1
    assert report["breakdowns"]["confidence"]["low"]["false_positives"] == 1
    assert report["breakdowns"]["confidence"]["high"]["recall"] is None
    assert report["breakdowns"]["confidence"]["unassigned"]["false_negatives"] == 1
    assert report["source_group_count"] == 1
    assert report["cluster_interval"] is None
    assert "too few" in report["cluster_interval_reason"]


def test_external_manifest_cli_keeps_unreviewed_inputs_out_of_false_positives(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from benchmarks.rule_quality import main

    source = tmp_path / "doc.md"
    source.write_text("delve\n")
    manifest = _manifest(tmp_path, _entry())

    assert (
        main(["--manifest", str(manifest), "--root", str(tmp_path), "--format", "json"])
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["totals"]["false_positives"] == 0
    assert report["unreviewed_count"] == 1
    assert report["metrics"]["precision"] is None
    assert report["metrics"]["false_warnings_per_1000_prose_words"] is None


def test_a_semantic_region_cannot_cover_another_same_rule_issue(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("delve delve\n")
    entry = _entry()
    entry["reviewed_rules"] = ["V001"]
    entry["expected"] = [
        {
            "rule_id": "V001",
            "line": 1,
            "column": 1,
            "id": "first",
            "match_region": {"line": 1, "column": 1, "end_column": 12},
        },
        {"rule_id": "V001", "line": 1, "column": 7},
    ]

    with pytest.raises(AnnotationError, match="ambiguous"):
        load_annotations(_manifest(tmp_path, entry), tmp_path, {"V001"})


@pytest.mark.parametrize("rule_id", ["V001", "V002"])
def test_overlap_or_wrong_rule_is_not_a_semantic_match(rule_id: str) -> None:
    from benchmarks.rule_quality import SourceSpan

    expected = (
        ExpectedFinding(
            "doc.md",
            "V001",
            1,
            1,
            identity="first",
            match_region=SourceSpan(1, 1, 1, 6),
        ),
    )
    actual = (ActualFinding("doc.md", rule_id, 1, 5, end_column=8),)

    score = score_findings(expected, actual, (), {"V001", "V002"})

    assert score.metrics["V001"].false_negatives == 1
    assert score.metrics[rule_id].false_positives == 1
    assert sum(metrics.true_positives for metrics in score.metrics.values()) == 0


def test_semantic_match_cannot_use_an_explicitly_unsupported_region() -> None:
    from benchmarks.rule_quality import ReviewScope, SourceSpan

    expected = (
        ExpectedFinding(
            "doc.md",
            "V001",
            1,
            1,
            identity="first",
            match_region=SourceSpan(1, 1, 1, 8),
        ),
    )
    actual = (ActualFinding("doc.md", "V001", 1, 5, end_column=6),)
    scopes = (
        ReviewScope("doc.md", ("V001",)),
        ReviewScope("doc.md", ("V001",), "unsupported", SourceSpan(1, 4, 1, 8)),
    )

    score = score_findings(expected, actual, (), {"V001"}, scopes=scopes)

    assert score.metrics["V001"].false_negatives == 1
    assert score.metrics["V001"].true_positives == 0
    assert score.unsupported == actual


def test_a_finding_crossing_review_boundaries_is_unreviewed() -> None:
    from benchmarks.rule_quality import ReviewScope, SourceSpan

    actual = (ActualFinding("doc.md", "V001", 1, 1, end_column=6),)
    scopes = (
        ReviewScope("doc.md", ("V001",)),
        ReviewScope("doc.md", ("V001",), "unsupported", SourceSpan(1, 4, 1, 8)),
    )

    score = score_findings((), actual, (), {"V001"}, scopes=scopes)

    assert score.metrics["V001"].false_positives == 0
    assert score.unreviewed == actual


def test_unresolved_or_unsupported_scope_requires_a_reason(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("text\n")
    entry = _entry()
    entry["regions"] = [
        {
            "rules": ["V001"],
            "status": "context-dependent",
            "line": 1,
            "column": 1,
            "end_column": 5,
        }
    ]

    with pytest.raises(AnnotationError, match="non-empty"):
        load_annotations(_manifest(tmp_path, entry), tmp_path, {"V001"})


def test_start_only_legacy_annotation_does_not_claim_full_span_accuracy() -> None:
    expected = (ExpectedFinding("doc.md", "V001", 1, 1, "legacy note"),)
    actual = (ActualFinding("doc.md", "V001", 1, 1, "message", end_column=6),)

    score = score_findings(expected, actual, (), {"V001"})

    assert score.metrics["V001"].true_positives == 1
    assert score.locations["V001"].span_total == 0


def test_actual_python_context_distinguishes_inline_comments_from_docstrings(
    tmp_path: Path,
) -> None:
    source = tmp_path / "doc.py"
    source.write_text('"""delve"""  # notable\n# delve\n')

    actual = collect_findings(Annotations((source,), (), ()), tmp_path)
    findings = [item for item in actual if item.rule_id == "V001"]

    assert [(item.line, item.context) for item in findings] == [
        (1, "docstring"),
        (1, "comment"),
        (2, "comment"),
    ]


@pytest.mark.parametrize("version", [True, 1.0, 2.0, "1"])
def test_version_is_a_strict_integer(tmp_path: Path, version: object) -> None:
    (tmp_path / "doc.md").write_text("plain\n")
    manifest = tmp_path / "annotations.json"
    manifest.write_text(json.dumps({"version": version, "files": {"doc.md": _entry()}}))

    with pytest.raises(AnnotationError, match="version"):
        load_annotations(manifest, tmp_path, {"V001"})


def test_partial_word_density_uses_only_whole_reviewed_words(tmp_path: Path) -> None:
    from benchmarks.rule_quality import (
        ReviewScope,
        SourceSpan,
        count_prose_words,
        metric_summary,
    )

    source = tmp_path / "doc.md"
    source.write_text("one two\n")
    annotations = Annotations(
        (source,),
        (),
        (),
        (ReviewScope("doc.md", ("V001",), span=SourceSpan(1, 1, 1, 6)),),
    )
    words = count_prose_words(annotations, tmp_path, {"V001"})
    score = score_findings(
        (),
        (ActualFinding("doc.md", "V001", 1, 1, end_column=4),),
        (),
        {"V001"},
        scopes=annotations.scopes,
    )

    assert sum(words.values()) == 1
    assert (
        metric_summary(
            score.metrics["V001"], prose_words=sum(words.values()), false_warnings=1
        )["false_warnings_per_1000_prose_words"]
        == 1000
    )
    assert (
        sum(
            count_prose_words(
                Annotations((source,), (), (), ()), tmp_path, {"V001"}
            ).values()
        )
        == 0
    )


def test_disabled_rule_coverage_does_not_grant_density_denominator(
    tmp_path: Path,
) -> None:
    from benchmarks.rule_quality import (
        ReviewScope,
        count_prose_words,
        eligible_annotations,
        prepare_evaluation_scan,
    )

    source = tmp_path / "doc.md"
    source.write_text("one two\n")
    annotations = Annotations((source,), (), (), (ReviewScope("doc.md", ("V004",)),))
    _config, linter, rules = prepare_evaluation_scan(mode="production", select="V001")
    eligible = eligible_annotations(annotations, tmp_path, linter, rules)

    assert (
        sum(count_prose_words(eligible, tmp_path, {rule.id for rule in rules}).values())
        == 0
    )


def test_semantic_identity_cannot_be_blank(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("delve\n")
    entry = _entry()
    entry["reviewed_rules"] = ["V001"]
    entry["expected"] = [
        {
            "rule_id": "V001",
            "line": 1,
            "column": 1,
            "id": " ",
            "match_region": {"line": 1, "column": 1, "end_column": 6},
        }
    ]

    with pytest.raises(AnnotationError, match="non-empty"):
        load_annotations(_manifest(tmp_path, entry), tmp_path, {"V001"})
