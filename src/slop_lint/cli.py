"""Command-line interface for slop-lint."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from slop_lint._ansi import clear_screen, style, table
from slop_lint.config import ConfigError, load_config
from slop_lint.core.linter import Linter, LintReadError
from slop_lint.rules import get_all_rules
from slop_lint.rules.base import (
    Confidence,
    Issue,
    Rule,
    Severity,
    severity_from_str,
    severity_rank,
)

if TYPE_CHECKING:
    from slop_lint.config import Config

_CONFIDENCE_RANK = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}


def _confidence_rank(confidence: Confidence) -> int:
    """Return numeric rank for confidence comparisons."""
    return _CONFIDENCE_RANK.get(confidence, 0)


def _parse_confidence(value: str) -> Confidence | None:
    """Parse a confidence string into a Confidence enum."""
    mapping = {
        "high": Confidence.HIGH,
        "medium": Confidence.MEDIUM,
        "low": Confidence.LOW,
    }
    return mapping.get(value.lower())


def _validate_existing_paths(paths: list[Path]) -> int | None:
    """Return a usage exit code after reporting missing paths, if any."""
    missing_paths = [path for path in paths if not path.exists()]
    if not missing_paths:
        return None

    for path in missing_paths:
        print(f"Path does not exist: {path}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _filter_by_confidence(
    results: dict[Path, list[Issue]],
    args: argparse.Namespace,
    config: Config,
) -> dict[Path, list[Issue]]:
    """Remove issues below the effective confidence threshold."""
    effective_confidence = args.min_confidence or (
        "medium" if args.hide_low else config.min_confidence
    )
    confidence_threshold = _parse_confidence(effective_confidence)
    if not confidence_threshold or confidence_threshold == Confidence.LOW:
        return results
    filtered = {
        path: [
            issue
            for issue in issues
            if _confidence_rank(issue.confidence)
            >= _confidence_rank(confidence_threshold)
        ]
        for path, issues in results.items()
    }
    return {path: issues for path, issues in filtered.items() if issues}


def _apply_baseline(
    results: dict[Path, list[Issue]],
    args: argparse.Namespace,
    paths: list[Path],
) -> dict[Path, list[Issue]] | None:
    """Handle --generate-baseline or --baseline filtering.

    Returns:
        Filtered results, or *None* when a baseline was generated (caller
        should return 0 immediately).
    """
    if args.generate_baseline:
        from slop_lint.core.baseline import Baseline

        baseline_path = Path(args.baseline) if args.baseline else None
        baseline_obj = Baseline(baseline_path)
        workspace = paths[0].parent if paths else Path.cwd()

        for file_path, issues in results.items():
            try:
                content = file_path.read_text()
                for issue in issues:
                    baseline_obj.add_issue(issue, file_path, content, workspace)
            except OSError:
                continue

        baseline_obj.save()
        print(
            style(
                f"Generated baseline with {baseline_obj.count} issue(s)",
                color="green",
            )
            + f" at {baseline_obj.baseline_path}"
        )
        return None

    if args.baseline:
        from slop_lint.core.baseline import Baseline, filter_new_issues

        baseline_path = Path(args.baseline)
        baseline_obj = Baseline(baseline_path)
        if baseline_obj.load():
            workspace = paths[0].parent if paths else Path.cwd()
            original_count = sum(len(issues) for issues in results.values())
            results = filter_new_issues(results, baseline_obj, workspace)
            new_count = sum(len(issues) for issues in results.values())
            if not args.quiet and args.verbose:
                print(
                    style(
                        f"Baseline: {original_count} total, {new_count} new issue(s)",
                        dim=True,
                    )
                )
        else:
            print(
                style(
                    f"Warning: Baseline file not found: {baseline_path}",
                    color="yellow",
                )
            )

    return results


_SEVERITY_COLOR = {
    Severity.ERROR: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "blue",
}


def _output_results(
    results: dict[Path, list[Issue]],
    args: argparse.Namespace,
    rules: list[Rule] | None = None,
) -> int:
    """Format and print results; return exit code."""
    total_issues = sum(len(issues) for issues in results.values())

    if args.format in ("json", "sarif"):
        from slop_lint.core.reporter import Reporter

        reporter = Reporter(format=args.format, rules=rules)
        print(reporter.report(results))
    elif not results:
        if not args.quiet:
            print(style("\u2713", color="green") + " No issues found!")
    else:
        for file_path, issues in results.items():
            for issue in issues:
                sev_color = _SEVERITY_COLOR[issue.severity]
                conf_tag = ""
                is_bold = False
                is_dim = False
                severity_text = issue.severity.value
                if issue.confidence == Confidence.LOW:
                    conf_tag = " [low]"
                    is_dim = True
                elif issue.confidence == Confidence.HIGH:
                    conf_tag = " [high]"
                    is_bold = True
                rule_part = style(f"{issue.rule_id}{conf_tag}", color=sev_color)
                line_text = (
                    f"{style(str(file_path), bold=True)}"
                    f":{issue.line}:{issue.column}: "
                    f"{rule_part} [{severity_text}] {issue.message}"
                )
                if is_dim:
                    line_text = style(line_text, dim=True)
                elif is_bold:
                    line_text = style(line_text, bold=True)
                print(line_text)
        if not args.quiet:
            print(style(f"\nFound {total_issues} issue(s)", bold=True))

    return 1 if total_issues > 0 else 0


def _cmd_check(args: argparse.Namespace) -> int:
    """Check files for bad writing practices."""
    paths = [Path(p) for p in args.paths]
    path_error = _validate_existing_paths(paths)
    if path_error is not None:
        return path_error

    config_path = Path(args.config) if args.config else None

    # Load config
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    # Apply CLI overrides
    if args.select:
        config.select = args.select.split(",")
    if args.ignore:
        ignore_list = args.ignore.split(",")
        config.ignore = list(set(config.ignore) | set(ignore_list))

    # Handle --show-config
    if args.show_config:
        print(style("Configuration:", bold=True))
        print(f"  Config file: {config_path or 'default'}")
        print(f"  Select: {config.select}")
        print(f"  Ignore: {config.ignore}")
        print(f"  Include patterns: {config.include}")
        print(f"  Exclude patterns: {config.exclude}")
        config_severity = args.severity or config.severity
        print(f"  Severity threshold: {config_severity}")
        if config.severity_overrides:
            print(f"  Severity overrides: {config.severity_overrides}")
        print(f"  Output format: {args.format}")
        return 0

    # Create linter and register rules
    linter = Linter(config)
    min_severity = severity_from_str(args.severity or config.severity, Severity.WARNING)
    if min_severity is None:  # pragma: no cover
        min_severity = Severity.WARNING

    active_rules: list[Rule] = []
    for rule in get_all_rules(config):
        if severity_rank(rule.severity) >= severity_rank(min_severity):
            linter.register_rule(rule)
            active_rules.append(rule)

    # Run checks
    try:
        results = linter.check(paths)
    except LintReadError as exc:
        print(f"Could not read file: {exc}", file=sys.stderr)
        return 3

    # Filter by confidence level
    results = _filter_by_confidence(results, args, config)

    # Handle baseline mode
    baseline_result = _apply_baseline(results, args, paths)
    if baseline_result is None:
        return 0
    results = baseline_result

    return _output_results(results, args, rules=active_rules)


def _cmd_rules(_args: argparse.Namespace) -> int:
    """List all available rules."""
    all_rules = get_all_rules()

    headers = ["ID", "Name", "Severity", "Description"]
    rows = [[r.id, r.name, r.severity.name, r.description] for r in all_rules]
    print(table(headers, rows, title="Available Rules"))
    return 0


def _cmd_init(_args: argparse.Namespace) -> int:
    """Create a .slop-lint.toml config file."""
    config_file = Path(".slop-lint.toml")
    if config_file.exists():
        print(f"Config file already exists: {config_file}", file=sys.stderr)
        return 2

    default_config = """\
