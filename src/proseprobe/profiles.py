"""Built-in rule profiles."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

__all__ = ["PROFILES", "Profile", "profile_names_for_rule"]


@dataclass(frozen=True)
class Profile:
    """A named rule-selection policy."""

    rules: frozenset[str]
    minimum_severity: str
    min_confidence: str


_GENERAL_RULES = frozenset(
    {
        *(f"G{number:03}" for number in range(1, 10)),
        "G015",
        *(f"S{number:03}" for number in range(1, 17)),
        *(f"T{number:03}" for number in range(1, 8)),
        *(f"V{number:03}" for number in range(1, 8)),
    }
)
_ACADEMIC_RULES = frozenset({"G011", "G012", "G013", "S018", "T008"})
_BUSINESS_RULES = frozenset({"G014", "S019", "S020", "S021"})
_JOURNALISM_RULES = frozenset({"G010", "S017", "V008"})
_TECHNICAL_DOCS_RULES = frozenset(
    {
        *(f"C{number:03}" for number in range(1, 5)),
        "G016",
        "G017",
        "G019",
        "G022",
        "G024",
        "G025",
        "G029",
        "G031",
        *(f"M{number:03}" for number in range(1, 11)),
        "S022",
        "S025",
        "S028",
        "T010",
        "T012",
        "T014",
        "T015",
        "T016",
        "V009",
        "V010",
        "V011",
        "V013",
        "V014",
        "V016",
    }
)

PROFILES: Mapping[str, Profile] = MappingProxyType(
    {
        "academic": Profile(_GENERAL_RULES | _ACADEMIC_RULES, "info", "medium"),
        "business": Profile(_GENERAL_RULES | _BUSINESS_RULES, "info", "low"),
        "general": Profile(_GENERAL_RULES, "info", "medium"),
        "journalism": Profile(_GENERAL_RULES | _JOURNALISM_RULES, "info", "medium"),
        "technical-docs": Profile(
            _GENERAL_RULES | _TECHNICAL_DOCS_RULES,
            "info",
            "low",
        ),
    }
)


def profile_names_for_rule(rule_id: str) -> tuple[str, ...]:
    """Return sorted profile names containing a rule."""
    return tuple(
        sorted(name for name, profile in PROFILES.items() if rule_id in profile.rules)
    )
