"""Command-line interface for ProseProbe."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from proseprobe import __version__
from proseprobe._ansi import clear_screen, style, table
from proseprobe.config import ConfigError, load_config
from proseprobe.core.baseline import Baseline, filter_new_issues, resolve_workspace
from proseprobe.core.linter import Linter, LintReadError, LintResults
from proseprobe.core.policy import filter_by_confidence, prepare_scan
from proseprobe.core.reporter import JSON_SCHEMA_VERSION
from proseprobe.profiles import PROFILES
from proseprobe.rules import (
    get_rule_metadata,
    get_rule_metadata_by_id,
)
from proseprobe.rules.base import (
    Issue,
    Rule,
    RuleMetadata,
    Severity,
)

if TYPE_CHECKING:
    from proseprobe.config import Config


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
    return filter_by_confidence(results, effective_confidence)


def _load_requested_baseline(args: argparse.Namespace) -> Baseline | None:
    """Load an explicitly requested filtering baseline once."""
    if not args.baseline or args.generate_baseline:
        return None
    baseline = Baseline(Path(args.baseline))
    if not baseline.load():
        raise ConfigError(baseline.baseline_path, "baseline file not found")
    return baseline


def _apply_baseline(
    lint_results: LintResults,
    args: argparse.Namespace,
    baseline: Baseline | None,
    workspace: Path,
) -> LintResults | None:
    """Generate or apply a preloaded baseline after all other scan filters."""
    results = lint_results.issues_by_file
    if args.generate_baseline:
        generated = Baseline(Path(args.baseline) if args.baseline else None)
        for file_path, issues in results.items():
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise LintReadError(file_path, str(exc)) from exc
            for issue in issues:
                generated.add_issue(issue, file_path, content, workspace)
        generated.save()
        print(
            style(f"Generated baseline with {generated.count} issue(s)", color="green")
            + f" at {generated.baseline_path}"
        )
        return None

    if baseline is None:
        return lint_results

    original_count = sum(len(issues) for issues in results.values())
    filtered = filter_new_issues(results, baseline, workspace)
    new_count = sum(len(issues) for issues in filtered.values())
    if not args.quiet and args.verbose:
        print(
            style(
                f"Baseline: {original_count} total, {new_count} new issue(s)",
                dim=True,
            ),
            file=sys.stderr,
        )
    return LintResults(filtered, files_checked=lint_results.files_checked)


def _prepare_scan(args: argparse.Namespace) -> tuple[Config, Linter, list[Rule]]:
    """Load config and build a linter with the effective active rules."""
    config_path = Path(args.config) if args.config else None
    return prepare_scan(
        load_config(config_path),
        profile=args.profile,
        select=args.select,
        ignore=args.ignore,
        severity=args.severity,
        min_confidence=args.min_confidence,
        hide_low=args.hide_low,
    )


def _scan_paths(
    linter: Linter,
    paths: list[Path],
    args: argparse.Namespace,
    config: Config,
) -> LintResults:
    """Scan paths and apply all non-baseline filters."""
    lint_results = linter.check(paths)
    results = _filter_by_confidence(lint_results.issues_by_file, args, config)
    return LintResults(results, files_checked=lint_results.files_checked)


def _scan_content(
    linter: Linter,
    content: str,
    path: Path,
    args: argparse.Namespace,
    config: Config,
) -> LintResults:
    """Scan one in-memory document and apply non-baseline filters."""
    issues = linter.check_content(content, path)
    results = {path: issues} if issues else {}
    filtered = _filter_by_confidence(results, args, config)
    return LintResults(filtered, files_checked=1)


def _has_failing_issue(results: dict[Path, list[Issue]]) -> bool:
    """Return True when any issue should make the process fail."""
    return any(
        issue.severity in {Severity.ERROR, Severity.WARNING}
        for issues in results.values()
        for issue in issues
    )


def _output_results(
    lint_results: LintResults,
    args: argparse.Namespace,
    rules: list[Rule] | None = None,
) -> int:
    """Format and print results; return exit code."""
    from proseprobe.core.reporter import format_results

    output = format_results(
        lint_results.issues_by_file,
        args.format,
        rules,
        lint_results.files_checked,
        quiet=args.quiet,
    )
    if output:
        print(output, end="" if args.format == "jsonl" else "\n")

    return 1 if _has_failing_issue(lint_results.issues_by_file) else 0


def _cmd_check(args: argparse.Namespace) -> int:
    """Check files for prose and documentation problems."""
    stdin_requested = "-" in args.paths
    if stdin_requested and args.paths != ["-"]:
        print(
            "Standard input '-' cannot be combined with file paths",
            file=sys.stderr,
        )
        return 2
    if stdin_requested and not args.filename:
        print("--filename is required with standard input", file=sys.stderr)
        return 2
    if not stdin_requested and args.filename is not None:
        print(
            "--filename can only be used with standard input '-'",
            file=sys.stderr,
        )
        return 2
    if stdin_requested and (args.baseline or args.generate_baseline):
        print("Baselines are not supported with standard input", file=sys.stderr)
        return 2

    paths = [] if stdin_requested else [Path(path) for path in args.paths]
    path_error = _validate_existing_paths(paths)
    if path_error is not None:
        return path_error

    try:
        config, linter, active_rules = _prepare_scan(args)
        baseline = _load_requested_baseline(args)
        workspace = Path.cwd() if stdin_requested else resolve_workspace(paths)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.show_config:
        print(style("Configuration:", bold=True))
        print(f"  Config file: {config.source_path or 'default'}")
        print(f"  Profile: {config.profile or 'default'}")
        print(f"  Markdown anchor style: {config.markdown_anchor_style}")
        print(f"  Local links: {config.local_links}")
        print(f"  Project root: {config.project_root}")
        print(f"  Local link exclude: {config.local_link_exclude}")
        print(f"  Select: {config.select}")
        print(f"  Ignore: {config.ignore}")
        print(f"  Include patterns: {config.include}")
        print(f"  Exclude patterns: {config.exclude}")
        config_severity = args.severity or config.severity
        print(f"  Minimum severity: {config_severity}")
        config_confidence = args.min_confidence or (
            "medium" if args.hide_low else config.min_confidence
        )
        print(f"  Minimum confidence: {config_confidence}")
        if config.severity_overrides:
            print(f"  Severity overrides: {config.severity_overrides}")
        if config.per_file_ignores:
            per_file = [
                {"pattern": item.pattern, "ignore": item.ignore}
                for item in config.per_file_ignores
            ]
            print(f"  Per-file ignores: {per_file}")
        print(f"  Output format: {args.format}")
        return 0

    try:
        if stdin_requested:
            content = sys.stdin.read()
            lint_results = _scan_content(
                linter, content, Path(args.filename), args, config
            )
        else:
            lint_results = _scan_paths(linter, paths, args, config)
        baseline_results = _apply_baseline(lint_results, args, baseline, workspace)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except LintReadError as exc:
        print(f"Could not read file: {exc}", file=sys.stderr)
        return 3
    except (OSError, UnicodeError) as exc:
        print(f"Could not read standard input: {exc}", file=sys.stderr)
        return 3
    if baseline_results is None:
        return 0
    return _output_results(baseline_results, args, rules=active_rules)


def _cmd_baseline(args: argparse.Namespace) -> int:
    """Create, update, prune, or summarize a baseline."""
    paths = [Path(path) for path in args.paths]
    path_error = _validate_existing_paths(paths)
    if path_error is not None:
        return path_error

    baseline = Baseline(Path(args.baseline) if args.baseline else None)
    try:
        config, linter, _active_rules = _prepare_scan(args)
        workspace = resolve_workspace(paths)
        if args.action != "create" and not baseline.load():
            raise ConfigError(baseline.baseline_path, "baseline file not found")
        lint_results = _scan_paths(linter, paths, args, config)
        comparison = baseline.compare(lint_results.issues_by_file, workspace)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except (LintReadError, OSError, UnicodeDecodeError) as exc:
        print(f"Could not read file: {exc}", file=sys.stderr)
        return 3

    input_version = baseline.format_version or 2
    try:
        if args.action == "create":
            baseline.replace_entries(comparison.active | comparison.new)
            baseline.save()
        elif args.action == "update":
            retained = (
                comparison.active if input_version == 1 else frozenset(baseline.entries)
            )
            baseline.replace_entries(retained | comparison.new)
            baseline.save()
        elif args.action == "prune":
            baseline.replace_entries(comparison.active)
            baseline.save()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    print(f"Baseline {args.action}: {baseline.baseline_path}")
    print(f"  Format: {input_version}")
    print(f"  Active: {comparison.active_count}")
    print(f"  Stale: {comparison.stale_count}")
    print(f"  New: {comparison.new_count}")
    print(f"  Entries: {baseline.count}")
    return 0


def _serialize_rule_metadata(metadata: RuleMetadata) -> dict[str, object]:
    """Serialize canonical rule metadata for machine-readable output."""
    return {
        "id": metadata.id,
        "category": metadata.category,
        "name": metadata.name,
        "description": metadata.description,
        "default_severity": metadata.default_severity.value,
        "default_confidence": metadata.default_confidence.value,
        "applies_to": list(metadata.applies_to),
        "content_scope": metadata.content_scope,
        "profiles": list(metadata.profiles),
        "config_key": metadata.config_key,
    }


def _cmd_rules(args: argparse.Namespace) -> int:
    """List all available rules."""
    metadata_entries = get_rule_metadata()
    if args.format == "json":
        print(
            json.dumps(
                {
                    "schema_version": JSON_SCHEMA_VERSION,
                    "version": __version__,
                    "rules": [
                        _serialize_rule_metadata(metadata)
                        for metadata in metadata_entries
                    ],
                },
                indent=2,
            )
        )
        return 0

    headers = [
        "ID",
        "Name",
        "Severity",
        "Confidence",
        "Applies To",
        "Scope",
        "Profiles",
        "Config",
        "Description",
    ]
    rows = [
        [
            metadata.id,
            metadata.name,
            metadata.default_severity.name,
            metadata.default_confidence.name,
            ", ".join(metadata.applies_to),
            metadata.content_scope,
            ", ".join(metadata.profiles),
            metadata.config_key or "-",
            metadata.description,
        ]
        for metadata in metadata_entries
    ]
    print(table(headers, rows, title="Available Rules"))
    return 0


def _cmd_init(_args: argparse.Namespace) -> int:
    """Create a .proseprobe.toml config file."""
    config_file = Path(".proseprobe.toml")
    if config_file.exists():
        print(f"Config file already exists: {config_file}", file=sys.stderr)
        return 2

    default_config = """\
