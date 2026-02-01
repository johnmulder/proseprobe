"""Command-line interface for humanize."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from humanize.config import load_config
from humanize.core.linter import Linter
from humanize.rules import get_all_rules
from humanize.rules.base import Severity

app = typer.Typer(
    name="humanize",
    help="Detect AI-generated content patterns in Markdown and Python files.",
    no_args_is_help=True,
)
console = Console()


def _severity_from_str(s: str) -> Severity:
    """Convert string to Severity enum."""
    mapping = {
        "error": Severity.ERROR,
        "warning": Severity.WARNING,
        "info": Severity.INFO,
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
        typer.Option("--dry-run", help="Show what fixes would be applied without writing"),
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
        str,
        typer.Option("--severity", help="Minimum severity: error, warning, info"),
    ] = "warning",
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Only output errors"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show additional diagnostic info"),
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
        console.print(f"  Severity threshold: {severity}")
        console.print(f"  Output format: {format}")
        console.print(f"  Fix mode: {fix}")
        console.print(f"  Dry run: {dry_run}")
        raise typer.Exit(0)

    # Create linter and register rules
    linter = Linter(config)
    min_severity = _severity_from_str(severity)

    for rule in get_all_rules():
        # Filter by severity
        if rule.severity.value >= min_severity.value:
            linter.register_rule(rule)

    # Run checks
    results = linter.check(paths)

    if not results:
        if not quiet:
            console.print("[green]✓[/green] No issues found!")
        raise typer.Exit(0)

    # Handle --fix mode
    if fix:
        from humanize.core.fixer import Fixer

        fixer = Fixer(get_all_rules())
        total_fixed = 0

        for file_path, issues in results.items():
            fixable = [i for i in issues if i.fixable]
            if not fixable:
                continue

            if dry_run:
                # Show what would be fixed without modifying
                content, num_fixes = fixer.fix_file(file_path, issues)
                if num_fixes > 0:
                    console.print(f"[bold]{file_path}[/bold]: Would fix {num_fixes} issue(s)")
                    if verbose:
                        for issue in fixable:
                            console.print(f"  - {issue.rule_id}: {issue.message}")
            else:
                # Actually apply fixes
                num_fixes = fixer.fix_and_write(file_path, issues)
                if num_fixes > 0:
                    console.print(f"[bold]{file_path}[/bold]: Fixed {num_fixes} issue(s)")
                total_fixed += num_fixes

        if dry_run:
            console.print("\n[yellow]Dry run:[/yellow] No files were modified.")
            raise typer.Exit(0)
        elif total_fixed > 0:
            console.print(f"\n[green]Fixed {total_fixed} issue(s)[/green]")
            raise typer.Exit(0)

    # Output results
    total_issues = 0
    for file_path, issues in results.items():
        total_issues += len(issues)
        if format == "text":
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

[lint]
# select = ["V001", "V002"]  # Only enable specific rules
# ignore = ["T003"]  # Disable specific rules
severity = "warning"  # Minimum severity: error, warning, info

[format]
output = "text"  # Output format: text, json, sarif

# [lint.per-file-ignores]
# "tests/*" = ["V001", "V002"]
# "docs/*" = ["S001"]
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


if __name__ == "__main__":
    app()