# slop-lint configuration
# See: https://github.com/slop-lint/slop-lint

[tool.slop-lint]
# include = ["*.md", "*.mdx", "*.markdown", "*.py"]
# exclude = ["venv/**", ".venv/**", "node_modules/**", ".git/**"]
# select = ["V", "S", "T", "G", "C", "M"]
# ignore = ["T003"]
severity = "warning"  # Minimum severity: error, warning, info

# Per-rule severity overrides
# NOTE: TOML does not allow both `severity = "warning"` and the table below.
# If you use overrides, remove the `severity` line above.
# [tool.slop-lint.severity]
# V001 = "error"

[tool.slop-lint.vocabulary]
# additional = ["synergy", "leverage"]
# allowed = ["crucial"]

[[tool.slop-lint.per-file-ignores]]
# pattern = "tests/*"
# ignore = ["V001", "V002"]
"""
    config_file.write_text(default_config)
    print(f"Created {config_file}")
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    """Explain a specific rule with examples."""
    all_rules = get_all_rules()
    rule = next((r for r in all_rules if r.id == args.rule_id.upper()), None)

    if rule is None:
        print(f"Unknown rule: {args.rule_id}", file=sys.stderr)
        return 1

    print(f"{style(rule.id, bold=True, color='cyan')}: {rule.name}")
    print(f"\n{style('Description:', bold=True)}\n{rule.description}")
    print(f"\n{style('Severity:', bold=True)} {rule.severity.name}")
    return 0


def _cmd_version(_args: argparse.Namespace) -> int:
    """Show version information."""
    from slop_lint import __version__

    print(f"slop-lint {__version__}")
    return 0


def _cmd_watch(args: argparse.Namespace) -> int:
    """Watch files for changes and report issues continuously."""
    paths = [Path(p) for p in args.paths]
    path_error = _validate_existing_paths(paths)
    if path_error is not None:
        return path_error

    config_path = Path(args.config) if args.config else None

    # Load config
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    # Apply CLI overrides
    if args.select:
        config.select = args.select.split(",")
    if args.ignore:
        ignore_list = args.ignore.split(",")
        config.ignore = list(set(config.ignore) | set(ignore_list))

    # Create linter and register rules
    linter = Linter(config)
    for rule in get_all_rules(config):
        linter.register_rule(rule)

    # Track file modification times
    file_mtimes: dict[Path, float] = {}

    print(
        style(f"Watching {len(paths)} path(s)...", bold=True) + " Press Ctrl+C to stop"
    )

    try:
        while True:
            # Discover all files
            files = linter.discover_files(paths)
            changed_files: list[Path] = []

            # Check for modified files
            for file in files:
                try:
                    mtime = file.stat().st_mtime
                    if file not in file_mtimes or file_mtimes[file] < mtime:
                        file_mtimes[file] = mtime
                        changed_files.append(file)
                except OSError:
                    continue  # File may have been deleted

            if changed_files:
                if not args.no_clear:
                    clear_screen()

                print(
                    style(time.strftime("%H:%M:%S"), dim=True)
                    + f" Checking {len(changed_files)} changed file(s)..."
                )

                total_issues = 0
                for file in changed_files:
                    try:
                        issues = linter.check_file(file)
                        total_issues += len(issues)

                        for issue in issues:
                            sev_color = _SEVERITY_COLOR[issue.severity]
                            print(
                                f"{style(str(file), bold=True)}"
                                f":{issue.line}:{issue.column}: "
                                f"{style(issue.rule_id, color=sev_color)} "
                                f"{issue.message}"
                            )
                    except Exception as e:
                        print(style(f"Error checking {file}: {e}", color="red"))

                if total_issues == 0:
                    print(style("\u2713", color="green") + " No issues found!")
                else:
                    print(style(f"\nFound {total_issues} issue(s)", bold=True))

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print(style("\nStopped watching.", color="yellow"))
        return 0


# ---------------------------------------------------------------------------
# Argument parser construction
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="slop-lint",
        description="Detect bad writing practices in Markdown and Python files.",
        add_help=False,
    )
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- check ---
    p_check = subparsers.add_parser(
        "check",
        help="Check files for bad writing practices",
        add_help=False,
    )
    p_check.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    p_check.add_argument("paths", nargs="+", help="Files or directories to check")
    p_check.add_argument(
        "--show-config", action="store_true", help="Display configuration and exit"
    )
    p_check.add_argument(
        "--format",
        "-f",
        choices=("text", "json", "sarif"),
        default="text",
        help="Output format: text, json, sarif",
    )
    p_check.add_argument(
        "--select", "-s", default=None, help="Rules to enable (comma-separated)"
    )
    p_check.add_argument(
        "--ignore", "-i", default=None, help="Rules to disable (comma-separated)"
    )
    p_check.add_argument(
        "--config", "-c", default=None, help="Path to configuration file"
    )
    p_check.add_argument(
        "--severity",
        choices=("error", "warning", "info"),
        default=None,
        help="Minimum severity: error, warning, info",
    )
    p_check.add_argument(
        "--quiet", "-q", action="store_true", help="Only output errors"
    )
    p_check.add_argument(
        "--verbose", "-v", action="store_true", help="Show additional diagnostic info"
    )
    p_check.add_argument(
        "--baseline", "-b", default=None, help="Baseline file for only-new-issues mode"
    )
    p_check.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Generate baseline file from current issues",
    )
    p_check.add_argument(
        "--min-confidence",
        choices=("high", "medium", "low"),
        default=None,
        help="Minimum confidence: high, medium, low",
    )
    p_check.add_argument(
        "--hide-low",
        action="store_true",
        help="Hide low-confidence issues (shorthand for --min-confidence medium)",
    )
    p_check.set_defaults(func=_cmd_check)

    # --- rules ---
    p_rules = subparsers.add_parser(
        "rules", help="List all available rules", add_help=False
    )
    p_rules.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    p_rules.set_defaults(func=_cmd_rules)

    # --- init ---
    p_init = subparsers.add_parser(
        "init", help="Create a .slop-lint.toml config file", add_help=False
    )
    p_init.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    p_init.set_defaults(func=_cmd_init)

    # --- explain ---
    p_explain = subparsers.add_parser(
        "explain", help="Explain a specific rule with examples", add_help=False
    )
    p_explain.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    p_explain.add_argument("rule_id", help="Rule ID (e.g., V001)")
    p_explain.set_defaults(func=_cmd_explain)

    # --- version ---
    p_version = subparsers.add_parser(
        "version", help="Show version information", add_help=False
    )
    p_version.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    p_version.set_defaults(func=_cmd_version)

    # --- watch ---
    p_watch = subparsers.add_parser(
        "watch",
        help="Watch files for changes and report issues continuously",
        add_help=False,
    )
    p_watch.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    p_watch.add_argument("paths", nargs="+", help="Files or directories to watch")
    p_watch.add_argument(
        "--select", "-s", default=None, help="Rules to enable (comma-separated)"
    )
    p_watch.add_argument(
        "--ignore", "-i", default=None, help="Rules to disable (comma-separated)"
    )
    p_watch.add_argument(
        "--config", "-c", default=None, help="Path to configuration file"
    )
    p_watch.add_argument(
        "--interval", "-n", type=float, default=2.0, help="Check interval in seconds"
    )
    p_watch.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear screen between checks",
    )
    p_watch.set_defaults(func=_cmd_watch)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 2

    return args.func(args)  # type: ignore[no-any-return]


if __name__ == "__main__":
    sys.exit(main())
