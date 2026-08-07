"""Tests for CLI commands."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path

import pytest

from slop_lint.cli import main
from slop_lint.config import load_config


@dataclass
class Result:
    """Captures CLI invocation result."""

    exit_code: int
    stdout: str
    stderr: str


def run_cli(*args: str) -> Result:
    """Run the CLI with the given arguments and capture output."""
    out = io.StringIO()
    err = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = main(list(args))
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
    return Result(exit_code=exit_code, stdout=out.getvalue(), stderr=err.getvalue())


class TestCheckCommand:
    """Tests for the check command."""

    def test_check_single_file(self, tmp_path: Path) -> None:
        """Test checking a single file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This is clean content.")

        result = run_cli("check", str(test_file))

        assert result.exit_code == 0
        assert "No issues found" in result.stdout

    def test_check_file_with_issues(self, tmp_path: Path) -> None:
        """Test checking a file with overused vocabulary."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This article delves into the topic.")

        result = run_cli("check", str(test_file))

        assert result.exit_code == 1
        assert "V001" in result.stdout
        assert "delves" in result.stdout

    def test_check_output_includes_explicit_severity(self, tmp_path: Path) -> None:
        """Test default text output includes severity labels."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This article delves into the topic.")

        result = run_cli("check", str(test_file))

        assert result.exit_code == 1
        assert "warning" in result.stdout.lower()

    def test_check_multiple_files(self, tmp_path: Path) -> None:
        """Test checking multiple files."""
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"
        file1.write_text("Clean content here.")
        file2.write_text("More clean content.")

        result = run_cli("check", str(file1), str(file2))

        assert result.exit_code == 0

    def test_check_directory(self, tmp_path: Path) -> None:
        """Test checking a directory."""
        test_file = tmp_path / "doc.md"
        test_file.write_text("This is a test document.")

        result = run_cli("check", str(tmp_path))

        assert result.exit_code == 0

    def test_check_with_json_format(self, tmp_path: Path) -> None:
        """Test JSON output format."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        result = run_cli("check", str(test_file), "--format", "json")

        assert result.exit_code == 1
        assert len(result.stdout) > 0

    def test_check_with_sarif_format(self, tmp_path: Path) -> None:
        """Test SARIF output format."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        result = run_cli("check", str(test_file), "--format", "sarif")

        assert result.exit_code == 1
        assert len(result.stdout) > 0

    def test_check_with_select(self, tmp_path: Path) -> None:
        """Test selecting specific rules."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics. I hope this helps!")

        # Only select V001
        result = run_cli("check", str(test_file), "--select", "V001")

        assert result.exit_code == 1
        assert "V001" in result.stdout
        assert "V002" not in result.stdout

    def test_cli_select_overrides_config_ignore(self, tmp_path: Path) -> None:
        """CLI --select should re-enable a rule ignored by config."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text('[tool.slop-lint]\nignore = ["V001"]\n')
        test_file = tmp_path / "doc.md"
        test_file.write_text("This delves into the topic.\n")

        result = run_cli(
            "check",
            "--config",
            str(config_file),
            "--select",
            "V001",
            str(test_file),
        )

        assert result.exit_code == 1
        assert "V001" in result.stdout

    def test_check_with_ignore(self, tmp_path: Path) -> None:
        """Test ignoring specific rules."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        result = run_cli("check", str(test_file), "--ignore", "V001")

        assert result.exit_code == 0

    def test_check_with_ignore_prefix(self, tmp_path: Path) -> None:
        """Test ignoring a category prefix."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics. I hope this helps!")

        result = run_cli("check", str(test_file), "--ignore", "V")

        assert result.exit_code == 0

    def test_check_with_severity_filter(self, tmp_path: Path) -> None:
        """Test severity filtering."""
        test_file = tmp_path / "test.md"
        test_file.write_text("As of my last update, this is accurate.")

        # V003 is INFO level by default
        result = run_cli("check", str(test_file), "--severity", "warning")
        assert "V003" not in result.stdout

        result = run_cli("check", str(test_file), "--severity", "info")
        assert "V003" in result.stdout

    def test_python_prose_uses_severity_and_confidence_filters(
        self, tmp_path: Path
    ) -> None:
        """Shared CLI filters apply to findings in Python documentation."""
        test_file = tmp_path / "documented.py"
        test_file.write_text(
            '"""As of my last update, this notable result is accurate."""'
        )

        filtered = run_cli(
            "check",
            str(test_file),
            "--select",
            "V001,V003",
            "--severity",
            "warning",
            "--min-confidence",
            "high",
        )
        included = run_cli(
            "check",
            str(test_file),
            "--select",
            "V001,V003",
            "--severity",
            "info",
            "--min-confidence",
            "low",
        )

        assert "V001" not in filtered.stdout
        assert "V003" not in filtered.stdout
        assert "V001" in included.stdout
        assert "V003" in included.stdout

    def test_check_nonexistent_file(self) -> None:
        """Test checking a nonexistent file."""
        result = run_cli("check", "/nonexistent/file.md")

        # File doesn't exist, but linter may just skip it
        # Check that command runs without crashing
        assert result.exit_code in (0, 1, 2)

    def test_check_quiet_mode(self, tmp_path: Path) -> None:
        """Test quiet mode output."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        result = run_cli("check", str(test_file), "--quiet")

        # Quiet mode should have minimal output
        assert result.exit_code == 1

    @pytest.mark.parametrize("output_format", ["text", "json", "sarif"])
    def test_check_omits_suppressed_findings_from_all_formats(
        self, tmp_path: Path, output_format: str
    ) -> None:
        """Suppressed issues never reach a reporter."""
        test_file = tmp_path / "suppressed.md"
        test_file.write_text(
            "<!-- slop-lint-ignore-next-line V001 -->\nThis delves into topics.\n"
        )

        result = run_cli(
            "check",
            str(test_file),
            "--select",
            "V001",
            "--format",
            output_format,
        )

        assert result.exit_code == 0
        if output_format == "text":
            assert "No issues found" in result.stdout
        elif output_format == "json":
            assert json.loads(result.stdout)["summary"]["total_issues"] == 0
        else:
            assert json.loads(result.stdout)["runs"][0]["results"] == []

    def test_inactive_rule_id_is_valid_in_suppression(self, tmp_path: Path) -> None:
        """Validation uses the full registry rather than only active rules."""
        test_file = tmp_path / "suppressed.md"
        test_file.write_text(
            "<!-- slop-lint-ignore-next-line V003 -->\nClean content.\n"
        )

        result = run_cli(
            "check", str(test_file), "--select", "V001", "--severity", "warning"
        )

        assert result.exit_code == 0
        assert "Configuration error" not in result.stderr


class TestRulesCommand:
    """Tests for the rules command."""

    def test_rules_lists_all_categories(self) -> None:
        """Test that rules command lists all categories."""
        result = run_cli("rules")

        assert result.exit_code == 0
        assert "V001" in result.stdout
        assert "S001" in result.stdout
        assert "T001" in result.stdout
        assert "G001" in result.stdout
        assert "C001" in result.stdout
        assert "M001" in result.stdout


class TestExplainCommand:
    """Tests for the explain command."""

    def test_explain_valid_rule(self) -> None:
        """Test explaining a valid rule."""
        result = run_cli("explain", "V001")

        assert result.exit_code == 0
        assert "V001" in result.stdout

    def test_explain_invalid_rule(self) -> None:
        """Test explaining an invalid rule."""
        result = run_cli("explain", "X999")

        assert result.exit_code == 1
        output = result.stdout + result.stderr
        assert (
            "Unknown rule" in output
            or "unknown" in output.lower()
            or result.exit_code == 1
        )


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_config(self, tmp_path: Path, monkeypatch: object) -> None:
        """Test that init creates a config file."""
        monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

        result = run_cli("init")

        assert result.exit_code == 0
        config_file = tmp_path / ".slop-lint.toml"
        assert config_file.exists()
        assert 'minimum_severity = "warning"' in config_file.read_text()
        assert load_config(config_file).severity == "warning"

    def test_init_fails_if_exists(self, tmp_path: Path, monkeypatch: object) -> None:
        """Test that init fails if config already exists."""
        monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
        (tmp_path / ".slop-lint.toml").write_text("[tool.slop-lint]")

        result = run_cli("init")

        assert result.exit_code == 2


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_shows_version(self) -> None:
        """Test that version command shows version."""
        result = run_cli("version")

        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


class TestShowConfigFlag:
    """Tests for the --show-config flag."""

    def test_show_config_displays_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Show-config should identify an all-default policy."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        test_file = tmp_path / "test.md"
        test_file.write_text("Clean content.")

        result = run_cli("check", str(test_file), "--show-config")

        assert result.exit_code == 0
        assert "Config file: default" in result.stdout
        assert "Minimum severity: warning" in result.stdout

    def test_show_config_with_custom_config(self, tmp_path: Path) -> None:
        """Show-config should identify an explicit config file."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text('[tool.slop-lint]\nignore = ["v001"]')
        test_file = tmp_path / "test.md"
        test_file.write_text("Clean content.")

        result = run_cli(
            "check",
            str(test_file),
            "--show-config",
            "--config",
            str(config_file),
        )

        assert result.exit_code == 0
        assert f"Config file: {config_file}" in result.stdout
        assert "Ignore: ['V001']" in result.stdout

    def test_show_config_with_discovered_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Show-config should identify an auto-discovered config file."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text('[tool.slop-lint]\nselect = ["v001"]\n')
        test_file = tmp_path / "test.md"
        test_file.write_text("Clean content.")
        monkeypatch.chdir(tmp_path)

        result = run_cli("check", str(test_file), "--show-config")

        assert result.exit_code == 0
        assert f"Config file: {config_file}" in result.stdout
        assert "Select: ['V001']" in result.stdout


