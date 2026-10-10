"""Conditional percentile intervals from complete identified source groups."""

from __future__ import annotations

import random
from typing import Any

SEED = 20261010
REPLICATES = 2000
MINIMUM_GROUPS = 5


def _percentile(values: list[float], fraction: float) -> float:
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def source_group_interval(
    groups: dict[str, tuple[int, int]], *, scale: float = 1.0
) -> dict[str, Any]:
    """Resample whole groups uniformly and estimate a ratio of summed counts."""
    if scale <= 0 or any(
        not isinstance(name, str)
        or not name.strip()
        or len(counts) != 2
        or any(type(value) is not int or value < 0 for value in counts)
        for name, counts in groups.items()
    ):
        raise ValueError(
            "source group counts must have nonnegative integer numerator/denominator and positive scale"
        )
    ordered = dict(sorted(groups.items()))
    numerator = sum(counts[0] for counts in ordered.values())
    denominator = sum(counts[1] for counts in ordered.values())
    contributing = [
        counts
        for name, counts in ordered.items()
        if name != "unspecified" and counts[1] > 0
    ]
    reason = None
    if denominator == 0:
        reason = "no eligible denominator observations"
    elif any(counts[0] and not counts[1] for counts in ordered.values()):
        reason = (
            "a source group has numerator observations without an eligible denominator"
        )
    elif ordered.get("unspecified", (0, 0))[1]:
        reason = (
            "unidentified contributing source groups cannot support a group interval"
        )
    elif len(contributing) < MINIMUM_GROUPS:
        reason = f"too few contributing source groups ({len(contributing)} < {MINIMUM_GROUPS})"
    interval = None
    if reason is None:
        rng = random.Random(SEED)  # noqa: S311 - reproducible statistical resampling
        samples = []
        for _ in range(REPLICATES):
            selected = rng.choices(contributing, k=len(contributing))
            samples.append(
                scale
                * sum(value[0] for value in selected)
                / sum(value[1] for value in selected)
            )
        samples.sort()
        interval = [_percentile(samples, 0.025), _percentile(samples, 0.975)]
    return {
        "method": "whole-source-group percentile bootstrap; ratio of summed counts",
        "seed": SEED,
        "replicates": REPLICATES,
        "minimum_contributing_groups": MINIMUM_GROUPS,
        "confidence_level": 0.95,
        "scope": "conditional on observed identified pilot source groups; no representative-population proof",
        "point_estimate": scale * numerator / denominator if denominator else None,
        "interval_95": interval,
        "unavailable_reason": reason,
        "contributing_groups_count": len(contributing),
        "group_counts": {
            name: {"numerator": counts[0], "denominator": counts[1]}
            for name, counts in ordered.items()
        },
        "dominant_denominator_share": max(
            (value[1] for value in ordered.values()), default=0
        )
        / denominator
        if denominator
        else None,
    }
