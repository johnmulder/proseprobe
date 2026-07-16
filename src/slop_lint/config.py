"""Configuration loading and merging."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "Config",
    "ConfigError",
    "PerFileIgnore",
    "ThresholdsConfig",
    "VocabularyConfig",
    "find_config_file",
    "load_config",
]


@dataclass
class PerFileIgnore:
    """Per-file rule override."""

    pattern: str
    ignore: list[str] = field(default_factory=list)


@dataclass
class ThresholdsConfig:
    """Configurable detection thresholds.

    These control when rules trigger based on counts/occurrences.
    """

    # S001: RuleOfThreeRule - flag if more than N triads in content
    rule_of_three: int = 3
    # S004: InlineHeaderListsRule - flag if >= N consecutive inline headers
    inline_header_lists: int = 3
    # T002: BoldOveruseRule - max bold phrases per paragraph
    bold_overuse: int = 3
    # T003: EmDashOveruseRule - max em dashes per document
    em_dash_overuse: int = 5
    # G011: NominalizationOverloadRule - flag if >= N nominalizations
    nominalization_overload: int = 3
    # G012: PassiveVoiceOveruseRule - flag if >= N formulaic passives
    passive_voice_overuse: int = 5
    # T008: SentenceLengthRule - max words per sentence
    sentence_length_max: int = 40
    # S018: CitationNameDroppingRule - flag if >= N consecutive citations
    citation_name_drop: int = 3
    # S010: AnaphoraAbuseRule - flag if >= N repeated sentence openings
    anaphora_abuse: int = 3
    # S011: GerundFragmentLitanyRule - flag if >= N consecutive gerund fragments
    gerund_fragment_litany: int = 3
    # S013: HistoricalAnalogyStackingRule - flag if >= N company name-drops
    historical_analogy_stacking: int = 3
    # T007: ShortPunchyFragmentsRule - flag if >= N consecutive short paragraphs
    short_punchy_fragments: int = 3
    # V007: InventedConceptLabelsRule - flag if >= N pseudo-analytical labels
    invented_concept_labels: int = 2


@dataclass
class VocabularyConfig:
    """Custom vocabulary settings."""

    additional: list[str] = field(default_factory=list)
    allowed: list[str] = field(default_factory=list)
    allowed_phrases: list[str] = field(
        default_factory=lambda: [
            "All notable changes",
            "Critical issue",
        ]
    )


@dataclass
class Config:
    """slop-lint configuration."""

    include: list[str] = field(
        default_factory=lambda: ["*.md", "*.mdx", "*.markdown", "*.py"]
    )
    exclude: list[str] = field(
        default_factory=lambda: [
            "venv/**",
            ".venv/**",
            "node_modules/**",
            ".git/**",
        ]
    )
    select: list[str] = field(default_factory=lambda: ["V", "S", "T", "G", "C", "M"])
    ignore: list[str] = field(default_factory=list)
    severity: str = "warning"
    min_confidence: str = "low"
    severity_overrides: dict[str, str] = field(default_factory=dict)
    vocabulary: VocabularyConfig = field(default_factory=VocabularyConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    per_file_ignores: list[PerFileIgnore] = field(default_factory=list)


class ConfigError(ValueError):
    """Raised when configuration cannot be loaded or parsed."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Find configuration file.

    Search order:
    1. .slop-lint.toml in current directory
    2. pyproject.toml [tool.slop-lint] section
    3. .slop-lint.toml in parent directories (up to git root)
    4. ~/.config/slop-lint/config.toml
    """
    if start_dir is None:
        start_dir = Path.cwd()

    current = start_dir.resolve()

    # 1) Current directory .slop-lint.toml
    slop_lint_config = current / ".slop-lint.toml"
    if slop_lint_config.exists():
        return slop_lint_config

    # 2) Current directory pyproject.toml [tool.slop-lint]
    pyproject = current / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
            if "tool" in data and "slop-lint" in data["tool"]:
                return pyproject

    # 3) Parent directories .slop-lint.toml (up to git root)
    parent = current.parent
    while parent != parent.parent:
        parent_config = parent / ".slop-lint.toml"
        if parent_config.exists():
            return parent_config

        if (parent / ".git").exists():
            break

        parent = parent.parent

    # Check user config
    user_config = Path.home() / ".config" / "slop-lint" / "config.toml"
    if user_config.exists():
        return user_config

    return None


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from file.

    Args:
        config_path: Explicit path to config file, or None to auto-detect.

    Returns:
        Merged configuration.
    """
    if config_path is None:
        config_path = find_config_file()

    if config_path is None:
        return Config()

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except OSError as exc:
        raise ConfigError(config_path, str(exc)) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(config_path, str(exc)) from exc

    # Handle pyproject.toml structure
    if config_path.name == "pyproject.toml":
        data = data.get("tool", {}).get("slop-lint", {})
    else:
        data = data.get("tool", {}).get("slop-lint", data)

    try:
        return _parse_config(data)
    except ValueError as exc:
        raise ConfigError(config_path, str(exc)) from exc


def _require_list(value: Any, key: str) -> list[str]:
    """Require a value to be a list of strings."""
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list of strings")

    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{key} must be a list of strings")
        items.append(item)
    return items


def _require_mapping(value: Any, key: str) -> dict[str, Any]:
    """Require a value to be a mapping with string keys."""
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a table")

    items: dict[str, Any] = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str):
            raise ValueError(f"{key} must use string keys")
        items[item_key] = item_value
    return items


