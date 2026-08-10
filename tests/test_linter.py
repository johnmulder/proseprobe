"""Tests for the core linter module."""

import subprocess
from pathlib import Path

import pytest

from proseprobe.config import Config, ConfigError, PerFileIgnore, VocabularyConfig
from proseprobe.core.linter import Linter, LintResults
from proseprobe.rules import get_all_rules
from proseprobe.rules.vocab import AIVocabularyRule


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

    def test_general_prose_rule_metadata_includes_supported_formats(self) -> None:
        """General prose rules declare Markdown and intended Python support."""
        markdown_only = {"G015"}
        for rule in get_all_rules():
            if rule.id[0] in {"V", "G", "S", "T"} and rule.content_scope == "prose":
                assert "markdown" in rule.applies_to, rule.id
                assert ("python" in rule.applies_to) == (
                    rule.id not in markdown_only
                ), rule.id


class TestDiscoverFiles:
    """Tests for file discovery."""

    @staticmethod
    def _init_git(path: Path) -> None:
        subprocess.run(["git", "init", "-q", str(path)], check=True)

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

    def test_discover_directory_includes_mdx_and_markdown(self, tmp_path: Path) -> None:
        """Test discovering .mdx and .markdown files with default config."""
        md_file = tmp_path / "doc.md"
        mdx_file = tmp_path / "page.mdx"
        markdown_file = tmp_path / "notes.markdown"
        md_file.write_text("content")
        mdx_file.write_text("content")
        markdown_file.write_text("content")

        config = Config()
        linter = Linter(config)
        files = set(linter.discover_files([tmp_path]))

        assert md_file in files
        assert mdx_file in files
        assert markdown_file in files

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

    def test_discover_respects_gitignore(self, tmp_path: Path) -> None:
        """Test that discovery excludes files matched by .gitignore."""
        self._init_git(tmp_path)
        (tmp_path / ".gitignore").write_text("ignored.md\n")
        ignored = tmp_path / "ignored.md"
        kept = tmp_path / "kept.md"
        ignored.write_text("content")
        kept.write_text("content")

        config = Config()
        linter = Linter(config)
        files = set(linter.discover_files([tmp_path]))

        assert kept in files
        assert ignored not in files

    def test_discover_explicit_file_overrides_gitignore(self, tmp_path: Path) -> None:
        """Test explicit file paths are linted even when gitignored."""
        self._init_git(tmp_path)
        (tmp_path / ".gitignore").write_text("ignored.md\n")
        ignored = tmp_path / "ignored.md"
        ignored.write_text("content")

        config = Config()
        linter = Linter(config)
        files = linter.discover_files([ignored])

        assert files == [ignored]

    def test_discover_respects_nested_gitignore(self, tmp_path: Path) -> None:
        """Test nested .gitignore files are applied for subdirectories."""
        self._init_git(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / ".gitignore").write_text("*.md\n")

        ignored = docs / "ignored.md"
        kept = tmp_path / "root.md"
        ignored.write_text("content")
        kept.write_text("content")

        config = Config()
        linter = Linter(config)
        files = set(linter.discover_files([tmp_path]))

        assert kept in files
        assert ignored not in files

    def test_discover_gitignore_negation_reincludes_file(self, tmp_path: Path) -> None:
        """Test gitignore negation patterns re-include matching files."""
        self._init_git(tmp_path)
        (tmp_path / ".gitignore").write_text("*.md\n!keep.md\n")
        ignored = tmp_path / "ignored.md"
        kept = tmp_path / "keep.md"
        ignored.write_text("content")
        kept.write_text("content")

        config = Config()
        linter = Linter(config)
        files = set(linter.discover_files([tmp_path]))

        assert kept in files
        assert ignored not in files

    def test_discover_nested_negation_overrides_parent_ignore(
        self, tmp_path: Path
    ) -> None:
        """Test child .gitignore can re-include a file ignored by parent patterns."""
        self._init_git(tmp_path)
        (tmp_path / ".gitignore").write_text("*.md\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / ".gitignore").write_text("!keep.md\n")

        keep = docs / "keep.md"
        drop = docs / "drop.md"
        keep.write_text("content")
        drop.write_text("content")

        config = Config()
        linter = Linter(config)
        files = set(linter.discover_files([tmp_path]))

        assert keep in files
        assert drop not in files


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


class TestCheckContent:
    """Tests for linting content without reading a file."""

    def test_check_content_uses_virtual_path_and_inline_suppressions(self) -> None:
        linter = Linter(Config(select=["V001"]))
        linter.register_rule(AIVocabularyRule())

        issues = linter.check_content(
            "<!-- proseprobe-ignore-next-line V001 -->\n"
            "This delves into setup.\n"
            "This delves into teardown.\n",
            Path("draft.md"),
        )

        assert [(issue.rule_id, issue.line) for issue in issues] == [("V001", 3)]

    def test_check_file_matches_check_content(self, tmp_path: Path) -> None:
        path = tmp_path / "draft.md"
        content = "This delves into the topic.\n"
        path.write_text(content)
        linter = Linter(Config(select=["V001"]))
        linter.register_rule(AIVocabularyRule())

        assert linter.check_file(path) == linter.check_content(content, path)


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
        """Test checking markdown file with overused vocabulary."""
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

    def test_general_prose_rules_scan_python_documentation(
        self, tmp_path: Path
    ) -> None:
        """Shared prose rules report docstrings and comments at source columns."""
        test_file = tmp_path / "documented.py"
        long_sentence = " ".join(["word"] * 41) + "."
        test_file.write_text(
            '"""This delves into systems.\n'
            "I hope this helps.\n"
            "It may perhaps work.\n"
            "This tool will change everything.\n"
            f"{long_sentence}\n"
            '"""\n'
            'message = "I hope this helps while it delves."\n'
            "# Let me know if you need help.\n"
            "value = 1  # As of my last update, this is accurate.\n"
        )
        linter = Linter(Config())
        for rule in get_all_rules():
            linter.register_rule(rule)

        issues = linter.check_file(test_file)

        locations = {(issue.rule_id, issue.line, issue.column) for issue in issues}
        assert ("V001", 1, 9) in locations
        assert ("V002", 2, 1) in locations
        assert ("G002", 3, 8) in locations
        assert ("V006", 4, 11) in locations
        assert ("T008", 5, 1) in locations
        assert ("V002", 8, 3) in locations
        assert ("V003", 9, 14) in locations
        assert not any(issue.line == 7 for issue in issues)

    def test_python_prose_rules_respect_selection_and_ignores(
        self, tmp_path: Path
    ) -> None:
        """Existing selectors control shared rules on Python files."""
        test_file = tmp_path / "documented.py"
        test_file.write_text('"""I hope this helps."""')

        selected = Linter(Config(select=["V002"]))
        ignored = Linter(Config(select=["V002"], ignore=["V002"]))
        for rule in get_all_rules():
            selected.register_rule(rule)
            ignored.register_rule(rule)

        assert [issue.rule_id for issue in selected.check_file(test_file)] == ["V002"]
        assert ignored.check_file(test_file) == []

    def test_python_prose_rules_respect_per_file_ignores(self, tmp_path: Path) -> None:
        """Per-file policy applies to shared rules on Python files."""
        test_file = tmp_path / "documented.py"
        test_file.write_text('"""I hope this helps."""')
        config = Config(
            select=["V002"],
            per_file_ignores=[PerFileIgnore(pattern="*.py", ignore=["V002"])],
        )
        linter = Linter(config)
        for rule in get_all_rules():
            linter.register_rule(rule)

        assert linter.check_file(test_file) == []

    def test_structural_rules_do_not_cross_python_docstrings(
        self, tmp_path: Path
    ) -> None:
        """Independent docstrings cannot form one repeated-opening sequence."""
        test_file = tmp_path / "separate.py"
        test_file.write_text(
            'def one():\n    """They build."""\n\n'
            'def two():\n    """They test."""\n\n'
            'def three():\n    """They ship."""\n'
        )
        linter = Linter(Config(select=["S010"]))
        for rule in get_all_rules():
            linter.register_rule(rule)

        assert linter.check_file(test_file) == []

    def test_threshold_rules_do_not_combine_python_docstrings(
        self, tmp_path: Path
    ) -> None:
        """Document-level thresholds restart for each Python prose block."""
        test_file = tmp_path / "separate.py"
        test_file.write_text(
            'def one():\n    """Compare speed, scale, and safety. Smith (2020) argues this."""\n\n'
            'def two():\n    """Compare cost, scope, and time. Jones (2021) reports this."""\n\n'
            'def three():\n    """Compare red, green, and blue. Brown (2022) finds this."""\n\n'
            'def four():\n    """Compare one, two, and three. White (2023) observes this."""\n'
        )
        linter = Linter(Config(select=["S001", "S018"]))
        for rule in get_all_rules():
            linter.register_rule(rule)

        assert linter.check_file(test_file) == []

    def test_v001_and_c001_own_distinct_python_vocabulary(self, tmp_path: Path) -> None:
        """General and docstring-only vocabulary rules do not duplicate matches."""
        test_file = tmp_path / "vocabulary.py"
        test_file.write_text('"""A robust API can utilize a bespoke adapter."""')
        linter = Linter(Config(select=["V001", "C001"]))
        for rule in get_all_rules():
            linter.register_rule(rule)

        issues = linter.check_file(test_file)

        assert [(issue.rule_id, issue.line) for issue in issues] == [
            ("C001", 1),
            ("V001", 1),
            ("V001", 1),
        ]

    def test_additional_vocabulary_promotes_c001_term_to_v001(
        self, tmp_path: Path
    ) -> None:
        """Configured general vocabulary remains owned by V001 alone."""
        test_file = tmp_path / "vocabulary.py"
        test_file.write_text('"""Use a bespoke adapter."""')
        config = Config(
            select=["V001", "C001"],
            vocabulary=VocabularyConfig(additional=["bespoke"]),
        )
        linter = Linter(config)
        for rule in get_all_rules(config):
            linter.register_rule(rule)

        assert [issue.rule_id for issue in linter.check_file(test_file)] == ["V001"]

    def test_inline_suppression_filters_only_matching_rule_and_line(
        self, tmp_path: Path
    ) -> None:
        """Rule IDs and prefixes apply only to the reported target line."""
        test_file = tmp_path / "suppressed.md"
        test_file.write_text(
            "<!-- proseprobe-ignore-next-line v001, v001 -->\n"
            "This delves into a topic. I hope this helps.\n"
            "This delves into another topic.\n"
            "<!-- proseprobe-ignore-next-line V -->\n"
            "This delves into a final topic. I hope this helps.\n"
        )
        linter = Linter(Config(select=["V001", "V002"]))
        for rule in get_all_rules():
            linter.register_rule(rule)

        issues = linter.check_file(test_file)

        assert [(issue.rule_id, issue.line) for issue in issues] == [
            ("V001", 3),
            ("V002", 2),
        ]

    def test_python_inline_suppression_targets_same_source_line(
        self, tmp_path: Path
    ) -> None:
        """Python directives suppress docstring and comment findings in place."""
        test_file = tmp_path / "suppressed.py"
        test_file.write_text(
            '"""This delves into the API."""  # proseprobe: ignore=V001\n'
            "# This delves into setup.  # proseprobe: ignore=V001\n"
            "# This delves into teardown.\n"
        )
        linter = Linter(Config(select=["V001"]))
        for rule in get_all_rules():
            linter.register_rule(rule)

        assert [
            (issue.rule_id, issue.line) for issue in linter.check_file(test_file)
        ] == [("V001", 3)]

    @pytest.mark.parametrize(
        ("directive", "detail"),
        [
            ("<!-- proseprobe-ignore-next-line V999 -->", "unknown"),
            ("<!-- proseprobe-ignore-next-line V001, -->", "malformed"),
        ],
    )
    def test_invalid_inline_suppression_is_a_config_error(
        self, tmp_path: Path, directive: str, detail: str
    ) -> None:
        """Invalid directives fail with the source path and directive line."""
        test_file = tmp_path / "invalid.md"
        test_file.write_text(f"Intro\n{directive}\nThis delves.\n")
        linter = Linter(Config())
        for rule in get_all_rules():
            linter.register_rule(rule)

        with pytest.raises(ConfigError, match=rf"invalid\.md: line 2: {detail}"):
            linter.check_file(test_file)

    def test_invalid_suppression_propagates_from_parallel_scan(
        self, tmp_path: Path
    ) -> None:
        """Threaded scans surface directive errors without swallowing them."""
        (tmp_path / "clean.md").write_text("Clean content.\n")
        invalid = tmp_path / "invalid.md"
        invalid.write_text("<!-- proseprobe-ignore-next-line X -->\nClean content.\n")
        linter = Linter(Config())
        for rule in get_all_rules():
            linter.register_rule(rule)

        with pytest.raises(ConfigError, match=r"invalid\.md: line 1: unknown"):
            linter.check([tmp_path])


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

        assert isinstance(results, LintResults)
        assert results.files_checked == 2
        # file1 should have issues
        assert file1 in results.issues_by_file
        assert len(results.issues_by_file[file1]) > 0

    def test_check_directory(self, tmp_path: Path) -> None:
        """Test checking a directory."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        config = Config()
        linter = Linter(config)
        for rule in get_all_rules():
            linter.register_rule(rule)

        results = linter.check([tmp_path])

        assert len(results.issues_by_file) >= 1

    def test_check_returns_deterministic_key_order(self, tmp_path: Path) -> None:
        """Test that check results are ordered deterministically by path."""
        file_a = tmp_path / "a.md"
        file_b = tmp_path / "b.md"
        file_c = tmp_path / "c.md"
        for f in (file_a, file_b, file_c):
            f.write_text("This delves into topics.")

        config = Config()
        linter = Linter(config)
        linter.register_rule(AIVocabularyRule())

        linter.discover_files = lambda _paths: [file_b, file_c, file_a]  # type: ignore[method-assign]
        results = linter.check([tmp_path])

        assert list(results.issues_by_file) == [file_a, file_b, file_c]

    def test_check_uses_parallel_executor_for_multiple_files(
        self,
        tmp_path: Path,
        monkeypatch: object,
    ) -> None:
        """Test check uses ThreadPoolExecutor path for multiple files."""
        for idx in range(3):
            (tmp_path / f"f{idx}.md").write_text("This delves into topics.")

        config = Config()
        linter = Linter(config)
        linter.register_rule(AIVocabularyRule())

        called = {"value": False}

        class FakeExecutor:
            def __init__(self, max_workers: int) -> None:
                self.max_workers = max_workers

            def __enter__(self) -> "FakeExecutor":
                called["value"] = True
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def map(self, fn: object, iterable: list[Path]) -> list[object]:
                return [fn(item) for item in iterable]  # type: ignore[misc,operator]

        monkeypatch.setattr("proseprobe.core.linter.ThreadPoolExecutor", FakeExecutor)
        linter.check([tmp_path])

        assert called["value"]
