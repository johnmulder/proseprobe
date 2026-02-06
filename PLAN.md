# Slop Lint — Development Plan

## Phase 7 — Remove auto-fix mechanisms  *(done)*

### Rationale

Auto-fix is a liability for a *style* linter that flags fuzzy, heuristic
matches.  A vocabulary substitution like "utilize → use" can be wrong in
quoted material, code identifiers, or domain-specific prose.  Silently
rewriting files (even with `--dry-run`) implies a level of certainty the
rules do not have.  Removing fix support simplifies the codebase, reduces
the maintenance surface, and positions slop-lint clearly as a *diagnostic*
tool — it tells you what to look at; you decide what to change.

### Implementation order

1. Delete `core/fixer.py` and update `core/__init__.py`.
2. Remove `fixable` attribute and `fix()` from `Rule` base class.
3. Remove `fixable` field from `Issue` dataclass.
4. Strip `fixable = True/False`, `fix()` methods, and `fixable=…`
   keyword args from all rule classes.
5. Remove `"fixable"` from reporter JSON/SARIF output.
6. Remove `--fix`, `--dry-run`, `--interactive` from CLI and all
   associated logic.
7. Delete `tests/test_fixer.py`; update remaining test files.
8. Update SPEC.md, README.md, docs/configuration.md, CHANGELOG.md.
9. Run full test suite and `make all` to verify clean state.

---

## Phase 8 — Remove external dependencies  *(done)*

### Rationale

slop-lint currently declares four runtime dependencies:

| Package | Why declared | Actually used? |
|---------|-------------|----------------|
| **typer** | CLI framework | Yes — argument parsing, subcommands, `typer.Exit` |
| **rich** | Coloured terminal output | Yes — `Console.print()` with markup, `Table` |
| **mistune** | Markdown AST parsing | **No** — never imported; parser is hand-written regex |
| **regex** | Extended regex engine | **No** — never imported; stdlib `re` used everywhere |

Two dependencies (`mistune`, `regex`) are dead weight — declared but never
imported.  The other two (`typer`, `rich`) are large transitive trees for
functionality that stdlib `argparse` and ANSI escape codes can provide.

Removing all four would make slop-lint a **zero-dependency** tool:
faster install, no supply-chain risk, trivially vendorable, and one fewer
reason for users to hesitate before adding it to CI.

### 8.1 Drop `mistune` and `regex` (dead dependencies)

These are never imported anywhere in `src/` or `tests/`.  Simply remove
them from `pyproject.toml` `[project] dependencies`.

- **Risk:** None.  No code references them.
- **Effort:** One-line edit.

### 8.2 Replace `rich` with ANSI helpers

`rich` is used in exactly one file (`cli.py`) for two things:

1. **`Console.print()` with markup** — `[bold]`, `[dim]`, `[red]`, etc.
2. **`Table`** — used once, in the `rules` subcommand.

**Replacement strategy:**

- Write a small `_ansi.py` module (< 80 lines) with:
  - `style(text, *, bold=False, dim=False, color=None) -> str` — wraps text
    in ANSI SGR codes; returns plain text when `NO_COLOR` env var is set or
    stdout is not a TTY.
  - `table(headers, rows) -> str` — formats a list of rows into aligned
    columns with optional header underline.
- Convert all `console.print(f"[bold]…[/bold]")` calls to
  `print(style("…", bold=True))`.
- Convert the `Table` usage in `rules` to `print(table(...))`.
- Respect the `NO_COLOR` convention (https://no-color.org).

**Risk:** Lose some niceties (auto line-wrapping, hyperlinks).  Acceptable
for a CLI linter.

### 8.3 Replace `typer` with `argparse`

`typer` is used for:

- **Subcommands:** `check`, `rules`, `explain`, `init`, `version`, `watch`.
- **Typed arguments/options:** `Annotated[..., typer.Option(...)]`.
- **Exit codes:** `raise typer.Exit(n)`.
- **`typer.echo`** — thin wrapper around `print`.

**Replacement strategy:**

- Use `argparse.ArgumentParser` with `add_subparsers()` for subcommands.
- Each current `@app.command()` function becomes a handler attached via
  `set_defaults(func=handler)`.
- `Annotated[..., typer.Option("--foo")]` → `parser.add_argument("--foo")`.
- `raise typer.Exit(n)` → `sys.exit(n)`.
- `typer.echo(msg)` → `print(msg)`.
- The entry point (`slop-lint = "slop_lint.cli:main"`) calls
  `parser.parse_args()` then dispatches to the handler.

**Risk:** Tests use `typer.testing.CliRunner`.  Replace with
`subprocess.run(["slop-lint", ...])` or refactor each command to accept
a parsed namespace so tests call the function directly and inspect the
return value / captured stdout.

### 8.4 Test migration

- Replace `from typer.testing import CliRunner` with a lightweight
  test helper that calls `cli.main()` with captured `sys.argv` and
  `sys.stdout` (using `contextlib.redirect_stdout` + `io.StringIO`).
- Alternatively, use `subprocess.run` for integration tests.
- All existing test assertions (exit code, stdout content) carry over
  unchanged.

### 8.5 Implementation order

1. Remove `mistune` and `regex` from `pyproject.toml` dependencies.
   Run `make all` to verify nothing breaks.
2. Create `src/slop_lint/_ansi.py` with `style()` and `table()` helpers.
3. Replace all `rich` usage in `cli.py` with `_ansi` helpers.
   Remove `rich` from `pyproject.toml`.
4. Replace `typer` with `argparse` in `cli.py`.
   Update entry point in `pyproject.toml`.
   Remove `typer` from `pyproject.toml`.
5. Migrate CLI tests from `CliRunner` to direct function calls or
   `subprocess.run`.
6. Run `make all`, verify zero dependencies, commit.