class TestBaselineMode:
    """Tests for baseline mode."""

    def test_generate_baseline(self, tmp_path: Path) -> None:
        """Baseline generation should write the structured format."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")
        baseline_file = tmp_path / ".slop-lint-baseline.json"

        result = run_cli(
            "check",
            str(test_file),
            "--generate-baseline",
            "--baseline",
            str(baseline_file),
        )

        assert result.exit_code == 0
        assert baseline_file.exists()
        assert "Generated baseline" in result.stdout
        assert json.loads(baseline_file.read_text())["version"] == 2

    def test_generate_baseline_excludes_suppressed_findings(
        self, tmp_path: Path
    ) -> None:
        """Inline suppression runs before baseline generation."""
        test_file = tmp_path / "suppressed.md"
        test_file.write_text(
            "<!-- slop-lint-ignore-next-line V001 -->\nThis delves into topics.\n"
        )
        baseline_file = tmp_path / "baseline.json"

        result = run_cli(
            "check",
            str(test_file),
            "--select",
            "V001",
            "--generate-baseline",
            "--baseline",
            str(baseline_file),
        )

        assert result.exit_code == 0
        assert "0 issue(s)" in result.stdout
        assert json.loads(baseline_file.read_text()) == {"version": 2, "entries": []}

    def test_baseline_filters_known_issues(self, tmp_path: Path) -> None:
        """Test that baseline mode filters known issues."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")
        baseline_file = tmp_path / ".slop-lint-baseline.json"

        # Generate baseline first
        run_cli(
            "check",
            str(test_file),
            "--generate-baseline",
            "--baseline",
            str(baseline_file),
        )

        # Now check with baseline - should show no new issues
        result = run_cli(
            "check",
            str(test_file),
            "--baseline",
            str(baseline_file),
        )

        assert result.exit_code == 0
        assert "No issues found" in result.stdout

    def test_missing_baseline_is_configuration_error(self, tmp_path: Path) -> None:
        """An explicitly requested baseline must exist."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        result = run_cli(
            "check",
            str(test_file),
            "--baseline",
            str(tmp_path / "missing.json"),
        )

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "Configuration error" in result.stderr
        assert "baseline file not found" in result.stderr

    @pytest.mark.parametrize("output_format", ["text", "json", "sarif"])
    @pytest.mark.parametrize(
        "payload",
        ["not json", '{"version": 3, "entries": []}'],
    )
    def test_invalid_baseline_stops_before_reporting(
        self, tmp_path: Path, output_format: str, payload: str
    ) -> None:
        """Invalid baselines should not emit findings or structured output."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(payload)

        result = run_cli(
            "check",
            str(test_file),
            "--format",
            output_format,
            "--baseline",
            str(baseline_file),
        )

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "Configuration error" in result.stderr
        assert str(baseline_file) in result.stderr
        assert "Traceback" not in result.stderr

    def test_unreadable_baseline_is_configuration_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Read failures should use configuration exit semantics."""
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text('{"version": 2, "entries": []}')
        test_file = tmp_path / "test.md"
        test_file.write_text("Clean content.")
        original_read_text = Path.read_text

        def fail_baseline(path: Path, *args: object, **kwargs: object) -> str:
            if path == baseline_file:
                raise PermissionError("permission denied")
            return original_read_text(path, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", fail_baseline)

        result = run_cli("check", str(test_file), "--baseline", str(baseline_file))

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "permission denied" in result.stderr

    def test_watch_rejects_invalid_baseline_before_loop(self, tmp_path: Path) -> None:
        """Watch should validate a baseline before printing loop output."""
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text("not json")
        test_file = tmp_path / "test.md"
        test_file.write_text("Clean content.")

        result = run_cli("watch", str(test_file), "--baseline", str(baseline_file))

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "Configuration error" in result.stderr

    def test_watch_loads_baseline_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A watch command should reuse its preflight baseline object."""
        from slop_lint.core.baseline import Baseline

        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text('{"version": 2, "entries": []}')
        test_file = tmp_path / "test.md"
        test_file.write_text("Clean content.")
        original_load = Baseline.load
        load_count = 0

        def count_load(baseline: Baseline) -> bool:
            nonlocal load_count
            load_count += 1
            return original_load(baseline)

        def stop(_interval: float) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr(Baseline, "load", count_load)
        monkeypatch.setattr("slop_lint.cli.time.sleep", stop)

        result = run_cli("watch", str(test_file), "--baseline", str(baseline_file))

        assert result.exit_code == 0
        assert load_count == 1

    def test_generation_uses_confidence_filtered_findings(self, tmp_path: Path) -> None:
        """Low-confidence findings hidden by policy should not enter a baseline."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This is a notable achievement.")
        baseline_file = tmp_path / "baseline.json"

        result = run_cli(
            "check",
            str(test_file),
            "--select",
            "V001",
            "--min-confidence",
            "high",
            "--generate-baseline",
            "--baseline",
            str(baseline_file),
        )

        assert result.exit_code == 0
        assert json.loads(baseline_file.read_text())["entries"] == []

    def test_baseline_workspace_is_independent_of_path_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Files in different directories should share their repository root."""
        (tmp_path / ".git").mkdir()
        docs = tmp_path / "docs"
        source = tmp_path / "src"
        docs.mkdir()
        source.mkdir()
        markdown_file = docs / "guide.md"
        python_file = source / "module.py"
        markdown_file.write_text("This delves into topics.")
        python_file.write_text("# This delves into setup.\n")
        baseline_file = tmp_path / "baseline.json"
        monkeypatch.chdir(tmp_path)

        generated = run_cli(
            "check",
            "docs/guide.md",
            str(python_file),
            "--select",
            "V001",
            "--generate-baseline",
            "--baseline",
            str(baseline_file),
        )
        checked = run_cli(
            "check",
            str(python_file),
            str(markdown_file),
            "--select",
            "V001",
            "--baseline",
            str(baseline_file),
        )

        assert generated.exit_code == 0
        assert checked.exit_code == 0
        assert "No issues found" in checked.stdout

    def test_version_one_baseline_still_filters(self, tmp_path: Path) -> None:
        """Legacy files should remain usable during the compatibility cycle."""
        from slop_lint.core.baseline import Baseline
        from slop_lint.rules.base import Issue

        test_file = tmp_path / "test.md"
        content = "This delves into topics."
        test_file.write_text(content)
        issue = Issue("V001", "Overused word: 'delves' → consider 'explore'", 1, 6)
        baseline = Baseline(tmp_path / "baseline.json")
        fingerprint = baseline._compute_legacy_fingerprint(
            issue, test_file, content, tmp_path
        )
        baseline.baseline_path.write_text(
            json.dumps({"version": "1.0", "fingerprints": [fingerprint]})
        )

        result = run_cli(
            "check",
            str(test_file),
            "--select",
            "V001",
            "--baseline",
            str(baseline.baseline_path),
        )

        assert result.exit_code == 0
        assert "No issues found" in result.stdout

    def test_baseline_write_failure_is_configuration_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Atomic write failures should be concise and recoverable."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        def fail_replace(_source: object, _target: object) -> None:
            raise OSError("disk unavailable")

        monkeypatch.setattr("slop_lint.core.baseline.os.replace", fail_replace)

        result = run_cli(
            "check",
            str(test_file),
            "--generate-baseline",
            "--baseline",
            str(tmp_path / "baseline.json"),
        )

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "disk unavailable" in result.stderr
        assert "Traceback" not in result.stderr

    def test_verbose_baseline_counts_do_not_corrupt_json(self, tmp_path: Path) -> None:
        """Verbose scan diagnostics leave structured stdout parseable."""
        import json

        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")
        baseline_file = tmp_path / "baseline.json"
        run_cli(
            "check",
            str(test_file),
            "--generate-baseline",
            "--baseline",
            str(baseline_file),
        )

        result = run_cli(
            "check",
            str(test_file),
            "--format",
            "json",
            "--verbose",
            "--baseline",
            str(baseline_file),
        )

        assert json.loads(result.stdout)["summary"]["total_issues"] == 0
        assert "Baseline:" in result.stderr


