"""Tests for the core linter module."""

from pathlib import Path

from slop_lint.config import Config, PerFileIgnore
from slop_lint.core.linter import Linter
from slop_lint.rules import get_all_rules
from slop_lint.rules.vocab import AIVocabularyRule


class TestLinter:
    """Tests for the Linter class."""

    def test_linter_creation(self) -> None:
        """Test creating a linter instance."""
        config = Config()
        linter = Linter(config)
        assert linter is not None

    def test_linter_with_ignore(self) -> None:
        """Test creating a linter with ignore config."""
        config = Config(ignore=["V001"])
        linter = Linter(config)
        assert linter.config.ignore == ["V001"]


class TestDiscoverFiles:
    """Tests for file discovery."""

    def test_discover_single_file(self, tmp_path: Path) -> None:
        """Test discovering a single file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("content")

        config = Config()
        linter = Linter(config)
        files = linter.discover_files([test_file])

        assert len(files) == 1
        assert files[0] == test_file

    def test_discover_directory(self, tmp_path: Path) -> None:
        """Test discovering files in a directory."""
        (tmp_path / "doc1.md").write_text("content")
        (tmp_path / "doc2.md").write_text("content")
        (tmp_path / "script.py").write_text("# content")

        config = Config()
        linter = Linter(config)
        files = linter.discover_files([tmp_path])

        assert len(files) >= 2

    def test_discover_nested_directory(self, tmp_path: Path) -> None:
        """Test discovering files in nested directories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "root.md").write_text("content")
        (subdir / "nested.md").write_text("content")

        config = Config()
        linter = Linter(config)
        files = linter.discover_files([tmp_path])

        assert len(files) >= 2

    def test_discover_excludes_venv(self, tmp_path: Path) -> None:
        """Test that venv directory is excluded."""
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        (tmp_path / "good.md").write_text("content")
        (venv_dir / "bad.md").write_text("content")

        config = Config(exclude=["venv/**"])
        linter = Linter(config)
        files = linter.discover_files([tmp_path])

        # Should only find good.md, not the one in venv
        assert len(files) == 1
        # Check filename (pytest tmp_path may contain "venv" in directory name)
        assert files[0].name == "good.md"

    def test_discover_excludes_dot_venv(self, tmp_path: Path) -> None:
        """Test that .venv directory is excluded."""
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (tmp_path / "good.md").write_text("content")
        (venv_dir / "bad.md").write_text("content")

        config = Config(exclude=[".venv/**"])
        linter = Linter(config)
        files = linter.discover_files([tmp_path])

        assert len(files) == 1
        assert files[0].name == "good.md"

    def test_discover_excludes_node_modules(self, tmp_path: Path) -> None:
        """Test that node_modules directory is excluded."""
        node_dir = tmp_path / "node_modules"
        node_dir.mkdir()
        (tmp_path / "good.md").write_text("content")
        (node_dir / "package.md").write_text("content")

        config = Config(exclude=["node_modules/**"])
        linter = Linter(config)
        files = linter.discover_files([tmp_path])

        assert len(files) == 1
        assert all("node_modules" not in str(f) for f in files)


class TestPerFileIgnores:
    """Tests for per-file rule ignores."""

    def test_per_file_ignore_disables_rule(self, tmp_path: Path) -> None:
        """Test that per-file ignores disable rules for specific files."""
        config = Config(
            per_file_ignores=[PerFileIgnore(pattern="CHANGELOG.md", ignore=["V001"])]
        )
        linter = Linter(config)
        rule = AIVocabularyRule()

        # V001 should be disabled for CHANGELOG.md
        assert not linter._rule_enabled(rule, Path("CHANGELOG.md"))
        # V001 should be enabled for other files
        assert linter._rule_enabled(rule, Path("README.md"))

    def test_per_file_ignore_by_category(self, tmp_path: Path) -> None:
        """Test that per-file ignores work with category prefixes."""
        config = Config(
            per_file_ignores=[PerFileIgnore(pattern="*.test.md", ignore=["V"])]
        )
        linter = Linter(config)
        rule = AIVocabularyRule()

        # All V rules should be disabled for test files
        assert not linter._rule_enabled(rule, Path("example.test.md"))
        # V rules should be enabled for non-test files
        assert linter._rule_enabled(rule, Path("example.md"))


class TestCheckFile:
    """Tests for file checking."""

    def test_check_clean_markdown(self, tmp_path: Path) -> None:
        """Test checking clean markdown file."""
        test_file = tmp_path / "clean.md"
        test_file.write_text("This is normal human-written content.")

        config = Config()
        linter = Linter(config)
        # Register rules
        for rule in get_all_rules():
            linter.register_rule(rule)
        issues = linter.check_file(test_file)

        # May or may not have issues, just verify it works
        assert isinstance(issues, list)

    def test_check_markdown_with_vocabulary(self, tmp_path: Path) -> None:
        """Test checking markdown file with AI vocabulary."""
        test_file = tmp_path / "ai.md"
        test_file.write_text("This article delves into the topic deeply.")

        config = Config()
        linter = Linter(config)
        for rule in get_all_rules():
            linter.register_rule(rule)
        issues = linter.check_file(test_file)

        assert len(issues) > 0
        rule_ids = [issue.rule_id for issue in issues]
        assert "V001" in rule_ids

    def test_check_python_file(self, tmp_path: Path) -> None:
        """Test checking Python file."""
        test_file = tmp_path / "script.py"
        test_file.write_text('"""This module will delve into algorithms."""')

        config = Config()
        linter = Linter(config)
        for rule in get_all_rules():
            linter.register_rule(rule)
        issues = linter.check_file(test_file)

        assert len(issues) > 0


class TestCheck:
    """Tests for checking paths."""

    def test_check_paths(self, tmp_path: Path) -> None:
        """Test checking multiple paths."""
        file1 = tmp_path / "doc1.md"
        file2 = tmp_path / "doc2.md"
        file1.write_text("This delves deep.")
        file2.write_text("Clean content.")

        config = Config()
        linter = Linter(config)
        for rule in get_all_rules():
            linter.register_rule(rule)

        results = linter.check([file1, file2])

        assert isinstance(results, dict)
        # file1 should have issues
        assert file1 in results
        assert len(results[file1]) > 0

    def test_check_directory(self, tmp_path: Path) -> None:
        """Test checking a directory."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        config = Config()
        linter = Linter(config)
        for rule in get_all_rules():
            linter.register_rule(rule)

        results = linter.check([tmp_path])

        assert isinstance(results, dict)
        assert len(results) >= 1
