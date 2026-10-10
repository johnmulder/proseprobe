"""Deterministic whole-source bootstrap tests use authored count fixtures."""

import pytest


def test_group_bootstrap_uses_ratio_of_sums_and_declared_reproducible_procedure() -> (
    None
):
    from benchmarks.source_intervals import source_group_interval

    groups = {"a": (8, 10), "b": (1, 2), "c": (3, 4), "d": (2, 3), "e": (4, 5)}
    result = source_group_interval(groups)
    assert result["point_estimate"] == pytest.approx(18 / 24)
    assert result["point_estimate"] != pytest.approx(
        sum(num / den for num, den in groups.values()) / 5
    )
    # Checked independently from draw frequencies and exact rational rank neighbors.
    assert result["interval_95"] == pytest.approx([9 / 14, 27 / 34])
    assert result == source_group_interval(dict(reversed(list(groups.items()))))
    assert result["seed"] == 20261010
    assert result["replicates"] == 2000
    assert result["minimum_contributing_groups"] == 5
    assert result["confidence_level"] == 0.95
    assert "conditional" in result["scope"]


def test_clean_groups_contribute_density_without_precision_denominators() -> None:
    from benchmarks.source_intervals import source_group_interval

    density = {"a": (1, 100), "b": (0, 50), "c": (0, 80), "d": (0, 90), "e": (0, 100)}
    result = source_group_interval(density, scale=1000)
    assert result["contributing_groups_count"] == 5
    assert result["point_estimate"] == pytest.approx(1000 / 420)
    assert result["interval_95"] is not None
    precision = source_group_interval(
        {"a": (1, 1), "b": (0, 0), "c": (0, 0), "d": (0, 0), "e": (0, 0)}
    )
    assert precision["contributing_groups_count"] == 1
    assert precision["interval_95"] is None
    assert "too few" in precision["unavailable_reason"]


def test_dominant_repository_share_and_contribution_sizes_are_visible() -> None:
    from benchmarks.source_intervals import source_group_interval

    groups = {
        "dominant": (900, 1000),
        "a": (0, 1),
        "b": (1, 1),
        "c": (0, 1),
        "d": (1, 1),
    }
    result = source_group_interval(groups)
    assert result["dominant_denominator_share"] == pytest.approx(1000 / 1004)
    assert result["group_counts"]["dominant"] == {"numerator": 900, "denominator": 1000}
    assert result["interval_95"] is not None


@pytest.mark.parametrize(
    ("groups", "reason"),
    [
        ({}, "denominator"),
        ({"a": (0, 0)}, "denominator"),
        ({"a": (1, 2), "b": (2, 3)}, "too few"),
        ({"unspecified": (1, 2), **{str(i): (1, 2) for i in range(5)}}, "unidentified"),
        ({"zero": (1, 0), **{str(i): (1, 2) for i in range(5)}}, "without"),
    ],
)
def test_inadequate_or_unidentified_group_support_has_no_interval(
    groups: dict[str, tuple[int, int]], reason: str
) -> None:
    from benchmarks.source_intervals import source_group_interval

    result = source_group_interval(groups)
    assert result["interval_95"] is None
    assert reason in result["unavailable_reason"]


def _report(tmp_path, rows):
    import json

    from benchmarks.rule_quality import (
        ActualFinding,
        Annotations,
        ExpectedFinding,
        format_json_report,
        score_findings,
    )

    from proseprobe.config import Config

    files, expected, actual, groups = [], [], [], {}
    for index, (group, tp, fp, fn, words) in enumerate(rows):
        name = f"fixture-{index}.md"
        source = tmp_path / name
        source.write_text(" ".join(["plain"] * words) + "\n")
        files.append(source)
        if group is not None:
            groups[name] = group
        expected.extend(
            ExpectedFinding(name, "V001", 1, column) for column in range(1, tp + fn + 1)
        )
        actual.extend(
            ActualFinding(name, "V001", 1, column)
            for column in [*range(1, tp + 1), *range(tp + fn + 1, tp + fn + fp + 1)]
        )
    annotations = Annotations(tuple(files), tuple(expected), (), source_groups=groups)
    manifest = tmp_path / "annotations.json"
    manifest.write_text(json.dumps({"version": 1, "files": {}}))
    score = score_findings(annotations.expected, tuple(actual), (), {"V001"})
    return json.loads(
        format_json_report(
            score,
            mode="all-rules",
            config=Config(),
            annotations=annotations,
            eligible=annotations,
            manifest_path=manifest,
            repo_root=tmp_path,
        )
    )


def test_evaluator_resamples_variants_in_their_shared_source_group(tmp_path) -> None:
    from benchmarks.source_intervals import source_group_interval

    report = _report(
        tmp_path,
        [
            ("a", 1, 0, 0, 10),
            ("a", 1, 1, 0, 20),
            ("b", 1, 0, 0, 5),
            ("c", 3, 0, 0, 8),
            ("d", 4, 0, 0, 9),
            ("e", 4, 0, 1, 10),
        ],
    )
    intervals = report["source_group_intervals"]
    assert intervals["precision"] == source_group_interval(
        {"a": (2, 3), "b": (1, 1), "c": (3, 3), "d": (4, 4), "e": (4, 4)}
    )
    assert intervals["recall"] == source_group_interval(
        {"a": (2, 2), "b": (1, 1), "c": (3, 3), "d": (4, 4), "e": (4, 5)}
    )
    assert intervals["density"] == source_group_interval(
        {"a": (1, 30), "b": (0, 5), "c": (0, 8), "d": (0, 9), "e": (0, 10)},
        scale=1000,
    )
    assert report["cluster_interval"] == {
        name: result["interval_95"] for name, result in intervals.items()
    }
    assert report["metric_source_group_counts"] == dict.fromkeys(
        ("precision", "recall", "density"), 5
    )
    assert report["metrics"]["precision"] == intervals["precision"]["point_estimate"]
    assert report["metrics"]["recall"] == intervals["recall"]["point_estimate"]


def test_evaluator_clean_groups_support_density_without_detection_events(
    tmp_path,
) -> None:
    report = _report(tmp_path, [(str(index), 0, 0, 0, 10) for index in range(5)])
    intervals = report["source_group_intervals"]
    assert intervals["density"]["interval_95"] == [0, 0]
    assert intervals["precision"]["interval_95"] is None
    assert intervals["recall"]["interval_95"] is None
    assert intervals["precision"]["contributing_groups_count"] == 0
    assert report["cluster_interval"] == {
        "precision": None,
        "recall": None,
        "density": [0, 0],
    }


def test_evaluator_cannot_drop_unidentified_observations_to_claim_support(
    tmp_path,
) -> None:
    report = _report(
        tmp_path,
        [(str(index), 1, 0, 0, 10) for index in range(5)] + [(None, 1, 0, 0, 20)],
    )
    assert report["cluster_interval"] is None
    for result in report["source_group_intervals"].values():
        assert result["interval_95"] is None
        assert "unidentified" in result["unavailable_reason"]
        assert "unspecified" in result["group_counts"]