class TestBaselineCommand:
    """Tests for baseline lifecycle maintenance."""

    @staticmethod
    def _create_lifecycle_baseline(tmp_path: Path) -> tuple[Path, list[Path]]:
        active = tmp_path / "active.md"
        stale = tmp_path / "stale.md"
        new = tmp_path / "new.md"
        active.write_text("This delves into active topics.")
        stale.write_text("This delves into stale topics.")
        new.write_text("Clean content.")
        baseline = tmp_path / "baseline.json"
        created = run_cli(
            "baseline",
            "create",
            str(active),
            str(stale),
            "--select",
            "V001",
            "--baseline",
            str(baseline),
        )
        assert created.exit_code == 0
        stale.write_text("Clean content.")
        new.write_text("This delves into new topics.")
        return baseline, [active, stale, new]

    def test_help_lists_actions_and_scan_options(self) -> None:
        """The compact command should advertise its complete surface."""
        result = run_cli("baseline", "--help")

        assert result.exit_code == 0
        for value in ("create", "update", "prune", "summary"):
            assert value in result.stdout
        for option in ("--baseline", "--select", "--ignore", "--severity"):
            assert option in result.stdout

    def test_create_replaces_deterministically(self, tmp_path: Path) -> None:
        """Create should write all current findings and be byte-stable."""
        test_file = tmp_path / "doc.md"
        test_file.write_text("This delves into topics.")
        baseline = tmp_path / "baseline.json"
        baseline.write_text("old data")

        first = run_cli(
            "baseline",
            "create",
            str(test_file),
            "--select",
            "V001",
            "--baseline",
            str(baseline),
        )
        first_bytes = baseline.read_bytes()
        second = run_cli(
            "baseline",
            "create",
            str(test_file),
            "--select",
            "V001",
            "--baseline",
            str(baseline),
        )

        assert first.exit_code == second.exit_code == 0
        assert "Active: 0" in first.stdout
        assert "Stale: 0" in first.stdout
        assert "New: 1" in first.stdout
        assert "Entries: 1" in first.stdout
        assert baseline.read_bytes() == first_bytes
        assert json.loads(first_bytes)["version"] == 2

    def test_summary_reports_lifecycle_without_writing(self, tmp_path: Path) -> None:
        """Summary should classify entries without changing the baseline."""
        baseline, paths = self._create_lifecycle_baseline(tmp_path)
        before = baseline.read_bytes()

        result = run_cli(
            "baseline",
            "summary",
            *(str(path) for path in paths),
            "--select",
            "V001",
            "--baseline",
            str(baseline),
        )

        assert result.exit_code == 0
        assert "Active: 1" in result.stdout
        assert "Stale: 1" in result.stdout
        assert "New: 1" in result.stdout
        assert "Entries: 2" in result.stdout
        assert baseline.read_bytes() == before

    def test_update_adds_new_and_retains_stale_entries(self, tmp_path: Path) -> None:
        """Update should accept new findings without pruning old entries."""
        baseline, paths = self._create_lifecycle_baseline(tmp_path)

        first = run_cli(
            "baseline",
            "update",
            *(str(path) for path in paths),
            "--select",
            "V001",
            "--baseline",
            str(baseline),
        )
        first_bytes = baseline.read_bytes()
        second = run_cli(
            "baseline",
            "update",
            *(str(path) for path in paths),
            "--select",
            "V001",
            "--baseline",
            str(baseline),
        )

        assert first.exit_code == second.exit_code == 0
        assert "Active: 1" in first.stdout
        assert "Stale: 1" in first.stdout
        assert "New: 1" in first.stdout
        assert "Entries: 3" in first.stdout
        assert baseline.read_bytes() == first_bytes

    def test_prune_removes_stale_without_accepting_new(self, tmp_path: Path) -> None:
        """Prune should retain active entries and leave new findings visible."""
        baseline, paths = self._create_lifecycle_baseline(tmp_path)

        first = run_cli(
            "baseline",
            "prune",
            *(str(path) for path in paths),
            "--select",
            "V001",
            "--baseline",
            str(baseline),
        )
        first_bytes = baseline.read_bytes()
        second = run_cli(
            "baseline",
            "prune",
            *(str(path) for path in paths),
            "--select",
            "V001",
            "--baseline",
            str(baseline),
        )

        assert first.exit_code == second.exit_code == 0
        assert "Active: 1" in first.stdout
        assert "Stale: 1" in first.stdout
        assert "New: 1" in first.stdout
        assert "Entries: 1" in first.stdout
        assert "New: 1" in second.stdout
        assert baseline.read_bytes() == first_bytes

    @pytest.mark.parametrize("action", ["update", "prune"])
    def test_writing_action_migrates_version_one(
        self, tmp_path: Path, action: str
    ) -> None:
        """A write should convert active v1 hashes and report opaque stale ones."""
        from slop_lint.core.baseline import Baseline
        from slop_lint.rules.base import Issue

        test_file = tmp_path / "doc.md"
        content = "This delves into topics."
        test_file.write_text(content)
        baseline = Baseline(tmp_path / "baseline.json")
        issue = Issue("V001", "Overused word: 'delves' → consider 'explore'", 1, 6)
        active = baseline._compute_legacy_fingerprint(
            issue, test_file, content, tmp_path
        )
        baseline.baseline_path.write_text(
            json.dumps({"version": "1.0", "fingerprints": [active, "0" * 32]})
        )

        result = run_cli(
            "baseline",
            action,
            str(test_file),
            "--select",
            "V001",
            "--baseline",
            str(baseline.baseline_path),
        )

        assert result.exit_code == 0
        assert "Format: 1" in result.stdout
        assert "Active: 1" in result.stdout
        assert "Stale: 1" in result.stdout
        assert "New: 0" in result.stdout
        data = json.loads(baseline.baseline_path.read_text())
        assert data["version"] == 2
        assert len(data["entries"]) == 1

    @pytest.mark.parametrize("action", ["update", "prune", "summary"])
    def test_existing_actions_require_baseline(
        self, tmp_path: Path, action: str
    ) -> None:
        """Only create may begin without an existing baseline."""
        test_file = tmp_path / "doc.md"
        test_file.write_text("Clean content.")

        result = run_cli(
            "baseline",
            action,
            str(test_file),
            "--baseline",
            str(tmp_path / "missing.json"),
        )

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "baseline file not found" in result.stderr

    def test_create_uses_default_path_and_scan_policy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Create should share suppressions and default baseline location."""
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "doc.md"
        test_file.write_text(
            "<!-- slop-lint-ignore-next-line V001 -->\nThis delves into topics.\n"
        )

        result = run_cli("baseline", "create", str(test_file), "--select", "V001")

        baseline = tmp_path / ".slop-lint-baseline.json"
        assert result.exit_code == 0
        assert baseline.exists()
        assert json.loads(baseline.read_text())["entries"] == []


class TestWatchCommand:
    """Tests for the watch command."""

    @staticmethod
    def _stop_after_first_iteration(monkeypatch: object) -> None:
        def stop(_interval: float) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr("slop_lint.cli.time.sleep", stop)  # type: ignore[attr-defined]

    @staticmethod
    def _finding_lines(output: str, path: Path) -> list[str]:
        prefix = f"{path}:"
        return [line for line in output.splitlines() if line.startswith(prefix)]

    def test_watch_help(self) -> None:
        """Test that watch command help is available."""
        result = run_cli("watch", "--help")

        assert result.exit_code == 0
        assert "Watch files" in result.stdout or "watch" in result.stdout.lower()
        assert "--interval" in result.stdout
        for option in (
            "--severity",
            "--min-confidence",
            "--hide-low",
            "--baseline",
            "--quiet",
            "--verbose",
        ):
            assert option in result.stdout
        assert "--format" not in result.stdout
        assert "--generate-baseline" not in result.stdout

    def test_watch_and_check_share_scan_filters(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        """One watch batch returns the same findings as check."""
        test_file = tmp_path / "doc.md"
        test_file.write_text(
            "This delves into a notable topic. As of my last update, it was accurate."
        )
        options = (
            "--select",
            "V001,V003",
            "--severity",
            "warning",
            "--min-confidence",
            "high",
        )
        self._stop_after_first_iteration(monkeypatch)

        checked = run_cli("check", str(test_file), *options)
        watched = run_cli("watch", str(test_file), "--no-clear", *options)

        assert self._finding_lines(watched.stdout, test_file) == self._finding_lines(
            checked.stdout, test_file
        )

    def test_watch_and_check_share_inline_suppressions(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        """One watch batch applies the same line suppression as check."""
        test_file = tmp_path / "doc.md"
        test_file.write_text(
            "<!-- slop-lint-ignore-next-line V001 -->\n"
            "This delves into a topic.\n"
            "This delves into another topic.\n"
        )
        self._stop_after_first_iteration(monkeypatch)

        checked = run_cli("check", str(test_file), "--select", "V001")
        watched = run_cli("watch", str(test_file), "--no-clear", "--select", "V001")

        assert self._finding_lines(watched.stdout, test_file) == self._finding_lines(
            checked.stdout, test_file
        )

    def test_watch_reports_malformed_inline_suppression(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        """Watch reports a configuration error and remains controllable."""
        test_file = tmp_path / "doc.md"
        test_file.write_text(
            "<!-- slop-lint-ignore-next-line V001, -->\nThis delves.\n"
        )
        self._stop_after_first_iteration(monkeypatch)

        watched = run_cli("watch", str(test_file), "--no-clear")

        assert watched.exit_code == 0
        assert "Configuration error" in watched.stderr
        assert f"{test_file}: line 1: malformed" in watched.stderr
        assert "Traceback" not in watched.stderr

    def test_watch_respects_baseline(self, tmp_path: Path, monkeypatch: object) -> None:
        """Known baseline findings are filtered from a watch batch."""
        test_file = tmp_path / "doc.md"
        test_file.write_text("This delves into a topic.")
        baseline_file = tmp_path / "baseline.json"
        run_cli(
            "check",
            str(test_file),
            "--generate-baseline",
            "--baseline",
            str(baseline_file),
        )
        self._stop_after_first_iteration(monkeypatch)

        watched = run_cli(
            "watch",
            str(test_file),
            "--no-clear",
            "--baseline",
            str(baseline_file),
        )

        assert "V001" not in watched.stdout
        assert "No issues found!" in watched.stdout

    def test_watch_applies_severity_override_before_threshold(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        """Configured rule severity is considered before minimum severity."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[tool.slop-lint.severity]\nV003 = "warning"\n')
        test_file = tmp_path / "doc.md"
        test_file.write_text("As of my last update, this was accurate.")
        self._stop_after_first_iteration(monkeypatch)

        watched = run_cli(
            "watch",
            str(test_file),
            "--no-clear",
            "--config",
            str(config_file),
            "--select",
            "V003",
            "--severity",
            "warning",
        )

        assert "V003" in watched.stdout
        assert "[warning]" in watched.stdout

    def test_quiet_watch_prints_only_error_findings(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        """Quiet watch suppresses loop status, summaries, and warnings."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[tool.slop-lint.severity]\nV001 = "error"\n')
        test_file = tmp_path / "doc.md"
        test_file.write_text("This delves into a topic.")
        self._stop_after_first_iteration(monkeypatch)

        watched = run_cli(
            "watch",
            str(test_file),
            "--config",
            str(config_file),
            "--quiet",
        )

        finding_lines = self._finding_lines(watched.stdout, test_file)
        assert len(finding_lines) == 1
        assert "V001 [high] [error] Overused word: 'delves'" in finding_lines[0]
        assert "Watching" not in watched.stdout
        assert "Found" not in watched.stdout
        assert "Stopped" not in watched.stdout

    def test_watch_reports_read_errors_on_stderr(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        """Watch reports unreadable input without hiding it or tracing back."""
        test_file = tmp_path / "invalid.md"
        test_file.write_bytes(b"\xff")
        self._stop_after_first_iteration(monkeypatch)

        watched = run_cli("watch", str(test_file), "--no-clear")

        assert "Could not read file" in watched.stderr
        assert "Traceback" not in watched.stderr


class TestHelpFlags:
    """Tests for help flag aliases."""

    def test_root_help_short_flag(self) -> None:
        """Test that -h shows top-level help."""
        result = run_cli("-h")

        assert result.exit_code == 0
        assert "Detect bad writing practices" in result.stdout
        assert "check" in result.stdout

    def test_check_help_short_flag(self) -> None:
        """Test that -h shows check command help."""
        result = run_cli("check", "-h")

        assert result.exit_code == 0
        assert "--format" in result.stdout


class TestOutputFormats:
    """Tests for JSON and SARIF output formats."""

    def test_json_format_valid(self, tmp_path: Path) -> None:
        """Test that --format json outputs valid JSON."""
        import json

        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        result = run_cli("check", str(test_file), "--format", "json")

        assert result.exit_code == 1
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert "files" in data
        assert "summary" in data
        assert data["summary"]["total_issues"] >= 1

    def test_sarif_format_valid(self, tmp_path: Path) -> None:
        """Test that --format sarif outputs valid SARIF."""
        import json

        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        result = run_cli("check", str(test_file), "--format", "sarif")

        assert result.exit_code == 1
        # Should be valid JSON (SARIF is JSON)
        data = json.loads(result.stdout)
        assert data.get("version") == "2.1.0"
        assert "runs" in data
        assert len(data["runs"]) > 0
        assert len(data["runs"][0]["results"]) >= 1

    def test_json_format_no_issues(self, tmp_path: Path) -> None:
        """Test JSON output with no issues."""
        import json

        test_file = tmp_path / "clean.md"
        test_file.write_text("This is clean content.")

        result = run_cli("check", str(test_file), "--format", "json")

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["summary"]["total_issues"] == 0
        assert data["summary"]["files_checked"] == 1


class TestMinConfidenceFlag:
    """Tests for --min-confidence and --hide-low CLI flags."""

    def test_min_confidence_high_filters_low(self, tmp_path: Path) -> None:
        """Low-confidence issues (tier 3 words) are hidden at --min-confidence high."""
        test_file = tmp_path / "test.md"
        # 'notable' is tier 3 (LOW confidence), 'delve' is tier 1 (HIGH)
        test_file.write_text("This is a notable achievement.")

        result = run_cli("check", str(test_file), "--min-confidence", "high")
        # 'notable' is LOW confidence, should be filtered out
        assert "notable" not in result.stdout

    def test_min_confidence_high_keeps_high(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.md"
        test_file.write_text("Let us delve into this topic.")

        result = run_cli("check", str(test_file), "--min-confidence", "high")
        assert "delve" in result.stdout

    def test_hide_low_flag(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.md"
        # 'notable' is tier 3 (LOW), will appear via V001 without --hide-low
        test_file.write_text("This is a notable achievement.")

        # Without --hide-low, V001 reports 'notable'
        result_all = run_cli("check", str(test_file))
        assert "V001" in result_all.stdout

        # With --hide-low, V001 low-confidence hit is suppressed
        result_filtered = run_cli("check", str(test_file), "--hide-low")
        assert "V001" not in result_filtered.stdout


class TestCliValidation:
    """Tests for argument validation before linting starts."""

    def test_invalid_format_returns_usage_error(self, tmp_path: Path) -> None:
        """Unsupported output formats should be rejected by argparse."""
        test_file = tmp_path / "clean.md"
        test_file.write_text("Clean content.")

        result = run_cli("check", "--format", "xml", str(test_file))

        assert result.exit_code == 2
        assert "invalid choice" in result.stderr

    def test_invalid_severity_returns_usage_error(self, tmp_path: Path) -> None:
        """Unsupported severity thresholds should be rejected by argparse."""
        test_file = tmp_path / "clean.md"
        test_file.write_text("Clean content.")

        result = run_cli("check", "--severity", "banana", str(test_file))

        assert result.exit_code == 2
        assert "invalid choice" in result.stderr

    def test_invalid_min_confidence_returns_usage_error(self, tmp_path: Path) -> None:
        """Unsupported confidence thresholds should be rejected by argparse."""
        test_file = tmp_path / "clean.md"
        test_file.write_text("Clean content.")

        result = run_cli("check", "--min-confidence", "certain", str(test_file))

        assert result.exit_code == 2
        assert "invalid choice" in result.stderr

    def test_missing_check_path_returns_usage_error(self) -> None:
        """Missing check paths should not be treated as clean scans."""
        result = run_cli("check", "/private/tmp/slop-lint-path-that-does-not-exist.md")

        assert result.exit_code == 2
        assert "Path does not exist" in result.stderr

    def test_missing_watch_path_returns_usage_error(self) -> None:
        """Missing watch paths should fail before entering the watch loop."""
        result = run_cli("watch", "/private/tmp/slop-lint-path-that-does-not-exist.md")

        assert result.exit_code == 2
        assert "Path does not exist" in result.stderr

    def test_invalid_config_returns_config_error(self, tmp_path: Path) -> None:
        """Malformed config files should not print Python tracebacks."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text("invalid [ toml ][\n")
        test_file = tmp_path / "clean.md"
        test_file.write_text("Clean content.")

        result = run_cli("check", "--config", str(config_file), str(test_file))

        assert result.exit_code == 2
        assert "Configuration error" in result.stderr
        assert str(config_file) in result.stderr
        assert "Traceback" not in result.stderr

    @pytest.mark.parametrize("option", ["--select", "--ignore"])
    def test_invalid_cli_rule_reference_returns_config_error(
        self, tmp_path: Path, option: str
    ) -> None:
        """CLI selectors should use the same registry validation as files."""
        test_file = tmp_path / "clean.md"
        test_file.write_text("Clean content.")

        result = run_cli("check", option, "V01", str(test_file))

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "<command line>" in result.stderr
        assert "did you mean 'V001'" in result.stderr

    @pytest.mark.parametrize("output_format", ["json", "sarif"])
    def test_invalid_config_rule_keeps_structured_stdout_empty(
        self, tmp_path: Path, output_format: str
    ) -> None:
        """Configuration diagnostics should not corrupt structured output."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text('[tool.slop-lint]\nselect = ["X999"]\n')
        test_file = tmp_path / "clean.md"
        test_file.write_text("Clean content.")

        result = run_cli(
            "check",
            "--config",
            str(config_file),
            "--format",
            output_format,
            str(test_file),
        )

        assert result.exit_code == 2
        assert result.stdout == ""
        assert str(config_file) in result.stderr
        assert "unknown rule reference" in result.stderr

    def test_watch_rejects_invalid_config_before_loop(self, tmp_path: Path) -> None:
        """Watch should share check's configuration failure semantics."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text('[tool.slop-lint]\nignore = ["X999"]\n')
        test_file = tmp_path / "clean.md"
        test_file.write_text("Clean content.")

        result = run_cli(
            "watch", "--config", str(config_file), str(test_file), "--no-clear"
        )

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "Configuration error" in result.stderr

    def test_lowercase_severity_override_changes_effective_rule(
        self, tmp_path: Path
    ) -> None:
        """Normalized override IDs should be applied during rule construction."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text(
            '[tool.slop-lint]\nminimum_severity = "warning"\nselect = ["v003"]\n\n'
            '[tool.slop-lint.severity]\nv003 = "warning"\n'
        )
        test_file = tmp_path / "doc.md"
        test_file.write_text("As of my last update, this was accurate.")

        result = run_cli("check", "--config", str(config_file), str(test_file))

        assert result.exit_code == 1
        assert "V003" in result.stdout
        assert "[warning]" in result.stdout

    def test_lowercase_per_file_ignore_suppresses_rule(self, tmp_path: Path) -> None:
        """Normalized per-file IDs should affect rule selection."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text(
            '[tool.slop-lint]\nselect = ["v001"]\n\n'
            "[[tool.slop-lint.per-file-ignores]]\n"
            'pattern = "doc.md"\nignore = ["v001"]\n'
        )
        test_file = tmp_path / "doc.md"
        test_file.write_text("This delves into the topic.")

        result = run_cli("check", "--config", str(config_file), str(test_file))

        assert result.exit_code == 0
        assert "V001" not in result.stdout

    @pytest.mark.parametrize(
        ("directive", "detail"),
        [
            ("<!-- slop-lint-ignore-next-line V999 -->", "unknown"),
            ("<!-- slop-lint-ignore-next-line V001, -->", "malformed"),
        ],
    )
    def test_invalid_inline_suppression_returns_config_error(
        self, tmp_path: Path, directive: str, detail: str
    ) -> None:
        """Directive errors use configuration exit semantics and stderr."""
        test_file = tmp_path / "invalid.md"
        test_file.write_text(f"Intro\n{directive}\nThis delves.\n")

        result = run_cli(
            "check", str(test_file), "--format", "json", "--select", "V001"
        )

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "Configuration error" in result.stderr
        assert f"{test_file}: line 2: {detail}" in result.stderr
        assert "Traceback" not in result.stderr

    def test_invalid_utf8_file_returns_internal_error(self, tmp_path: Path) -> None:
        """Undecodable files should be reported without tracebacks."""
        test_file = tmp_path / "invalid.md"
        test_file.write_bytes(b"\xff")

        result = run_cli("check", str(test_file))

        assert result.exit_code == 3
        assert "Could not read file" in result.stderr
        assert str(test_file) in result.stderr
        assert "Traceback" not in result.stderr


class TestCliExitSemantics:
    """Tests for exit-code and quiet-output behavior."""

    def test_info_only_issues_do_not_fail(self, tmp_path: Path) -> None:
        """Info-only findings should be displayed without failing the process."""
        test_file = tmp_path / "doc.md"
        test_file.write_text("This not only improves speed but also reliability.")

        result = run_cli(
            "check", "--select", "S002", "--severity", "info", str(test_file)
        )

        assert result.exit_code == 0
        assert "S002" in result.stdout

    def test_warning_issues_fail(self, tmp_path: Path) -> None:
        """Warnings should still make the process fail."""
        test_file = tmp_path / "doc.md"
        test_file.write_text("Let us delve into this topic.")

        result = run_cli("check", "--select", "V001", str(test_file))

        assert result.exit_code == 1
        assert "V001" in result.stdout

    def test_quiet_outputs_error_issues(self, tmp_path: Path) -> None:
        """Quiet mode should print error findings and suppress non-errors."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text('[tool.slop-lint.severity]\nV001 = "error"\n')
        test_file = tmp_path / "doc.md"
        test_file.write_text("Let us delve into this topic.\n")

        result = run_cli(
            "check", "--config", str(config_file), "--quiet", str(test_file)
        )

        assert result.exit_code == 1
        assert "V001" in result.stdout
        assert "[error]" in result.stdout

    def test_quiet_suppresses_warning_issues(self, tmp_path: Path) -> None:
        """Quiet mode should leave exit status intact but hide warning findings."""
        test_file = tmp_path / "doc.md"
        test_file.write_text("Let us delve into this topic.")

        result = run_cli("check", "--quiet", str(test_file))

        assert result.exit_code == 1
        assert result.stdout == ""
