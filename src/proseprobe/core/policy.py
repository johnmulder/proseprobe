"""Construct scan policy without discovering configuration or applying baselines."""

from pathlib import Path

from proseprobe.config import Config, ConfigError, validate_rule_references
from proseprobe.core.linter import Linter
from proseprobe.profiles import EXPERIMENTAL_RULES, PROFILES
from proseprobe.rules import get_all_rules
from proseprobe.rules.base import (
    Confidence,
    Issue,
    Rule,
    Severity,
    severity_from_str,
    severity_rank,
)


def _split_rule_tokens(value: str) -> list[str]:
    return [token.strip().upper() for token in value.split(",") if token.strip()]


def _selection_overrides_ignore(ignored: str, selected: list[str]) -> bool:
    ignored = ignored.upper()
    return any(
        ignored == token
        or (len(ignored) == 1 and token.startswith(ignored))
        or (len(token) == 1 and ignored.startswith(token))
        for token in selected
    )


def prepare_scan(
    config: Config,
    *,
    profile: str | None = None,
    select: str | None = None,
    ignore: str | None = None,
    severity: str | None = None,
    min_confidence: str | None = None,
    hide_low: bool = False,
) -> tuple[Config, Linter, list[Rule]]:
    """Apply command overrides to explicit config and construct the scan.

    The supplied config receives the effective policy. Returned rules retain
    the CLI's severity-filtered registry; the linter applies selection and
    file-specific policy when scanning.
    """
    valid_rule_ids = {rule.id for rule in get_all_rules()}
    profiled_rule_ids = set().union(*(item.rules for item in PROFILES.values()))
    categorized_rule_ids = profiled_rule_ids | EXPERIMENTAL_RULES
    if categorized_rule_ids != valid_rule_ids or profiled_rule_ids & EXPERIMENTAL_RULES:
        unknown = sorted(categorized_rule_ids - valid_rule_ids)
        missing = sorted(valid_rule_ids - categorized_rule_ids)
        raise ConfigError(
            Path("<profiles>"),
            f"profile catalog mismatch (unknown={unknown}, untagged={missing})",
        )
    validate_rule_references(config, valid_rule_ids)
    if profile is not None:
        selected_profile = PROFILES[profile]
        config.profile = profile
        config.select = sorted(selected_profile.rules)
        config.severity = selected_profile.minimum_severity
        config.min_confidence = selected_profile.min_confidence
    if select:
        selected = _split_rule_tokens(select)
        config.select = selected
        config.ignore = [
            ignored
            for ignored in config.ignore
            if not _selection_overrides_ignore(ignored, selected)
        ]
    if ignore:
        existing = {ignored.upper() for ignored in config.ignore}
        for ignored in _split_rule_tokens(ignore):
            if ignored not in existing:
                config.ignore.append(ignored)
                existing.add(ignored)
    if profile or select or ignore:
        validate_rule_references(config, valid_rule_ids, Path("<command line>"))

    config.severity = severity or config.severity
    config.min_confidence = min_confidence or (
        "medium" if hide_low else config.min_confidence
    )
    minimum = severity_from_str(config.severity, Severity.WARNING) or Severity.WARNING
    rules = [
        rule
        for rule in get_all_rules(config)
        if severity_rank(rule.severity) >= severity_rank(minimum)
    ]
    linter = Linter(config, valid_rule_ids=valid_rule_ids)
    for rule in rules:
        linter.register_rule(rule)
    return config, linter, rules


def filter_by_confidence(
    results: dict[Path, list[Issue]], minimum: str
) -> dict[Path, list[Issue]]:
    """Apply the CLI confidence threshold to emitted issues."""
    ranks = {
        Confidence.LOW.value: 0,
        Confidence.MEDIUM.value: 1,
        Confidence.HIGH.value: 2,
    }
    threshold = ranks.get(minimum.lower(), 0)
    if threshold == 0:
        return results
    filtered = {
        path: [issue for issue in issues if ranks.get(issue.confidence, 0) >= threshold]
        for path, issues in results.items()
    }
    return {path: issues for path, issues in filtered.items() if issues}
