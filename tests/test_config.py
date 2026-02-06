"""Tests for configuration loading."""

import tomllib
from pathlib import Path

import pytest

from slop_lint.config import (
    Config,
    ThresholdsConfig,
    VocabularyConfig,
    find_config_file,
    load_config,
)


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_finds_slop_lint_toml(self, tmp_path: Path) -> None:
        """Test finding .slop-lint.toml file."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("[lint]")

        result = find_config_file(tmp_path)

        assert result == config_file

    def test_finds_pyproject_toml(self, tmp_path: Path) -> None:
        """Test finding pyproject.toml with slop-lint config."""
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("[tool.slop-lint]\nrules = {}")

        result = find_config_file(tmp_path)

        assert result == config_file

    def test_prefers_slop_lint_toml(self, tmp_path: Path) -> None:
        """Test that .slop-lint.toml is preferred over pyproject.toml."""
        slop_lint_toml = tmp_path / ".slop-lint.toml"
        slop_lint_toml.write_text("[lint]")

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.slop-lint]")

        result = find_config_file(tmp_path)

        assert result == slop_lint_toml

    def test_returns_none_if_not_found(self, tmp_path: Path) -> None:
        """Test returns None when no config file exists."""
        # Create a .git to stop search
        (tmp_path / ".git").mkdir()

        result = find_config_file(tmp_path)

        assert result is None

    def test_ignores_pyproject_without_slop_lint(self, tmp_path: Path) -> None:
        """Test ignores pyproject.toml without [tool.slop-lint]."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test'")
        # Create a .git to stop search
        (tmp_path / ".git").mkdir()

        result = find_config_file(tmp_path)

        assert result is None

    def test_searches_parent_directories(self, tmp_path: Path) -> None:
        """Test that config is found in parent directories."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("[lint]")

        subdir = tmp_path / "subdir" / "deep"
        subdir.mkdir(parents=True)

        result = find_config_file(subdir)

        assert result == config_file


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_slop_lint_toml(self, tmp_path: Path, monkeypatch) -> None:
        """Test loading .slop-lint.toml."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("""
select = ["V001", "V002"]
ignore = ["S001"]
severity = "warning"
""")

        config = load_config(config_file)

        assert isinstance(config, Config)
        assert config.select == ["V001", "V002"]
        assert config.ignore == ["S001"]

    def test_load_pyproject_toml(self, tmp_path: Path) -> None:
        """Test loading pyproject.toml."""
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("""
[project]
name = "test"

[tool.slop-lint]
select = ["G001"]
""")

        config = load_config(config_file)

        assert isinstance(config, Config)
        assert config.select == ["G001"]

    def test_load_no_config(self, tmp_path: Path, monkeypatch) -> None:
        """Test loading with no config returns defaults."""
        monkeypatch.chdir(tmp_path)
        # Create .git to stop search
        (tmp_path / ".git").mkdir()

        config = load_config(None)

        assert isinstance(config, Config)
        assert config.severity == "warning"

    def test_load_config_with_vocabulary(self, tmp_path: Path) -> None:
        """Test loading custom vocabulary config."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("""
[vocabulary]
additional = ["synergy", "leverage"]
allowed = ["delve"]
""")

        config = load_config(config_file)

        assert isinstance(config, Config)
        assert config.vocabulary.additional == ["synergy", "leverage"]
        assert config.vocabulary.allowed == ["delve"]

    def test_load_legacy_lint_section(self, tmp_path: Path) -> None:
        """Test loading legacy [lint] config shape."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("""
[lint]
select = ["V001"]
ignore = ["S001"]
severity = "error"

[lint.per-file-ignores]
"CHANGELOG.md" = ["V001"]
""")

        config = load_config(config_file)

        assert config.select == ["V001"]
        assert config.ignore == ["S001"]
        assert config.severity == "error"
        assert len(config.per_file_ignores) == 1
        assert config.per_file_ignores[0].pattern == "CHANGELOG.md"

    def test_load_severity_overrides_table(self, tmp_path: Path) -> None:
        """Test parsing severity overrides table."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("""
