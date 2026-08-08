"""Tests for built-in rule profiles."""

from proseprobe.profiles import PROFILES, profile_names_for_rule
from proseprobe.rules import get_all_rules


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
    assert "G017" in PROFILES["technical-docs"].rules
    assert "G024" in PROFILES["technical-docs"].rules
    assert "G029" in PROFILES["technical-docs"].rules
    assert "G011" in PROFILES["academic"].rules
    assert "V008" in PROFILES["journalism"].rules
    assert "S021" in PROFILES["business"].rules
    assert "M006" in PROFILES["technical-docs"].rules
    assert "M007" in PROFILES["technical-docs"].rules
    assert "M008" in PROFILES["technical-docs"].rules
    assert "M009" in PROFILES["technical-docs"].rules
    assert "M010" in PROFILES["technical-docs"].rules
    assert "S025" in PROFILES["technical-docs"].rules
    assert "T015" in PROFILES["technical-docs"].rules
    assert "V009" in PROFILES["technical-docs"].rules
    assert "V010" in PROFILES["technical-docs"].rules
    assert "V016" in PROFILES["technical-docs"].rules

    assert "G011" not in PROFILES["journalism"].rules
    assert "G017" not in PROFILES["general"].rules
    assert "G024" not in PROFILES["general"].rules
    assert "G029" not in PROFILES["general"].rules
    assert "V008" not in PROFILES["business"].rules
    assert "S021" not in PROFILES["academic"].rules
    assert "M006" not in PROFILES["general"].rules
    assert "M007" not in PROFILES["general"].rules
    assert "M008" not in PROFILES["general"].rules
    assert "M009" not in PROFILES["general"].rules
    assert "M010" not in PROFILES["general"].rules
    assert "S025" not in PROFILES["general"].rules
    assert "T015" not in PROFILES["general"].rules
    assert "V009" not in PROFILES["general"].rules
    assert "V010" not in PROFILES["general"].rules
    assert "V016" not in PROFILES["general"].rules


def test_reverse_profile_tags_are_sorted() -> None:
    assert profile_names_for_rule("V001") == (
        "academic",
        "business",
        "general",
        "journalism",
        "technical-docs",
    )
    assert profile_names_for_rule("G011") == ("academic",)
    assert profile_names_for_rule("G017") == ("technical-docs",)
    assert profile_names_for_rule("G024") == ("technical-docs",)
    assert profile_names_for_rule("G029") == ("technical-docs",)
    assert profile_names_for_rule("M009") == ("technical-docs",)
    assert profile_names_for_rule("M010") == ("technical-docs",)
    assert profile_names_for_rule("S025") == ("technical-docs",)
    assert profile_names_for_rule("T015") == ("technical-docs",)
    assert profile_names_for_rule("V009") == ("technical-docs",)
    assert profile_names_for_rule("V010") == ("technical-docs",)
    assert profile_names_for_rule("V016") == ("technical-docs",)
    assert profile_names_for_rule("G015") == (
        "academic",
        "business",
        "general",
        "journalism",
        "technical-docs",
    )
    assert profile_names_for_rule("unknown") == ()
