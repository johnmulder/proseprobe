"""Tests for canonical rule metadata."""

from dataclasses import FrozenInstanceError, fields

import pytest

from proseprobe.config import Config, ThresholdsConfig
from proseprobe.profiles import profile_names_for_rule
from proseprobe.rules import (
    get_all_rules,
    get_rule_metadata,
    get_rule_metadata_by_id,
)
from proseprobe.rules.base import Confidence, Severity


def test_metadata_covers_registry_in_rule_id_order() -> None:
    metadata = get_rule_metadata()
    metadata_ids = tuple(item.id for item in metadata)

    assert metadata_ids == tuple(rule.id for rule in get_all_rules())
    assert len(metadata) == 76
    assert len(set(metadata_ids)) == len(metadata_ids)


def test_metadata_is_immutable_and_complete() -> None:
    metadata = get_rule_metadata_by_id("s001")

    assert metadata is not None
    assert metadata.name == "Rule of Three"
    assert metadata.category == "Structure"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.MEDIUM
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == profile_names_for_rule("S001")
    assert metadata.config_key == "thresholds.rule_of_three"
    with pytest.raises(FrozenInstanceError):
        metadata.name = "changed"  # type: ignore[misc]


def test_metadata_reports_low_confidence_rule_defaults() -> None:
    assert get_rule_metadata_by_id("M001").default_confidence is Confidence.LOW  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("S021").default_confidence is Confidence.LOW  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("V001").default_confidence is Confidence.MEDIUM  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("M005").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("M006").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("M007").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("M008").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("M009").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("M010").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("S025").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("V009").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("V010").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("V011").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("V013").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("V016").default_confidence is Confidence.MEDIUM  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("G015").default_confidence is Confidence.MEDIUM  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("G017").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("G024").default_confidence is Confidence.MEDIUM  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("G029").default_confidence is Confidence.HIGH  # type: ignore[union-attr]
    assert get_rule_metadata_by_id("T015").default_confidence is Confidence.HIGH  # type: ignore[union-attr]


def test_metadata_config_keys_match_threshold_fields() -> None:
    threshold_fields = {field.name for field in fields(ThresholdsConfig)}
    configured = {
        item.config_key.removeprefix("thresholds.")
        for item in get_rule_metadata()
        if item.config_key is not None
    }

    assert configured == threshold_fields


def test_metadata_keeps_default_severity_when_runtime_config_overrides_it() -> None:
    configured = get_all_rules(Config(severity_overrides={"V001": "error"}))
    configured_v001 = next(rule for rule in configured if rule.id == "V001")

    assert configured_v001.severity is Severity.ERROR
    assert get_rule_metadata_by_id("V001").default_severity is Severity.WARNING  # type: ignore[union-attr]


def test_metadata_lookup_rejects_unknown_rule() -> None:
    assert get_rule_metadata_by_id("X999") is None


def test_m009_metadata_matches_the_bare_url_contract() -> None:
    metadata = get_rule_metadata_by_id("M009")

    assert metadata is not None
    assert metadata.name == "Bare URL in Prose"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.HIGH
    assert metadata.applies_to == ("markdown",)
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_m010_metadata_matches_the_link_text_contract() -> None:
    metadata = get_rule_metadata_by_id("M010")

    assert metadata is not None
    assert metadata.name == "Non-Descriptive Link Text"
    assert metadata.default_severity is Severity.WARNING
    assert metadata.applies_to == ("markdown",)
    assert metadata.content_scope == "non_code"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_s025_metadata_matches_the_empty_heading_contract() -> None:
    metadata = get_rule_metadata_by_id("S025")

    assert metadata is not None
    assert metadata.name == "Heading Without Body"
    assert metadata.default_severity is Severity.WARNING
    assert metadata.default_confidence is Confidence.HIGH
    assert metadata.applies_to == ("markdown",)
    assert metadata.content_scope == "raw"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_v009_metadata_matches_the_wordy_phrase_contract() -> None:
    metadata = get_rule_metadata_by_id("V009")

    assert metadata is not None
    assert metadata.name == "Wordy Phrase"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.HIGH
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_v010_metadata_matches_the_redundant_pair_contract() -> None:
    metadata = get_rule_metadata_by_id("V010")

    assert metadata is not None
    assert metadata.name == "Redundant Pair"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.HIGH
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_v011_metadata_matches_the_verbose_verb_contract() -> None:
    metadata = get_rule_metadata_by_id("V011")

    assert metadata is not None
    assert metadata.name == "Verbose Verb Phrase"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.HIGH
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_v013_metadata_matches_the_redundant_modifier_contract() -> None:
    metadata = get_rule_metadata_by_id("V013")

    assert metadata is not None
    assert metadata.name == "Redundant Modifier"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.HIGH
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_v016_metadata_matches_the_reliability_claim_contract() -> None:
    metadata = get_rule_metadata_by_id("V016")

    assert metadata is not None
    assert metadata.name == "Absolute Reliability Claim"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.MEDIUM
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_g029_metadata_matches_the_double_negative_contract() -> None:
    metadata = get_rule_metadata_by_id("G029")

    assert metadata is not None
    assert metadata.name == "Double Negative"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.HIGH
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_g017_metadata_matches_the_empty_it_opener_contract() -> None:
    metadata = get_rule_metadata_by_id("G017")

    assert metadata is not None
    assert metadata.name == 'Empty "It" Opener'
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.HIGH
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_g024_metadata_matches_the_unclear_actor_contract() -> None:
    metadata = get_rule_metadata_by_id("G024")

    assert metadata is not None
    assert metadata.name == "Unclear Actor in Requirement"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.MEDIUM
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None


def test_t015_metadata_matches_the_nested_parenthetical_contract() -> None:
    metadata = get_rule_metadata_by_id("T015")

    assert metadata is not None
    assert metadata.name == "Nested Parenthetical"
    assert metadata.default_severity is Severity.INFO
    assert metadata.default_confidence is Confidence.HIGH
    assert metadata.applies_to == ("markdown", "python")
    assert metadata.content_scope == "prose"
    assert metadata.profiles == ("technical-docs",)
    assert metadata.config_key is None
