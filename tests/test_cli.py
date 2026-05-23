"""Tests for CLI commands."""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path

from slop_lint.cli import main


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

    def test_check_with_ignore(self, tmp_path: Path) -> None:
        """Test ignoring specific rules."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        result = run_cli("check", str(test_file), "--ignore", "V001")

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
        assert (tmp_path / ".slop-lint.toml").exists()

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

    def test_show_config_displays_settings(self, tmp_path: Path) -> None:
        """Test that --show-config displays configuration."""
        test_file = tmp_path / "test.md"
        test_file.write_text("Clean content.")

        result = run_cli("check", str(test_file), "--show-config")

        assert result.exit_code == 0
        # Should show config info
        assert "select" in result.stdout.lower() or "config" in result.stdout.lower()

    def test_show_config_with_custom_config(self, tmp_path: Path) -> None:
        """Test --show-config with custom config file."""
        config_file = tmp_path / ".slop-lint.toml"
        config_file.write_text('[lint]\nignore = ["V001"]')
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


class TestBaselineMode:
    """Tests for baseline mode."""

    def test_generate_baseline(self, tmp_path: Path) -> None:
        """Test generating a baseline file."""
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

    def test_baseline_warning_on_missing_file(self, tmp_path: Path) -> None:
        """Test warning when baseline file doesn't exist."""
        test_file = tmp_path / "test.md"
        test_file.write_text("This delves into topics.")

        result = run_cli(
            "check",
            str(test_file),
            "--baseline",
            str(tmp_path / "missing.json"),
        )

        assert "Warning" in result.stdout or "not found" in result.stdout


class TestWatchCommand:
    """Tests for the watch command."""

    def test_watch_help(self) -> None:
        """Test that watch command help is available."""
        result = run_cli("watch", "--help")

        assert result.exit_code == 0
        assert "Watch files" in result.stdout or "watch" in result.stdout.lower()
        assert "--interval" in result.stdout


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

    def test_quiet_suppresses_text_output(self, tmp_path: Path) -> None:
        """Quiet mode should leave exit status intact but suppress text output."""
        test_file = tmp_path / "doc.md"
        test_file.write_text("Let us delve into this topic.")

        result = run_cli("check", "--quiet", str(test_file))

        assert result.exit_code == 1
        assert result.stdout == ""
