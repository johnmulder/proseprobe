"""Command-line interface for slop-lint."""

import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from slop_lint.config import load_config
from slop_lint.core.linter import Linter
from slop_lint.rules import get_all_rules
from slop_lint.rules.base import Confidence, Severity, severity_from_str, severity_rank

_CONFIDENCE_RANK = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}


def _confidence_rank(confidence: Confidence) -> int:
    """Return numeric rank for confidence comparisons."""
    return _CONFIDENCE_RANK.get(confidence, 0)


def _parse_confidence(value: str) -> Confidence | None:
    """Parse a confidence string into a Confidence enum."""
    mapping = {"high": Confidence.HIGH, "medium": Confidence.MEDIUM, "low": Confidence.LOW}
    return mapping.get(value.lower())


app = typer.Typer(
    name="slop-lint",
    help="Detect bad writing practices in Markdown and Python files.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


@app.command()
def check(
    paths: Annotated[
        list[Path],
        typer.Argument(help="Files or directories to check"),
    ],
    show_config: Annotated[
        bool,
        typer.Option("--show-config", help="Display configuration and exit"),
    ] = False,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text, json, sarif"),
    ] = "text",
    select: Annotated[
        str | None,
        typer.Option("--select", "-s", help="Rules to enable (comma-separated)"),
    ] = None,
    ignore: Annotated[
        str | None,
        typer.Option("--ignore", "-i", help="Rules to disable (comma-separated)"),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to configuration file"),
    ] = None,
    severity: Annotated[
        str | None,
        typer.Option("--severity", help="Minimum severity: error, warning, info"),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Only output errors"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show additional diagnostic info"),
    ] = False,
    baseline: Annotated[
        Path | None,
        typer.Option("--baseline", "-b", help="Baseline file for only-new-issues mode"),
    ] = None,
    generate_baseline: Annotated[
        bool,
        typer.Option(
            "--generate-baseline", help="Generate baseline file from current issues"
        ),
    ] = False,
    min_confidence: Annotated[
        str | None,
        typer.Option(
            "--min-confidence",
            help="Minimum confidence: high, medium, low",
        ),
    ] = None,
    hide_low: Annotated[
        bool,
        typer.Option("--hide-low", help="Hide low-confidence issues (shorthand for --min-confidence medium)"),
    ] = False,
) -> None:
    """Check files for bad writing practices."""
    # Load config
    config = load_config(config_path)

    # Apply CLI overrides
    if select:
        config.select = select.split(",")
    if ignore:
        ignore_list = ignore.split(",")
        config.ignore = list(set(config.ignore) | set(ignore_list))

    # Handle --show-config
    if show_config:
        console.print("[bold]Configuration:[/bold]")
        console.print(f"  Config file: {config_path or 'default'}")
        console.print(f"  Select: {config.select}")
        console.print(f"  Ignore: {config.ignore}")
        console.print(f"  Include patterns: {config.include}")
        console.print(f"  Exclude patterns: {config.exclude}")
        config_severity = severity or config.severity
        console.print(f"  Severity threshold: {config_severity}")
        if config.severity_overrides:
            console.print(f"  Severity overrides: {config.severity_overrides}")
        console.print(f"  Output format: {format}")
        raise typer.Exit(0)

    # Create linter and register rules
    linter = Linter(config)
    min_severity = severity_from_str(severity or config.severity, Severity.WARNING)
    assert min_severity is not None  # default ensures this

    for rule in get_all_rules(config):
        # Filter by severity
        if severity_rank(rule.severity) >= severity_rank(min_severity):
            linter.register_rule(rule)

    # Run checks
    results = linter.check(paths)

    # Filter by confidence level
    effective_confidence = min_confidence or ("medium" if hide_low else config.min_confidence)
    confidence_threshold = _parse_confidence(effective_confidence)
    if confidence_threshold and confidence_threshold != Confidence.LOW:
        results = {
            path: [
                issue
                for issue in issues
                if _confidence_rank(issue.confidence) >= _confidence_rank(confidence_threshold)
            ]
            for path, issues in results.items()
        }
        results = {path: issues for path, issues in results.items() if issues}

    # Handle baseline mode
    if generate_baseline:
        from slop_lint.core.baseline import Baseline

        baseline_obj = Baseline(baseline)
        workspace = paths[0].parent if paths else Path.cwd()

        for file_path, issues in results.items():
            try:
                content = file_path.read_text()
                for issue in issues:
                    baseline_obj.add_issue(issue, file_path, content, workspace)
            except OSError:
                continue

        baseline_obj.save()
        console.print(
            f"[green]Generated baseline with {baseline_obj.count} issue(s)[/green] "
            f"at {baseline_obj.baseline_path}"
        )
        raise typer.Exit(0)

    if baseline:
        from slop_lint.core.baseline import Baseline, filter_new_issues

        baseline_obj = Baseline(baseline)
        if baseline_obj.load():
            workspace = paths[0].parent if paths else Path.cwd()
            original_count = sum(len(issues) for issues in results.values())
            results = filter_new_issues(results, baseline_obj, workspace)
            new_count = sum(len(issues) for issues in results.values())
            if not quiet and verbose:
                console.print(
                    f"[dim]Baseline: {original_count} total, "
                    f"{new_count} new issue(s)[/dim]"
                )
        else:
            console.print(
                f"[yellow]Warning: Baseline file not found: {baseline}[/yellow]"
            )

    if not results:
        if format == "json":
            from slop_lint.core.reporter import Reporter

            reporter = Reporter(format="json")
            print(reporter.report({}))
        elif format == "sarif":
            from slop_lint.core.reporter import Reporter

            reporter = Reporter(format="sarif")
            print(reporter.report({}))
        elif not quiet:
            console.print("[green]✓[/green] No issues found!")
        raise typer.Exit(0)

    # Output results
    total_issues = sum(len(issues) for issues in results.values())

    if format == "json":
        from slop_lint.core.reporter import Reporter

        reporter = Reporter(format="json")
        print(reporter.report(results))
    elif format == "sarif":
        from slop_lint.core.reporter import Reporter

        reporter = Reporter(format="sarif")
        print(reporter.report(results))
    else:
        # Text format (default)
        for file_path, issues in results.items():
            for issue in issues:
                severity_color = {
                    Severity.ERROR: "red",
                    Severity.WARNING: "yellow",
                    Severity.INFO: "blue",
                }[issue.severity]
                conf_tag = ""
                style_open = ""
                style_close = ""
                if issue.confidence == Confidence.LOW:
                    conf_tag = " [low]"
                    style_open = "[dim]"
                    style_close = "[/dim]"
                elif issue.confidence == Confidence.HIGH:
                    conf_tag = " [high]"
                    style_open = "[bold]"
                    style_close = "[/bold]"
                console.print(
                    f"{style_open}[bold]{file_path}[/bold]:{issue.line}:{issue.column}: "
                    f"[{severity_color}]{issue.rule_id}{conf_tag}[/{severity_color}] "
                    f"{issue.message}{style_close}"
                )
        if not quiet:
            console.print(f"\n[bold]Found {total_issues} issue(s)[/bold]")

    # Exit with error code if issues found
    raise typer.Exit(1 if total_issues > 0 else 0)