# ProseProbe configuration
# See: https://github.com/johnmulder/proseprobe

[tool.proseprobe]
# include = ["*.md", "*.mdx", "*.markdown", "*.py"]
# exclude = ["venv/**", ".venv/**", "node_modules/**", ".git/**"]
# profile = "technical-docs"
# select = ["V", "S", "T", "G", "C", "M"]
# ignore = ["T003"]
minimum_severity = "warning"  # error, warning, info

# Per-rule severity overrides
# [tool.proseprobe.severity]
# V001 = "error"

[tool.proseprobe.vocabulary]
# additional = ["synergy", "leverage"]
# allowed = ["crucial"]

# [[tool.proseprobe.per-file-ignores]]
# pattern = "tests/*"
# ignore = ["V001", "V002"]
"""
    config_file.write_text(default_config)
    print(f"Created {config_file}")
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    """Explain a specific rule with examples."""
    metadata = get_rule_metadata_by_id(args.rule_id)

    if metadata is None:
        print(f"Unknown rule: {args.rule_id}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(
            json.dumps(
                {
                    "schema_version": JSON_SCHEMA_VERSION,
                    "version": __version__,
                    "rule": _serialize_rule_metadata(metadata),
                },
                indent=2,
            )
        )
        return 0

    print(f"{style(metadata.id, bold=True, color='cyan')}: {metadata.name}")
    print(f"\n{style('Description:', bold=True)}\n{metadata.description}")
    print(
        f"\n{style('Severity:', bold=True)} {metadata.default_severity.name}"
        f"\n{style('Confidence:', bold=True)} {metadata.default_confidence.name}"
        f"\n{style('Applies to:', bold=True)} {', '.join(metadata.applies_to)}"
        f"\n{style('Scope:', bold=True)} {metadata.content_scope}"
        f"\n{style('Profiles:', bold=True)} {', '.join(metadata.profiles)}"
        f"\n{style('Configuration:', bold=True)} {metadata.config_key or '-'}"
    )
    return 0


def _cmd_version(_args: argparse.Namespace) -> int:
    """Show version information."""
    print(f"proseprobe {__version__}")
    return 0


def _changed_files(
    linter: Linter,
    paths: list[Path],
    file_stamps: dict[Path, tuple[int, int]],
) -> list[Path]:
    """Return discovered files changed since the previous watch iteration."""
    changed: list[Path] = []
    discovered = linter.discover_files(paths)
    for departed in file_stamps.keys() - set(discovered):
        del file_stamps[departed]
    for file in discovered:
        try:
            stat = file.stat()
        except OSError:
            continue
        stamp = (stat.st_mtime_ns, stat.st_size)
        if file_stamps.get(file) != stamp:
            file_stamps[file] = stamp
            changed.append(file)
    return changed


def _cmd_watch(args: argparse.Namespace) -> int:
    """Watch files for changes and report issues continuously."""
    paths = [Path(p) for p in args.paths]
    path_error = _validate_existing_paths(paths)
    if path_error is not None:
        return path_error

    try:
        config, linter, active_rules = _prepare_scan(args)
        baseline = _load_requested_baseline(args)
        workspace = resolve_workspace(paths)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    file_stamps: dict[Path, tuple[int, int]] = {}
    if not args.quiet:
        print(
            style(f"Watching {len(paths)} path(s)...", bold=True)
            + " Press Ctrl+C to stop"
        )

    try:
        while True:
            changed_files = _changed_files(linter, paths, file_stamps)
            if changed_files:
                if not args.quiet and not args.no_clear:
                    clear_screen()
                if not args.quiet:
                    print(
                        style(time.strftime("%H:%M:%S"), dim=True)
                        + f" Checking {len(changed_files)} changed file(s)..."
                    )
                try:
                    lint_results = _scan_paths(linter, changed_files, args, config)
                    baseline_results = _apply_baseline(
                        lint_results, args, baseline, workspace
                    )
                except ConfigError as exc:
                    print(f"Configuration error: {exc}", file=sys.stderr)
                except LintReadError as exc:
                    print(f"Could not read file: {exc}", file=sys.stderr)
                else:
                    if baseline_results is not None:
                        _output_results(baseline_results, args, rules=active_rules)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        if not args.quiet:
            print(style("\nStopped watching.", color="yellow"))
        return 0


# ---------------------------------------------------------------------------
# Argument parser construction
# ---------------------------------------------------------------------------


def _add_scan_options(parser: argparse.ArgumentParser) -> None:
    """Add options shared by check and watch scans."""
    parser.add_argument(
        "--select", "-s", default=None, help="Rules to enable (comma-separated)"
    )
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILES),
        default=None,
        help="Built-in rule profile",
    )
    parser.add_argument(
        "--ignore", "-i", default=None, help="Rules to disable (comma-separated)"
    )
    parser.add_argument(
        "--config", "-c", default=None, help="Path to configuration file"
    )
    parser.add_argument(
        "--severity",
        choices=("error", "warning", "info"),
        default=None,
        help="Minimum severity: error, warning, info",
    )
    parser.add_argument(
        "--min-confidence",
        choices=("high", "medium", "low"),
        default=None,
        help="Minimum confidence: high, medium, low",
    )
    parser.add_argument(
        "--hide-low",
        action="store_true",
        help="Hide low-confidence issues (shorthand for --min-confidence medium)",
    )
    parser.add_argument(
        "--baseline", "-b", default=None, help="Baseline file for only-new-issues mode"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output errors")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show additional diagnostic info"
    )
    parser.set_defaults(format="text", generate_baseline=False)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="proseprobe",
        description=(
            "A Unix-style linter for common prose, documentation, "
            "and Markdown problems."
        ),
        add_help=False,
    )
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- check ---
    p_check = subparsers.add_parser(
        "check",
        help="Check files for prose and documentation problems",
        add_help=False,
    )
    p_check.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    p_check.add_argument("paths", nargs="+", help="Files or directories to check")
    _add_scan_options(p_check)
    p_check.add_argument(
        "--filename",
        default=None,
        help="Virtual path and file type when reading standard input from '-'",
    )
    p_check.add_argument(
        "--show-config", action="store_true", help="Display configuration and exit"
    )
    p_check.add_argument(
        "--format",
        "-f",
        choices=("text", "json", "jsonl", "sarif"),
        default="text",
        help="Output format: text, json, jsonl, sarif",
    )
    p_check.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Generate baseline file from current issues",
    )
    p_check.set_defaults(func=_cmd_check)

    # --- baseline ---
    p_baseline = subparsers.add_parser(
        "baseline",
        help="Create and maintain a baseline",
        add_help=False,
    )
    p_baseline.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    p_baseline.add_argument(
        "action",
        choices=("create", "update", "prune", "summary"),
        help="Baseline maintenance action",
    )
    p_baseline.add_argument("paths", nargs="+", help="Files or directories to check")
    _add_scan_options(p_baseline)
    p_baseline.set_defaults(func=_cmd_baseline)

    # --- rules ---
    p_rules = subparsers.add_parser(
        "rules", help="List all available rules", add_help=False
    )
    p_rules.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    p_rules.add_argument(
        "--format",
        "-f",
        choices=("text", "json"),
        default="text",
        help="Output format: text, json",
    )
    p_rules.set_defaults(func=_cmd_rules)

    # --- init ---
    p_init = subparsers.add_parser(
        "init", help="Create a .proseprobe.toml config file", add_help=False
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
    p_explain.add_argument(
        "--format",
        "-f",
        choices=("text", "json"),
        default="text",
        help="Output format: text, json",
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
    _add_scan_options(p_watch)
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
