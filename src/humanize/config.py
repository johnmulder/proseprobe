"""Configuration loading and merging."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PerFileIgnore:
    """Per-file rule override."""

    pattern: str
    ignore: list[str] = field(default_factory=list)


@dataclass
class VocabularyConfig:
    """Custom vocabulary settings."""

    additional: list[str] = field(default_factory=list)
    allowed: list[str] = field(default_factory=list)


@dataclass
class Config:
    """Humanize configuration."""

    include: list[str] = field(default_factory=lambda: ["*.md", "*.py"])
    exclude: list[str] = field(
        default_factory=lambda: ["venv/**", "node_modules/**", ".git/**"]
    )
    select: list[str] = field(default_factory=lambda: ["V", "S", "T", "G", "C", "M"])
    ignore: list[str] = field(default_factory=list)
    severity: str = "warning"
    severity_overrides: dict[str, str] = field(default_factory=dict)
    vocabulary: VocabularyConfig = field(default_factory=VocabularyConfig)
    per_file_ignores: list[PerFileIgnore] = field(default_factory=list)


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Find configuration file.

    Search order:
    1. .humanize.toml in current directory
    2. pyproject.toml [tool.humanize] section
    3. .humanize.toml in parent directories (up to git root)
    4. ~/.config/humanize/config.toml
    """
    if start_dir is None:
        start_dir = Path.cwd()

    # Check current and parent directories
    current = start_dir.resolve()
    while current != current.parent:
        humanize_config = current / ".humanize.toml"
        if humanize_config.exists():
            return humanize_config

        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                if "tool" in data and "humanize" in data["tool"]:
                    return pyproject

        # Stop at git root
        if (current / ".git").exists():
            break

        current = current.parent

    # Check user config
    user_config = Path.home() / ".config" / "humanize" / "config.toml"
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
        data = data.get("tool", {}).get("humanize", {})
    else:
        data = data.get("tool", {}).get("humanize", data)

    return _parse_config(data)


def _parse_config(data: dict[str, Any]) -> Config:
    """Parse configuration dictionary into Config object."""
    vocabulary_data = data.get("vocabulary", {})
    vocabulary = VocabularyConfig(
        additional=vocabulary_data.get("additional", []),
        allowed=vocabulary_data.get("allowed", []),
    )

    per_file_ignores = [
        PerFileIgnore(
            pattern=item.get("pattern", ""),
            ignore=item.get("ignore", []),
        )
        for item in data.get("per-file-ignores", [])
    ]

    return Config(
        include=data.get("include", ["*.md", "*.py"]),
        exclude=data.get("exclude", ["venv/**", "node_modules/**", ".git/**"]),
        select=data.get("select", ["V", "S", "T", "G", "C", "M"]),
        ignore=data.get("ignore", []),
        severity=data.get("severity", "warning"),
        severity_overrides=data.get("severity", {}),
        vocabulary=vocabulary,
        per_file_ignores=per_file_ignores,
    )