@app.command()
def rules() -> None:
    """List all available rules."""
    all_rules = get_all_rules()

    table = Table(title="Available Rules")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Severity", style="yellow")
    table.add_column("Description")

    for rule in all_rules:
        table.add_row(rule.id, rule.name, rule.severity.name, rule.description)

    console.print(table)


@app.command()
def init() -> None:
    """Create a .slop-lint.toml config file."""
    config_path = Path(".slop-lint.toml")
    if config_path.exists():
        typer.echo(f"Config file already exists: {config_path}", err=True)
        raise typer.Exit(2)

    default_config = """# slop-lint configuration
# See: https://github.com/slop-lint/slop-lint

[tool.slop-lint]
# include = ["*.md", "*.py"]
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
    config_path.write_text(default_config)
    typer.echo(f"Created {config_path}")


@app.command()
def explain(
    rule_id: Annotated[str, typer.Argument(help="Rule ID (e.g., V001)")],
) -> None:
    """Explain a specific rule with examples."""
    all_rules = get_all_rules()
    rule = next((r for r in all_rules if r.id == rule_id.upper()), None)

    if rule is None:
        typer.echo(f"Unknown rule: {rule_id}", err=True)
        raise typer.Exit(1)

    console.print(f"[bold cyan]{rule.id}[/bold cyan]: {rule.name}")
    console.print(f"\n[bold]Description:[/bold]\n{rule.description}")
    console.print(f"\n[bold]Severity:[/bold] {rule.severity.name}")


@app.command()
def version() -> None:
    """Show version information."""
    from slop_lint import __version__

    typer.echo(f"slop-lint {__version__}")


@app.command()
def watch(
    paths: Annotated[
        list[Path],
        typer.Argument(help="Files or directories to watch"),
    ],
    select: Annotated[
        str | None,
        typer.Option("--select", "-s", help="Rules to enable (comma-separated)"),
    ] = None,
    ignore: Annotated[
        str | None,
        typer.Option("--ignore", "-i", help="Rules to disable (comma-separated)"),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to configuration file"),
    ] = None,
    interval: Annotated[
        float,
        typer.Option("--interval", "-n", help="Check interval in seconds"),
    ] = 2.0,
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Clear screen between checks"),
    ] = True,
) -> None:
    """Watch files for changes and report issues continuously.

    Press Ctrl+C to stop watching.
    """
    # Load config
    config = load_config(config_path)

    # Apply CLI overrides
    if select:
        config.select = select.split(",")
    if ignore:
        ignore_list = ignore.split(",")
        config.ignore = list(set(config.ignore) | set(ignore_list))

    # Create linter and register rules
    linter = Linter(config)
    for rule in get_all_rules(config):
        linter.register_rule(rule)

    # Track file modification times
    file_mtimes: dict[Path, float] = {}
    last_issues: dict[Path, int] = {}

    console.print(f"[bold]Watching {len(paths)} path(s)...[/bold] Press Ctrl+C to stop")

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
                if clear:
                    console.clear()

                console.print(
                    f"[dim]{time.strftime('%H:%M:%S')}[/dim] "
                    f"Checking {len(changed_files)} changed file(s)..."
                )

                total_issues = 0
                for file in changed_files:
                    try:
                        issues = linter.check_file(file)
                        last_issues[file] = len(issues)
                        total_issues += len(issues)

                        for issue in issues:
                            severity_color = {
                                Severity.ERROR: "red",
                                Severity.WARNING: "yellow",
                                Severity.INFO: "blue",
                            }[issue.severity]
                            console.print(
                                f"[bold]{file}[/bold]:{issue.line}:{issue.column}: "
                                f"[{severity_color}]{issue.rule_id}[/{severity_color}] "
                                f"{issue.message}"
                            )
                    except Exception as e:
                        console.print(f"[red]Error checking {file}: {e}[/red]")

                if total_issues == 0:
                    console.print("[green]✓[/green] No issues found!")
                else:
                    console.print(f"\n[bold]Found {total_issues} issue(s)[/bold]")

            time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching.[/yellow]")
        raise typer.Exit(0) from None


if __name__ == "__main__":
    app()