[tool.slop-lint]
select = ["V"]

[tool.slop-lint.severity]
V001 = "error"
""")

        config = load_config(config_file)

        assert config.severity == "warning"
        assert config.severity_overrides["V001"] == "error"

    def test_load_invalid_toml(self, tmp_path: Path) -> None:
        """Test loading invalid TOML raises error."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("invalid [ toml ][")

        with pytest.raises(tomllib.TOMLDecodeError):
            load_config(config_file)


class TestConfig:
    """Tests for Config class."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = Config()

        assert config.select == ["V", "S", "T", "G", "C", "M"]
        assert config.ignore == []
        assert config.severity == "warning"
        assert ".venv/**" in config.exclude

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = Config(
            select=["V001", "V002"],
            ignore=["S001"],
            severity="error",
        )

        assert config.select == ["V001", "V002"]
        assert config.ignore == ["S001"]
        assert config.severity == "error"

    def test_default_thresholds(self) -> None:
        """Test default threshold values."""
        config = Config()

        assert config.thresholds.rule_of_three == 3
        assert config.thresholds.inline_header_lists == 3
        assert config.thresholds.bold_overuse == 3
        assert config.thresholds.em_dash_overuse == 5

    def test_load_thresholds_config(self, tmp_path: Path) -> None:
        """Test loading custom thresholds from config file."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("""
[thresholds]
rule_of_three = 5
inline_header_lists = 4
bold_overuse = 2
em_dash_overuse = 10
""")

        config = load_config(config_file)

        assert config.thresholds.rule_of_three == 5
        assert config.thresholds.inline_header_lists == 4
        assert config.thresholds.bold_overuse == 2
        assert config.thresholds.em_dash_overuse == 10

    def test_partial_thresholds_config(self, tmp_path: Path) -> None:
        """Test loading partial thresholds uses defaults for missing values."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("""
[thresholds]
rule_of_three = 10
""")

        config = load_config(config_file)

        assert config.thresholds.rule_of_three == 10
        assert config.thresholds.inline_header_lists == 3  # default
        assert config.thresholds.bold_overuse == 3  # default
        assert config.thresholds.em_dash_overuse == 5  # default


class TestThresholdsConfig:
    """Tests for ThresholdsConfig class."""

    def test_default_values(self) -> None:
        """Test default threshold values."""
        thresholds = ThresholdsConfig()

        assert thresholds.rule_of_three == 3
        assert thresholds.inline_header_lists == 3
        assert thresholds.bold_overuse == 3
        assert thresholds.em_dash_overuse == 5

    def test_custom_values(self) -> None:
        """Test custom threshold values."""
        thresholds = ThresholdsConfig(
            rule_of_three=10,
            inline_header_lists=5,
            bold_overuse=4,
            em_dash_overuse=8,
        )

        assert thresholds.rule_of_three == 10
        assert thresholds.inline_header_lists == 5
        assert thresholds.bold_overuse == 4
        assert thresholds.em_dash_overuse == 8


class TestVocabularyConfig:
    """Tests for VocabularyConfig class."""

    def test_default_allowed_phrases(self) -> None:
        vocab = VocabularyConfig()
        assert "All notable changes" in vocab.allowed_phrases
        assert "Critical issue" in vocab.allowed_phrases

    def test_custom_allowed_phrases(self) -> None:
        vocab = VocabularyConfig(allowed_phrases=["my custom phrase"])
        assert vocab.allowed_phrases == ["my custom phrase"]


class TestMinConfidenceConfig:
    """Tests for min_confidence config option."""

    def test_default_min_confidence(self) -> None:
        config = Config()
        assert config.min_confidence == "low"

    def test_load_min_confidence_from_toml(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text(
            '[tool.slop-lint]\nmin_confidence = "medium"\n'
        )
        config = load_config(config_file)
        assert config.min_confidence == "medium"