def _require_choice(value: Any, key: str, choices: set[str]) -> str:
    """Require a string value to be one of a fixed set of choices."""
    if not isinstance(value, str):
        allowed = ", ".join(sorted(choices))
        raise ValueError(f"{key} must be one of: {allowed}")

    normalized = value.lower()
    if normalized not in choices:
        allowed = ", ".join(sorted(choices))
        raise ValueError(f"{key} must be one of: {allowed}")
    return normalized


def _require_int(value: Any, key: str) -> int:
    """Require a value to be an integer."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value


def _require_choice_mapping(
    value: Any,
    key: str,
    choices: set[str],
) -> dict[str, str]:
    """Require a string-to-choice mapping."""
    raw_mapping = _require_mapping(value, key)
    return {
        item_key: _require_choice(item_value, f"{key}.{item_key}", choices)
        for item_key, item_value in raw_mapping.items()
    }


def _parse_per_file_ignores(value: Any) -> list[PerFileIgnore]:
    """Parse per-file ignore configuration."""
    per_file_ignores: list[PerFileIgnore] = []
    if not isinstance(value, list):
        raise ValueError("per-file-ignores must be a list of tables")

    for index, item in enumerate(value):
        item_data = _require_mapping(item, f"per-file-ignores[{index}]")
        pattern = item_data.get("pattern", "")
        if not isinstance(pattern, str):
            raise ValueError("per-file-ignores.pattern must be a string")
        per_file_ignores.append(
            PerFileIgnore(
                pattern=pattern,
                ignore=_require_list(
                    item_data.get("ignore", []), f"per-file-ignores[{index}].ignore"
                ),
            )
        )
    return per_file_ignores


def _parse_config(data: dict[str, Any]) -> Config:
    """Parse configuration dictionary into Config object."""
    vocabulary_data = _require_mapping(data.get("vocabulary", {}), "vocabulary")
    vocabulary = VocabularyConfig(
        additional=_require_list(vocabulary_data.get("additional", []), "additional"),
        allowed=_require_list(vocabulary_data.get("allowed", []), "allowed"),
        allowed_phrases=_require_list(
            vocabulary_data.get(
                "allowed_phrases",
                ["All notable changes", "Critical issue"],
            ),
            "allowed_phrases",
        ),
    )

    thresholds_data = _require_mapping(data.get("thresholds", {}), "thresholds")
    thresholds = ThresholdsConfig(
        rule_of_three=_require_int(
            thresholds_data.get("rule_of_three", 3), "thresholds.rule_of_three"
        ),
        inline_header_lists=_require_int(
            thresholds_data.get("inline_header_lists", 3),
            "thresholds.inline_header_lists",
        ),
        bold_overuse=_require_int(
            thresholds_data.get("bold_overuse", 3), "thresholds.bold_overuse"
        ),
        em_dash_overuse=_require_int(
            thresholds_data.get("em_dash_overuse", 5), "thresholds.em_dash_overuse"
        ),
        nominalization_overload=_require_int(
            thresholds_data.get("nominalization_overload", 3),
            "thresholds.nominalization_overload",
        ),
        passive_voice_overuse=_require_int(
            thresholds_data.get("passive_voice_overuse", 5),
            "thresholds.passive_voice_overuse",
        ),
        sentence_length_max=_require_int(
            thresholds_data.get("sentence_length_max", 40),
            "thresholds.sentence_length_max",
        ),
        citation_name_drop=_require_int(
            thresholds_data.get("citation_name_drop", 3),
            "thresholds.citation_name_drop",
        ),
        anaphora_abuse=_require_int(
            thresholds_data.get("anaphora_abuse", 3), "thresholds.anaphora_abuse"
        ),
        gerund_fragment_litany=_require_int(
            thresholds_data.get("gerund_fragment_litany", 3),
            "thresholds.gerund_fragment_litany",
        ),
        historical_analogy_stacking=_require_int(
            thresholds_data.get("historical_analogy_stacking", 3),
            "thresholds.historical_analogy_stacking",
        ),
        short_punchy_fragments=_require_int(
            thresholds_data.get("short_punchy_fragments", 3),
            "thresholds.short_punchy_fragments",
        ),
        invented_concept_labels=_require_int(
            thresholds_data.get("invented_concept_labels", 2),
            "thresholds.invented_concept_labels",
        ),
    )

    per_file_ignores = _parse_per_file_ignores(data.get("per-file-ignores", []))

    raw_severity = data.get("severity", "warning")
    if isinstance(raw_severity, str):
        min_severity = _require_choice(
            raw_severity, "severity", {"error", "info", "warning"}
        )
        severity_overrides: dict[str, str] = {}
    elif isinstance(raw_severity, dict):
        min_severity = "warning"
        severity_overrides = _require_choice_mapping(
            raw_severity, "severity", {"error", "info", "off", "warning"}
        )
    else:
        raise ValueError("severity must be a string or table")

    return Config(
        include=_require_list(
            data.get("include", ["*.md", "*.mdx", "*.markdown", "*.py"]),
            "include",
        ),
        exclude=_require_list(
            data.get("exclude", ["venv/**", ".venv/**", "node_modules/**", ".git/**"]),
            "exclude",
        ),
        select=_require_list(
            data.get("select", ["V", "S", "T", "G", "C", "M"]), "select"
        ),
        ignore=_require_list(data.get("ignore", []), "ignore"),
        severity=min_severity,
        min_confidence=_require_choice(
            data.get("min_confidence", "low"),
            "min_confidence",
            {"high", "low", "medium"},
        ),
        severity_overrides=severity_overrides,
        vocabulary=vocabulary,
        thresholds=thresholds,
        per_file_ignores=per_file_ignores,
    )
