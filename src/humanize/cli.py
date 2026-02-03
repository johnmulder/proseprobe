"""Command-line interface for humanize."""

import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from humanize.config import load_config
from humanize.core.linter import Linter
from humanize.rules import get_all_rules
from humanize.rules.base import Severity, severity_rank

app = typer.Typer(
    name="humanize",
    help="Detect AI-generated content patterns in Markdown and Python files.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


def _severity_from_str(s: str) -> Severity:
    """Convert string to Severity enum."""
    mapping = {
        "error": Severity.ERROR,
        "warning": Severity.WARNING,
        "info": Severity.INFO,
        "off": Severity.OFF,
    }
    return mapping.get(s.lower(), Severity.WARNING)


@app.command()
def check(
    paths: Annotated[
        list[Path],
        typer.Argument(help="Files or directories to check"),
    ],
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Apply auto-fixes for fixable issues"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Show what fixes would be applied without writing"
        ),
    ] = False,
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
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive", "-I", help="Interactively confirm each fix"
        ),
    ] = False,
) -> None:
    """Check files for AI content patterns."""
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
        console.print(f"  Fix mode: {fix}")
        console.print(f"  Dry run: {dry_run}")
        raise typer.Exit(0)

    # Create linter and register rules
    linter = Linter(config)
    min_severity = _severity_from_str(severity or config.severity)

    for rule in get_all_rules(config):
        # Filter by severity
        if severity_rank(rule.severity) >= severity_rank(min_severity):
            linter.register_rule(rule)

    # Run checks
    results = linter.check(paths)

    # Handle baseline mode
    if generate_baseline:
        from humanize.core.baseline import Baseline

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
        from humanize.core.baseline import Baseline, filter_new_issues

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
            from humanize.core.reporter import Reporter
            reporter = Reporter(format="json")
            print(reporter.report({}))
        elif format == "sarif":
            from humanize.core.reporter import Reporter
            reporter = Reporter(format="sarif")
            print(reporter.report({}))
        elif not quiet:
            console.print("[green]✓[/green] No issues found!")
        raise typer.Exit(0)

    # Handle --fix mode
    if fix:
        from humanize.core.fixer import Fixer

        fixer = Fixer(get_all_rules(config))
        total_fixed = 0
        total_skipped = 0

        for file_path, issues in results.items():
            fixable = [i for i in issues if i.fixable]
            if not fixable:
                continue

            if dry_run:
                # Show what would be fixed without modifying
                content, num_fixes = fixer.fix_file(file_path, issues)
                if num_fixes > 0:
                    console.print(
                        f"[bold]{file_path}[/bold]: Would fix {num_fixes} issue(s)"
                    )
                    if verbose:
                        for issue in fixable:
                            console.print(f"  - {issue.rule_id}: {issue.message}")
            elif interactive:
                # Interactive mode: prompt for each fix
                content = file_path.read_text(encoding="utf-8")
                file_fixed = 0

                # Sort by position (reverse) for safe application
                fixable.sort(key=lambda i: (i.line, i.column), reverse=True)

                for issue in fixable:
                    # Show context
                    lines = content.split("\n")
                    line_idx = issue.line - 1
                    start = max(0, line_idx - 1)
                    end = min(len(lines), line_idx + 2)

                    console.print(f"\n[bold]{file_path}:{issue.line}[/bold]")
                    console.print(f"[cyan]{issue.rule_id}[/cyan]: {issue.message}")
                    if issue.suggestion:
                        console.print(f"[green]Suggestion:[/green] {issue.suggestion}")
                    console.print("\n[dim]Context:[/dim]")
                    for i, line in enumerate(lines[start:end], start=start + 1):
                        marker = "→" if i == issue.line else " "
                        console.print(f"  {marker} {i:4d} | {line}")

                    # Prompt user
                    response = typer.prompt(
                        "\nApply fix? [y]es / [n]o / [a]ll / [q]uit",
                        default="y",
                    ).lower()

                    if response in ("y", "yes"):
                        fix_rule = fixer._rules.get(issue.rule_id)
                        if fix_rule:
                            new_content = fix_rule.fix(content, issue)
                            if new_content != content:
                                content = new_content
                                file_fixed += 1
                                console.print("[green]✓ Fixed[/green]")
                    elif response in ("a", "all"):
                        # Fix this and all remaining
                        fix_rule = fixer._rules.get(issue.rule_id)
                        if fix_rule:
                            new_content = fix_rule.fix(content, issue)
                            if new_content != content:
                                content = new_content
                                file_fixed += 1

                        # Fix remaining without prompting
                        remaining = fixable[fixable.index(issue) + 1 :]
                        for rem_issue in remaining:
                            rem_rule = fixer._rules.get(rem_issue.rule_id)
                            if rem_rule:
                                new_content = rem_rule.fix(content, rem_issue)
                                if new_content != content:
                                    content = new_content
                                    file_fixed += 1
                        console.print(
                            "[green]✓ Applied all remaining fixes[/green]"
                        )
                        break
                    elif response in ("q", "quit"):
                        console.print("[yellow]Quitting...[/yellow]")
                        if file_fixed > 0:
                            file_path.write_text(content, encoding="utf-8")
                            total_fixed += file_fixed
                        raise typer.Exit(0)
                    else:
                        total_skipped += 1
                        console.print("[dim]Skipped[/dim]")

                # Write changes for this file
                if file_fixed > 0:
                    file_path.write_text(content, encoding="utf-8")
                    total_fixed += file_fixed
                    console.print(
                        f"\n[bold]{file_path}[/bold]: Fixed {file_fixed} issue(s)"
                    )
            else:
                # Actually apply fixes
                num_fixes = fixer.fix_and_write(file_path, issues)
                if num_fixes > 0:
                    console.print(
                        f"[bold]{file_path}[/bold]: Fixed {num_fixes} issue(s)"
                    )
                total_fixed += num_fixes

        if dry_run:
            console.print("\n[yellow]Dry run:[/yellow] No files were modified.")
            raise typer.Exit(0)
        elif total_fixed > 0:
            msg = f"Fixed {total_fixed} issue(s)"
            if interactive and total_skipped > 0:
                msg += f", skipped {total_skipped}"
            console.print(f"\n[green]{msg}[/green]")
            raise typer.Exit(0)

    # Output results
    total_issues = sum(len(issues) for issues in results.values())

    if format == "json":
        from humanize.core.reporter import Reporter
        reporter = Reporter(format="json")
        print(reporter.report(results))
    elif format == "sarif":
        from humanize.core.reporter import Reporter
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
                console.print(
                    f"[bold]{file_path}[/bold]:{issue.line}:{issue.column}: "
                    f"[{severity_color}]{issue.rule_id}[/{severity_color}] "
                    f"{issue.message}"
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
    """Create a .humanize.toml config file."""
    config_path = Path(".humanize.toml")
    if config_path.exists():
        typer.echo(f"Config file already exists: {config_path}", err=True)
        raise typer.Exit(2)

    default_config = """# humanize configuration
# See: https://github.com/humanize-cli/humanize

[tool.humanize]
# include = ["*.md", "*.py"]
# exclude = ["venv/**", ".venv/**", "node_modules/**", ".git/**"]
# select = ["V", "S", "T", "G", "C", "M"]
# ignore = ["T003"]
severity = "warning"  # Minimum severity: error, warning, info

# Per-rule severity overrides
# NOTE: TOML does not allow both `severity = "warning"` and the table below.
# If you use overrides, remove the `severity` line above.
# [tool.humanize.severity]
# V001 = "error"

[tool.humanize.vocabulary]
# additional = ["synergy", "leverage"]
# allowed = ["crucial"]

[[tool.humanize.per-file-ignores]]
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
    console.print(f"\n[bold]Fixable:[/bold] {'Yes' if rule.fixable else 'No'}")


@app.command()
def version() -> None:
    """Show version information."""
    from humanize import __version__

    typer.echo(f"humanize {__version__}")


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
