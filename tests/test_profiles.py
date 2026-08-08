"""Tests for built-in rule profiles."""

from slop_lint.profiles import PROFILES, profile_names_for_rule
from slop_lint.rules import get_all_rules


def test_profile_catalog_has_expected_names_and_policy() -> None:
    assert set(PROFILES) == {
        "academic",
        "business",
        "general",
        "journalism",
        "technical-docs",
    }
    assert {
        name: (profile.minimum_severity, profile.min_confidence)
        for name, profile in PROFILES.items()
    } == {
        "academic": ("info", "medium"),
        "business": ("info", "low"),
        "general": ("info", "medium"),
        "journalism": ("info", "medium"),
        "technical-docs": ("info", "low"),
    }


def test_profiles_cover_the_registry_without_unknown_rules() -> None:
    registered = {rule.id for rule in get_all_rules()}
    profiled = set().union(*(profile.rules for profile in PROFILES.values()))

    assert all(profile.rules <= registered for profile in PROFILES.values())
    assert all(profile.rules for profile in PROFILES.values())
    assert profiled == registered


def test_profiles_include_only_their_specialized_rules() -> None:
    assert "G015" in PROFILES["general"].rules
    assert "G011" in PROFILES["academic"].rules
    assert "V008" in PROFILES["journalism"].rules
    assert "S021" in PROFILES["business"].rules
    assert "M006" in PROFILES["technical-docs"].rules
    assert "M007" in PROFILES["technical-docs"].rules
    assert "M008" in PROFILES["technical-docs"].rules

    assert "G011" not in PROFILES["journalism"].rules
    assert "V008" not in PROFILES["business"].rules
    assert "S021" not in PROFILES["academic"].rules
    assert "M006" not in PROFILES["general"].rules
    assert "M007" not in PROFILES["general"].rules
    assert "M008" not in PROFILES["general"].rules


def test_reverse_profile_tags_are_sorted() -> None:
    assert profile_names_for_rule("V001") == (
        "academic",
        "business",
        "general",
        "journalism",
        "technical-docs",
    )
    assert profile_names_for_rule("G011") == ("academic",)
    assert profile_names_for_rule("G015") == (
        "academic",
        "business",
        "general",
        "journalism",
        "technical-docs",
    )
    assert profile_names_for_rule("unknown") == ()
