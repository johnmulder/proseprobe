"""Configuration loading and merging."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "Config",
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
    """Humanize configuration."""

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

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # Handle pyproject.toml structure
    if config_path.name == "pyproject.toml":
        data = data.get("tool", {}).get("slop-lint", {})
    else:
        data = data.get("tool", {}).get("slop-lint", data)

    return _parse_config(data)


def _parse_config(data: dict[str, Any]) -> Config:
    """Parse configuration dictionary into Config object."""
    lint_data = data.get("lint", {}) if isinstance(data.get("lint"), dict) else {}
    effective: dict[str, Any] = {}

    # Support legacy [lint] configuration by overlaying with top-level keys
    effective.update(lint_data)
    for key, value in data.items():
        if key in {"lint", "format"}:
            continue
        effective[key] = value

    vocabulary_data = effective.get("vocabulary", {})
    vocabulary = VocabularyConfig(
        additional=vocabulary_data.get("additional", []),
        allowed=vocabulary_data.get("allowed", []),
        allowed_phrases=vocabulary_data.get(
            "allowed_phrases",
            ["All notable changes", "Critical issue"],
        ),
    )

    thresholds_data = effective.get("thresholds", {})
    thresholds = ThresholdsConfig(
        rule_of_three=thresholds_data.get("rule_of_three", 3),
        inline_header_lists=thresholds_data.get("inline_header_lists", 3),
        bold_overuse=thresholds_data.get("bold_overuse", 3),
        em_dash_overuse=thresholds_data.get("em_dash_overuse", 5),
        nominalization_overload=thresholds_data.get("nominalization_overload", 3),
        passive_voice_overuse=thresholds_data.get("passive_voice_overuse", 5),
        sentence_length_max=thresholds_data.get("sentence_length_max", 40),
        citation_name_drop=thresholds_data.get("citation_name_drop", 3),
        anaphora_abuse=thresholds_data.get("anaphora_abuse", 3),
        gerund_fragment_litany=thresholds_data.get("gerund_fragment_litany", 3),
        historical_analogy_stacking=thresholds_data.get(
            "historical_analogy_stacking", 3
        ),
        short_punchy_fragments=thresholds_data.get("short_punchy_fragments", 3),
        invented_concept_labels=thresholds_data.get("invented_concept_labels", 2),
    )

    per_file_raw = effective.get("per-file-ignores", [])
    per_file_ignores: list[PerFileIgnore] = []
    if isinstance(per_file_raw, dict):
        # Legacy [lint.per-file-ignores] mapping
        for pattern, ignore_list in per_file_raw.items():
            per_file_ignores.append(
                PerFileIgnore(
                    pattern=pattern,
                    ignore=list(ignore_list) if isinstance(ignore_list, list) else [],
                )
            )
    else:
        per_file_ignores = [
            PerFileIgnore(
                pattern=item.get("pattern", ""),
                ignore=item.get("ignore", []),
            )
            for item in per_file_raw
            if isinstance(item, dict)
        ]

    raw_severity = effective.get("severity", "warning")
    if isinstance(raw_severity, str):
        min_severity = raw_severity
        severity_overrides: dict[str, str] = {}
    elif isinstance(raw_severity, dict):
        min_severity = "warning"
        severity_overrides = raw_severity
    else:
        min_severity = "warning"
        severity_overrides = {}

    return Config(
        include=effective.get("include", ["*.md", "*.mdx", "*.markdown", "*.py"]),
        exclude=effective.get(
            "exclude", ["venv/**", ".venv/**", "node_modules/**", ".git/**"]
        ),
        select=effective.get("select", ["V", "S", "T", "G", "C", "M"]),
        ignore=effective.get("ignore", []),
        severity=min_severity,
        min_confidence=effective.get("min_confidence", "low"),
        severity_overrides=severity_overrides,
        vocabulary=vocabulary,
        thresholds=thresholds,
        per_file_ignores=per_file_ignores,
    )
