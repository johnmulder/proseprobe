# Slop-Lint Quality and Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve slop-lint's release reliability, CLI correctness, reporting accuracy, dogfood signal quality, and documentation alignment without broad feature expansion.

**Architecture:** Work in small, reversible slices. Fix automation and packaging metadata first, then harden CLI validation and error handling, then correct result accounting and exit semantics, then reduce Markdown false positives, and finally refresh docs and benchmark signals. Preserve the current zero-runtime-dependency design and the existing argparse-based CLI.

**Tech Stack:** Python 3.11+, argparse, pathlib, tomllib, pytest, pytest-cov, ruff, mypy, GitHub Actions, pre-commit.

---

## Slow, Safe, Checked Progress Rules

- [ ] Start on a clean branch named `codex/quality-reliability-plan`.
- [ ] Before each task, run `git status --short` and confirm only expected files are dirty.
- [ ] Write or adjust the smallest failing test first for every behavior change.
- [ ] Run the specific test that proves the change before running broader checks.
- [ ] Commit after each task passes its listed verification.
- [ ] Keep every commit narrow enough to revert independently.
- [ ] Do not modify rule behavior while fixing CI, docs, pre-commit, or packaging metadata.
- [ ] Do not modify docs to hide failing product behavior; fix product behavior first unless the docs are plainly stale.
- [ ] Stop and investigate any unexpected traceback, changed public output shape, or unrelated test failure before continuing.

## File Structure

- Modify `.github/workflows/ci.yml`: correct package names, coverage source, dogfood command, and build verification.
- Modify `.pre-commit-hooks.yaml`: replace stale `humanize` hook metadata with `slop-lint` hooks that match implemented CLI behavior.
- Modify `src/slop_lint/cli.py`: validate CLI choices, map expected failures to documented exit codes, honor quiet mode, and calculate exit code by severity.
- Modify `src/slop_lint/config.py`: expose a friendly configuration-loading exception with path context.
- Modify `src/slop_lint/core/linter.py`: report missing files and file read/decode failures without tracebacks, and track checked file counts.
- Modify `src/slop_lint/core/reporter.py`: report true checked-file counts in JSON and SARIF-compatible output paths.
- Modify `src/slop_lint/parsers/markdown.py`: add prose extraction that excludes Markdown tables and list marker syntax from sentence-style rules.
- Modify `src/slop_lint/rules/struct.py`: make `S010` operate on actual prose sentences rather than Markdown table rows or list markers.
- Modify `tests/test_cli.py`: cover invalid CLI values, missing paths, quiet output, config errors, invalid UTF-8, and exit-code semantics.
- Modify `tests/test_linter.py`: cover file discovery and read-error result metadata.
- Modify `tests/test_reporter.py`: cover true `files_checked` accounting.
- Modify `tests/test_parsers/test_markdown.py`: cover prose extraction for bullets and tables.
- Modify `tests/test_rules/test_struct.py`: cover `S010` list/table false-positive regressions.
- Modify `Makefile`: align `dogfood`, benchmark, build, and NFR targets with actual project names and commands.
- Modify `benchmarks/bench_rules.py`: rename stale output labels and add a clear files/sec summary.
- Modify `SPEC.md`, `README.md`, `docs/configuration.md`, and `docs/rules.md`: align documented commands, dependencies, tests, hooks, and severity behavior with implementation.

---

### Task 1: Create Branch and Capture Baseline

**Files:**
- No file edits.

- [ ] **Step 1: Create the branch**

Run:

```bash
git switch -c codex/quality-reliability-plan
```

Expected: branch created and checked out.

- [ ] **Step 2: Record the starting status**

Run:

```bash
git status --short --branch
```

Expected: output begins with `## codex/quality-reliability-plan` and has no modified files.

- [ ] **Step 3: Run the baseline checks**

Run:

```bash
make check
make coverage-analyze
make startup-check
```

Expected:

```text
All checks passed!
Success: no issues found in 26 source files
698 passed
Required test coverage of 90% reached
real 0.04
```

The exact startup time may vary by machine; investigate if it is above `0.10`.

- [ ] **Step 4: Reproduce known failures without changing files**

Run:

```bash
make dogfood
.venv/bin/slop-lint check --severity banana tests/fixtures/human_written/sample2.py
.venv/bin/slop-lint check --format xml tests/fixtures/human_written/sample2.py
.venv/bin/slop-lint check /private/tmp/does-not-exist.md
```

Expected current behavior before fixes:

```text
make dogfood
# exits non-zero with current docs issues

.venv/bin/slop-lint check --severity banana tests/fixtures/human_written/sample2.py
# exits 0 and silently accepts invalid severity

.venv/bin/slop-lint check --format xml tests/fixtures/human_written/sample2.py
# exits 0 and silently falls back to text

.venv/bin/slop-lint check /private/tmp/does-not-exist.md
# exits 0 and prints No issues found
```

- [ ] **Step 5: Commit baseline note only if a file was intentionally created**

No commit is expected for this task.

---

### Task 2: Fix CI and Pre-Commit Rename Drift

**Files:**
- Modify `.github/workflows/ci.yml`
- Modify `.pre-commit-hooks.yaml`

- [ ] **Step 1: Write workflow metadata checks**

Create a new test in `tests/test_project_metadata.py`:

```python
"""Project metadata regression tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_uses_slop_lint_names() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "--cov=src/slop_lint" in workflow
    assert "slop-lint check README.md docs/" in workflow
    assert "humanize" not in workflow
    assert "src/humanize" not in workflow


def test_pre_commit_hook_uses_existing_cli() -> None:
    hooks = (ROOT / ".pre-commit-hooks.yaml").read_text()
    assert "id: slop-lint" in hooks
    assert "entry: slop-lint check" in hooks
    assert "humanize" not in hooks
    assert "--fix" not in hooks
```

- [ ] **Step 2: Run metadata tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_project_metadata.py -q
```

Expected: both tests fail because the files still mention `humanize`.

- [ ] **Step 3: Update `.github/workflows/ci.yml`**

Change the coverage and dogfood sections to:

```yaml
      - name: Run tests with coverage
        run: pytest tests/ -v --cov=src/slop_lint --cov-report=xml
```

and:

```yaml
      - name: Install slop-lint
        run: |
          python -m pip install --upgrade pip
          pip install -e .

      - name: Dogfood - check own docs
        run: slop-lint check README.md docs/ --baseline .slop-lint-baseline.json
        continue-on-error: true
```

Keep `continue-on-error: true` until Task 8 makes dogfood clean or intentionally baselined.

- [ ] **Step 4: Update `.pre-commit-hooks.yaml`**

Replace the file with:

```yaml
# Pre-commit hooks for slop-lint
# Add to your .pre-commit-config.yaml:
#
# repos:
#   - repo: https://github.com/yourusername/slop-lint
#     rev: v0.1.0
#     hooks:
#       - id: slop-lint
#
- id: slop-lint
  name: slop-lint
  description: Detect bad writing practices in Markdown and Python files
  entry: slop-lint check
  language: python
  types_or: [markdown, python]
  require_serial: false
  minimum_pre_commit_version: '2.9.0'
```

- [ ] **Step 5: Verify metadata tests pass**

Run:

```bash
.venv/bin/pytest tests/test_project_metadata.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Run formatting and linting checks for touched test file**

Run:

```bash
.venv/bin/ruff check tests/test_project_metadata.py
.venv/bin/mypy src/
```

Expected:

```text
All checks passed!
Success: no issues found in 26 source files
```

- [ ] **Step 7: Commit**

Run:

```bash
git add .github/workflows/ci.yml .pre-commit-hooks.yaml tests/test_project_metadata.py
git commit -m "chore: align automation with slop-lint package"
```

Expected: one commit containing only metadata and its regression tests.

---

### Task 3: Validate CLI Option Values and Missing Paths

**Files:**
- Modify `src/slop_lint/cli.py`
- Modify `tests/test_cli.py`

- [ ] **Step 1: Add failing CLI validation tests**

Append these tests to `tests/test_cli.py`:

```python
def test_invalid_format_returns_usage_error(tmp_path: Path) -> None:
    test_file = tmp_path / "clean.md"
    test_file.write_text("Clean content.")

    result = run_cli("check", "--format", "xml", str(test_file))

    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_invalid_severity_returns_usage_error(tmp_path: Path) -> None:
    test_file = tmp_path / "clean.md"
    test_file.write_text("Clean content.")

    result = run_cli("check", "--severity", "banana", str(test_file))

    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_invalid_min_confidence_returns_usage_error(tmp_path: Path) -> None:
    test_file = tmp_path / "clean.md"
    test_file.write_text("Clean content.")

    result = run_cli("check", "--min-confidence", "certain", str(test_file))

    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_missing_path_returns_usage_error() -> None:
    result = run_cli("check", "/private/tmp/slop-lint-path-that-does-not-exist.md")

    assert result.returncode == 2
    assert "Path does not exist" in result.stderr
```

If `tests/test_cli.py` does not already import `Path`, add:

```python
from pathlib import Path
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -q
```

Expected: new validation tests fail.

- [ ] **Step 3: Add argparse choices**

In `src/slop_lint/cli.py`, change the `check` option definitions to:

```python
    p_check.add_argument(
        "--format",
        "-f",
        choices=("text", "json", "sarif"),
        default="text",
        help="Output format: text, json, sarif",
    )
```

```python
    p_check.add_argument(
        "--severity",
        choices=("error", "warning", "info"),
        default=None,
        help="Minimum severity: error, warning, info",
    )
```

```python
    p_check.add_argument(
        "--min-confidence",
        choices=("high", "medium", "low"),
        default=None,
        help="Minimum confidence: high, medium, low",
    )
```

- [ ] **Step 4: Add missing path validation**

In `_cmd_check`, after `paths = [Path(p) for p in args.paths]`, add:

```python
    missing_paths = [path for path in paths if not path.exists()]
    if missing_paths:
        for path in missing_paths:
            print(f"Path does not exist: {path}", file=sys.stderr)
        return 2
```

In `_cmd_watch`, after `paths = [Path(p) for p in args.paths]`, add the same block.

- [ ] **Step 5: Verify focused tests**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -q
```

Expected:

```text
36 passed
```

The count may be higher if additional tests already exist; all tests in `tests/test_cli.py` must pass.

- [ ] **Step 6: Verify direct CLI behavior**

Run:

```bash
.venv/bin/slop-lint check --severity banana tests/fixtures/human_written/sample2.py
.venv/bin/slop-lint check --format xml tests/fixtures/human_written/sample2.py
.venv/bin/slop-lint check /private/tmp/slop-lint-path-that-does-not-exist.md
```

Expected: each command exits `2`; invalid choices use argparse's `invalid choice` message, and the missing path prints `Path does not exist`.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/slop_lint/cli.py tests/test_cli.py
git commit -m "fix: validate cli inputs"
```

Expected: one commit containing CLI validation and tests.

---

### Task 4: Convert Expected Runtime Failures Into Friendly Exit Codes

**Files:**
- Modify `src/slop_lint/config.py`
- Modify `src/slop_lint/cli.py`
- Modify `src/slop_lint/core/linter.py`
- Modify `tests/test_cli.py`
- Modify `tests/test_linter.py`

- [ ] **Step 1: Add config error tests**

Append to `tests/test_cli.py`:

```python
def test_invalid_config_returns_config_error(tmp_path: Path) -> None:
    config_file = tmp_path / ".slop-lint.toml"
    config_file.write_text("invalid [ toml ][\n")
    test_file = tmp_path / "clean.md"
    test_file.write_text("Clean content.")

    result = run_cli("check", "--config", str(config_file), str(test_file))

    assert result.returncode == 2
    assert "Configuration error" in result.stderr
    assert str(config_file) in result.stderr
    assert "Traceback" not in result.stderr
```

- [ ] **Step 2: Add invalid UTF-8 test**

Append to `tests/test_cli.py`:

```python
def test_invalid_utf8_file_returns_internal_error(tmp_path: Path) -> None:
    test_file = tmp_path / "invalid.md"
    test_file.write_bytes(b"\xff")

    result = run_cli("check", str(test_file))

    assert result.returncode == 3
    assert "Could not read file" in result.stderr
    assert str(test_file) in result.stderr
    assert "Traceback" not in result.stderr
```

- [ ] **Step 3: Run focused tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_cli.py::test_invalid_config_returns_config_error tests/test_cli.py::test_invalid_utf8_file_returns_internal_error -q
```

Expected: both tests fail with tracebacks or incorrect exit codes.

- [ ] **Step 4: Add configuration exception type**

In `src/slop_lint/config.py`, add this class near the dataclasses:

```python
class ConfigError(ValueError):
    """Raised when configuration cannot be loaded or parsed."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message
```

Add `"ConfigError"` to `__all__`.

- [ ] **Step 5: Wrap TOML parsing**

In `load_config`, replace:

```python
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
```

with:

```python
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except OSError as exc:
        raise ConfigError(config_path, str(exc)) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(config_path, str(exc)) from exc
```

- [ ] **Step 6: Add linter read error type**

In `src/slop_lint/core/linter.py`, add near the top:

```python
class LintReadError(OSError):
    """Raised when a file cannot be read for linting."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message
```

Add `"LintReadError"` to `__all__`.

- [ ] **Step 7: Wrap file reads**

In `check_file`, replace:

```python
        content = path.read_text(encoding="utf-8")
```

with:

```python
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise LintReadError(path, str(exc)) from exc
```

- [ ] **Step 8: Map expected exceptions in CLI**

In `src/slop_lint/cli.py`, import the exception classes:

```python
from slop_lint.config import ConfigError, load_config
from slop_lint.core.linter import LintReadError, Linter
```

In `_cmd_check`, wrap config loading:

```python
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
```

Wrap `linter.check(paths)`:

```python
    try:
        results = linter.check(paths)
    except LintReadError as exc:
        print(f"Could not read file: {exc}", file=sys.stderr)
        return 3
```

Apply the same `ConfigError` mapping in `_cmd_watch`.

- [ ] **Step 9: Verify focused tests**

Run:

```bash
.venv/bin/pytest tests/test_cli.py::test_invalid_config_returns_config_error tests/test_cli.py::test_invalid_utf8_file_returns_internal_error -q
```

Expected:

```text
2 passed
```

- [ ] **Step 10: Verify broader CLI tests**

Run:

```bash
.venv/bin/pytest tests/test_cli.py tests/test_linter.py -q
```

Expected: all tests pass.

- [ ] **Step 11: Commit**

Run:

```bash
git add src/slop_lint/config.py src/slop_lint/cli.py src/slop_lint/core/linter.py tests/test_cli.py tests/test_linter.py
git commit -m "fix: report expected cli failures cleanly"
```

Expected: one commit containing friendly error mapping and tests.

---

### Task 5: Make Exit Codes Honor Severity Semantics and Quiet Mode

**Files:**
- Modify `src/slop_lint/cli.py`
- Modify `tests/test_cli.py`

- [ ] **Step 1: Add exit-code tests**

Append to `tests/test_cli.py`:

```python
def test_info_only_issues_do_not_fail(tmp_path: Path) -> None:
    test_file = tmp_path / "doc.md"
    test_file.write_text("This not only improves speed but also reliability.")

    result = run_cli("check", "--select", "S002", "--severity", "info", str(test_file))

    assert result.returncode == 0
    assert "S002" in result.stdout


def test_warning_issues_fail(tmp_path: Path) -> None:
    test_file = tmp_path / "doc.md"
    test_file.write_text("Let us delve into this topic.")

    result = run_cli("check", "--select", "V001", str(test_file))

    assert result.returncode == 1
    assert "V001" in result.stdout


def test_quiet_suppresses_warning_output(tmp_path: Path) -> None:
    test_file = tmp_path / "doc.md"
    test_file.write_text("Let us delve into this topic.")

    result = run_cli("check", "--quiet", str(test_file))

    assert result.returncode == 1
    assert result.stdout == ""
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_cli.py::test_info_only_issues_do_not_fail tests/test_cli.py::test_quiet_suppresses_warning_output -q
```

Expected: info-only currently exits `1`, and quiet still prints issues.

- [ ] **Step 3: Add exit-code helper**

In `src/slop_lint/cli.py`, add above `_output_results`:

```python
def _has_failing_issue(results: dict[Path, list[Issue]]) -> bool:
    """Return True when any issue should make the process fail."""
    return any(
        issue.severity in {Severity.ERROR, Severity.WARNING}
        for issues in results.values()
        for issue in issues
    )
```

- [ ] **Step 4: Honor quiet mode in text output**

In `_output_results`, replace the text-output branch:

```python
    else:
        for file_path, issues in results.items():
```

with:

```python
    elif args.quiet:
        pass
    else:
        for file_path, issues in results.items():
```

Keep JSON and SARIF output unchanged when `--quiet` is provided because machine output must remain complete.

- [ ] **Step 5: Return by severity**

Replace the final line in `_output_results`:

```python
    return 1 if total_issues > 0 else 0
```

with:

```python
    return 1 if _has_failing_issue(results) else 0
```

- [ ] **Step 6: Verify focused tests**

Run:

```bash
.venv/bin/pytest tests/test_cli.py::test_info_only_issues_do_not_fail tests/test_cli.py::test_warning_issues_fail tests/test_cli.py::test_quiet_suppresses_warning_output -q
```

Expected:

```text
3 passed
```

- [ ] **Step 7: Run CLI suite**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -q
```

Expected: all CLI tests pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add src/slop_lint/cli.py tests/test_cli.py
git commit -m "fix: honor severity in cli exit codes"
```

Expected: one commit containing exit-code and quiet-mode behavior.

---

### Task 6: Report True Checked File Counts

**Files:**
- Modify `src/slop_lint/core/linter.py`
- Modify `src/slop_lint/core/reporter.py`
- Modify `src/slop_lint/cli.py`
- Modify `tests/test_reporter.py`
- Modify `tests/test_linter.py`
- Modify `tests/test_cli.py`

- [ ] **Step 1: Add result object**

In `src/slop_lint/core/linter.py`, add:

```python
@dataclass(frozen=True)
class LintResults:
    """Issues plus scan metadata."""

    issues_by_file: dict[Path, list[Issue]]
    files_checked: int
```

Add `"LintResults"` to `__all__`.

- [ ] **Step 2: Add failing tests for checked count**

Add to `tests/test_reporter.py`:

```python
def test_json_reports_files_checked_from_metadata(tmp_path: Path) -> None:
    from slop_lint.core.reporter import Reporter

    reporter = Reporter(format="json", files_checked=3)
    output = json.loads(reporter.report({}))

    assert output["summary"]["files_checked"] == 3
```

If needed, add:

```python
import json
```

Add to `tests/test_cli.py`:

```python
def test_json_clean_file_reports_one_file_checked(tmp_path: Path) -> None:
    test_file = tmp_path / "clean.md"
    test_file.write_text("Clean content.")

    result = run_cli("check", "--format", "json", str(test_file))

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["summary"]["files_checked"] == 1
    assert output["summary"]["total_issues"] == 0
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_reporter.py::test_json_reports_files_checked_from_metadata tests/test_cli.py::test_json_clean_file_reports_one_file_checked -q
```

Expected: tests fail because `Reporter` does not accept `files_checked` and clean JSON reports zero.

- [ ] **Step 4: Update linter `check` return type**

Change `Linter.check` to return `LintResults`:

```python
    def check(self, paths: list[Path]) -> LintResults:
        """Check multiple paths for issues."""
        files = self.discover_files(paths)
        if not files:
            return LintResults(issues_by_file={}, files_checked=0)

        worker_count = min(32, (os.cpu_count() or 1) + 4)

        file_results: list[tuple[Path, list[Issue]]]
        if len(files) > 1 and worker_count > 1:
            with ThreadPoolExecutor(max_workers=min(worker_count, len(files))) as pool:
                file_results = list(pool.map(self._check_file_with_path, files))
        else:
            file_results = [self._check_file_with_path(file) for file in files]

        file_results.sort(key=lambda item: str(item[0]))
        issues_by_file = {path: issues for path, issues in file_results if issues}
        return LintResults(issues_by_file=issues_by_file, files_checked=len(files))
```

- [ ] **Step 5: Update CLI call site**

In `_cmd_check`, replace:

```python
        results = linter.check(paths)
```

with:

```python
        lint_results = linter.check(paths)
```

Then set:

```python
    files_checked = lint_results.files_checked
    results = lint_results.issues_by_file
```

Pass `files_checked` to output:

```python
    return _output_results(results, args, rules=active_rules, files_checked=files_checked)
```

Update `_output_results` signature:

```python
def _output_results(
    results: dict[Path, list[Issue]],
    args: argparse.Namespace,
    rules: list[Rule] | None = None,
    files_checked: int | None = None,
) -> int:
```

Create reporter with:

```python
        reporter = Reporter(format=args.format, rules=rules, files_checked=files_checked)
```

- [ ] **Step 6: Update Reporter**

Change `Reporter.__init__` to:

```python
    def __init__(
        self,
        format: str = "text",
        rules: list[Any] | None = None,
        files_checked: int | None = None,
    ) -> None:
        self.format = format
        self._rules = rules
        self._files_checked = files_checked
```

Change `_format_json` signature:

```python
def _format_json(results: _Results, files_checked: int | None = None) -> str:
```

Set summary count:

```python
            "files_checked": files_checked if files_checked is not None else len(results),
```

In `Reporter.report`, call:

```python
        if self.format == "json":
            return _format_json(results, files_checked=self._files_checked)
```

- [ ] **Step 7: Update tests using `Linter.check`**

Where tests expect a dictionary from `linter.check(...)`, change:

```python
results = linter.check([test_file])
```

to:

```python
lint_results = linter.check([test_file])
results = lint_results.issues_by_file
```

Add assertions where useful:

```python
assert lint_results.files_checked == 1
```

- [ ] **Step 8: Verify focused tests**

Run:

```bash
.venv/bin/pytest tests/test_reporter.py tests/test_linter.py tests/test_cli.py -q
```

Expected: all tests pass.

- [ ] **Step 9: Run type check**

Run:

```bash
.venv/bin/mypy src/
```

Expected:

```text
Success: no issues found in 26 source files
```

- [ ] **Step 10: Commit**

Run:

```bash
git add src/slop_lint/core/linter.py src/slop_lint/core/reporter.py src/slop_lint/cli.py tests/test_reporter.py tests/test_linter.py tests/test_cli.py
git commit -m "fix: report true checked file counts"
```

Expected: one commit containing result metadata plumbing.

---

### Task 7: Reduce Markdown Table and List False Positives for S010

**Files:**
- Modify `src/slop_lint/parsers/markdown.py`
- Modify `src/slop_lint/rules/struct.py`
- Modify `tests/test_parsers/test_markdown.py`
- Modify `tests/test_rules/test_struct.py`
- Modify `tests/fixtures/human_written/sample1.md` only if the fixture is plainly mislabeled after the rule fix.

- [ ] **Step 1: Add parser tests for prose lines**

Append to `tests/test_parsers/test_markdown.py`:

```python
def test_prose_lines_exclude_table_rows() -> None:
    content = """\
| Prefix | Category |
|--------|----------|
| `V` | Vocabulary |

This is prose.
"""
    parser = MarkdownParser(content)

    lines = parser.get_prose_lines()

    assert lines == [(5, "This is prose.")]


def test_prose_lines_exclude_list_markers_but_keep_item_text() -> None:
    content = """\
- First item explains the behavior.
- Second item explains the tradeoff.

This is prose.
"""
    parser = MarkdownParser(content)

    lines = parser.get_prose_lines()

    assert lines == [
        (1, "First item explains the behavior."),
        (2, "Second item explains the tradeoff."),
        (4, "This is prose."),
    ]
```

- [ ] **Step 2: Add S010 regression tests**

Append to `tests/test_rules/test_struct.py` near the `AnaphoraAbuseRule` tests:

```python
def test_anaphora_ignores_markdown_table_rows() -> None:
    rule = AnaphoraAbuseRule(threshold=3)
    text = """\
| Prefix | Category |
|--------|----------|
| `V` | Vocabulary |
| `S` | Structure |
| `T` | Style |
"""

    issues = rule.check(text, "README.md")

    assert issues == []


def test_anaphora_does_not_count_list_marker_as_opening() -> None:
    rule = AnaphoraAbuseRule(threshold=3)
    text = """\
- First item explains setup.
- Second item explains usage.
- Third item explains cleanup.
"""

    issues = rule.check(text, "README.md")

    assert issues == []
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_parsers/test_markdown.py::test_prose_lines_exclude_table_rows tests/test_parsers/test_markdown.py::test_prose_lines_exclude_list_markers_but_keep_item_text tests/test_rules/test_struct.py::test_anaphora_ignores_markdown_table_rows tests/test_rules/test_struct.py::test_anaphora_does_not_count_list_marker_as_opening -q
```

Expected: tests fail because tables are still included and list markers are counted as sentence openings.

- [ ] **Step 4: Add Markdown table and list helpers**

In `MarkdownParser`, add:

```python
    @staticmethod
    def _is_table_row(line: str) -> bool:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            return False
        return stripped.count("|") >= 2

    @staticmethod
    def _strip_list_marker(line: str) -> str:
        return re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line)
```

- [ ] **Step 5: Update prose line extraction**

Replace `get_prose_lines` with:

```python
    def get_prose_lines(self) -> list[tuple[int, str]]:
        """Return prose lines with Markdown syntax that is not prose removed."""
        prose_lines: list[tuple[int, str]] = []
        for line_num, line in self.get_lines():
            stripped_line, _ = self._strip_blockquote_prefix(line)
            if self._is_table_row(stripped_line):
                continue
            prose = self._strip_list_marker(stripped_line)
            prose = self._mask_inline_code_and_links(prose).strip()
            if prose:
                prose_lines.append((line_num, prose))
        return prose_lines
```

This preserves prose content inside list items while preventing `-` and `|` from becoming repeated sentence openings.

- [ ] **Step 6: Verify focused parser and rule tests**

Run:

```bash
.venv/bin/pytest tests/test_parsers/test_markdown.py tests/test_rules/test_struct.py -q
```

Expected: all parser and structure-rule tests pass.

- [ ] **Step 7: Check dogfood delta**

Run:

```bash
make dogfood
```

Expected: fewer `S010` findings against README and docs. If dogfood still fails on examples in `docs/rules.md`, keep those failures for Task 8 instead of weakening this rule further.

- [ ] **Step 8: Commit**

Run:

```bash
git add src/slop_lint/parsers/markdown.py src/slop_lint/rules/struct.py tests/test_parsers/test_markdown.py tests/test_rules/test_struct.py
git commit -m "fix: avoid markdown syntax false positives in anaphora rule"
```

Expected: one commit containing parser/rule behavior and tests.

---

### Task 8: Make Dogfood Useful and Stable

**Files:**
- Modify `Makefile`
- Modify `.slop-lint-baseline.json`
- Modify `docs/rules.md`
- Modify `README.md`
- Modify `docs/configuration.md`
- Modify `tests/test_fixtures.py` if fixture expectations need updating after Task 7.

- [ ] **Step 1: Generate a fresh dogfood baseline**

Run:

```bash
.venv/bin/python -m slop_lint check README.md docs/ --generate-baseline --baseline .slop-lint-baseline.json
```

Expected: baseline regenerated with current, intentional docs examples.

- [ ] **Step 2: Run dogfood**

Run:

```bash
make dogfood
```

Expected: exits `0`. If it still exits non-zero, inspect each reported issue and classify it as either an intentional example or a docs quality issue.

- [ ] **Step 3: Move intentional examples under example headings**

For any intentional examples in `docs/rules.md` that are not downgraded by `is_example_line`, place them under headings containing one of these words: `Example`, `Bad`, `Detected`, `Demo`, or `Before`.

Use this shape:

````markdown
**Example (bad):**

```text
This comprehensive guide delves into the intricacies of the topic.
```
````

- [ ] **Step 4: Remove accidental docs issues**

For docs issues that are not examples, rewrite the prose plainly. Example replacements:

```markdown
Fast, parallel file processing
```

may become:

```markdown
Parallel file processing
```

and:

```markdown
The landscape of modern development
```

may become:

```markdown
Modern development
```

- [ ] **Step 5: Verify dogfood**

Run:

```bash
make dogfood
```

Expected:

```text
✓ No issues found!
```

or JSON/text output with zero new issues after baseline filtering.

- [ ] **Step 6: Verify fixture expectations**

Run:

```bash
.venv/bin/pytest tests/test_fixtures.py -q
```

Expected: all fixture tests pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add Makefile .slop-lint-baseline.json docs/rules.md README.md docs/configuration.md tests/test_fixtures.py
git commit -m "chore: stabilize dogfood baseline"
```

Expected: one commit containing only dogfood-related updates. Omit files from `git add` if they were not changed.

---

### Task 9: Align SPEC, README, Configuration Docs, and Test Names

**Files:**
- Modify `SPEC.md`
- Modify `README.md`
- Modify `docs/configuration.md`
- Modify `.pre-commit-hooks.yaml` only if Task 2 did not already update public hook examples.

- [ ] **Step 1: Add docs drift tests**

Append to `tests/test_project_metadata.py`:

```python
def test_spec_matches_current_dependency_policy() -> None:
    spec = (ROOT / "SPEC.md").read_text()
    assert "Runtime Dependencies" in spec
    assert "No third-party runtime dependencies" in spec
    assert "typer" not in spec
    assert "rich" not in spec
    assert "mistune" not in spec
    assert "regex" not in spec


def test_spec_mentions_existing_test_files() -> None:
    spec = (ROOT / "SPEC.md").read_text()
    assert "tests/test_cli.py" in spec
    assert "tests/test_property.py" in spec
    assert "tests/test_integration.py" not in spec
    assert "tests/test_properties.py" not in spec


def test_spec_documents_watch_command() -> None:
    spec = (ROOT / "SPEC.md").read_text()
    assert "slop-lint watch [OPTIONS] [PATHS]..." in spec
```

- [ ] **Step 2: Run docs drift tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_project_metadata.py -q
```

Expected: new docs drift tests fail.

- [ ] **Step 3: Update `SPEC.md` command list**

In section `4.1 Commands`, include:

```text
slop-lint check [OPTIONS] [PATHS]...   Check files for bad writing practices
slop-lint rules                        List all available rules
slop-lint explain RULE_ID              Show detailed rule documentation
slop-lint init                         Create .slop-lint.toml config file
slop-lint version                      Show version information
slop-lint watch [OPTIONS] [PATHS]...   Watch files and re-check changes
```

- [ ] **Step 4: Update `SPEC.md` runtime dependency section**

Replace the runtime dependency table with:

```markdown
### 9.1 Runtime Dependencies

No third-party runtime dependencies are required. `slop-lint` uses the Python standard library for CLI parsing, TOML parsing on Python 3.11+, Markdown-oriented scanning, ANSI formatting, file discovery, and concurrency.
```

- [ ] **Step 5: Update `SPEC.md` testing strategy paths**

Use these rows:

```markdown
| Category | Purpose | Location |
|----------|---------|----------|
| Unit tests | Individual rule behavior | `tests/test_rules/` |
| CLI and pipeline tests | Command-line and linter behavior | `tests/test_cli.py`, `tests/test_linter.py` |
| Fixture tests | Known bad/clean samples | `tests/fixtures/`, `tests/test_fixtures.py` |
| Property tests | Edge cases via hypothesis | `tests/test_property.py` |
```

- [ ] **Step 6: Update public repository placeholders only where necessary**

If the repository URL is still unknown, leave `yourusername` examples unchanged. If a real upstream URL is known from `git remote -v`, replace placeholders consistently in `README.md` and `docs/configuration.md`.

- [ ] **Step 7: Verify docs drift tests**

Run:

```bash
.venv/bin/pytest tests/test_project_metadata.py -q
```

Expected: all metadata tests pass.

- [ ] **Step 8: Verify documentation structure**

Run:

```bash
make doc-audit
make spec-verify
```

Expected: both targets pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add SPEC.md README.md docs/configuration.md .pre-commit-hooks.yaml tests/test_project_metadata.py
git commit -m "docs: align specification with current implementation"
```

Expected: one commit containing docs alignment and tests. Omit unchanged files from `git add`.

---

### Task 10: Refresh Benchmarks and NFR Checks

**Files:**
- Modify `benchmarks/bench_rules.py`
- Modify `Makefile`
- Modify `SPEC.md` if measured NFR targets are revised.

- [ ] **Step 1: Add benchmark smoke test**

Create `tests/test_benchmarks.py`:

```python
"""Benchmark harness regression tests."""

from benchmarks.bench_rules import BenchmarkResult, print_results


def test_benchmark_output_uses_project_name(capsys) -> None:  # type: ignore[no-untyped-def]
    result = BenchmarkResult(
        name="sample",
        content_size=1024,
        num_rules=59,
        duration_ms=10.0,
        issues_found=1,
        throughput_kb_per_sec=100.0,
    )

    print_results([result])

    output = capsys.readouterr().out
    assert "SLOP-LINT BENCHMARK RESULTS" in output
    assert "HUMANIZE" not in output
    assert "Files/sec estimate" in output
```

- [ ] **Step 2: Run benchmark test and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_benchmarks.py -q
```

Expected: fails because output still says `HUMANIZE` and does not include files/sec.

- [ ] **Step 3: Update benchmark output title and files/sec summary**

In `benchmarks/bench_rules.py`, replace:

```python
    print("HUMANIZE BENCHMARK RESULTS")
```

with:

```python
    print("SLOP-LINT BENCHMARK RESULTS")
```

After average throughput, add:

```python
    avg_file_size_kb = sum(r.content_size for r in results) / len(results) / 1024
    files_per_sec = avg_throughput / avg_file_size_kb if avg_file_size_kb > 0 else 0
    print(f"Files/sec estimate: {files_per_sec:.1f}")
```

- [ ] **Step 4: Make memory-check honest**

In `Makefile`, replace:

```make
memory-check:
	@echo "Running memory probe via benchmark harness..."
	@$(PYTHON) -m benchmarks.bench_rules --memory 2>/dev/null || \
		echo "Memory probe flag not supported by benchmark harness yet"
```

with:

```make
memory-check:
	@echo "Memory probe is not implemented yet; skipping."
```

This keeps the NFR target honest until a real memory probe exists.

- [ ] **Step 5: Verify benchmark test**

Run:

```bash
.venv/bin/pytest tests/test_benchmarks.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Run benchmark target**

Run:

```bash
make benchmark
```

Expected: output starts with `SLOP-LINT BENCHMARK RESULTS` and includes `Files/sec estimate`.

- [ ] **Step 7: Decide whether to adjust NFR targets**

If `make benchmark` remains far below `>1000 files/second for typical docs`, update [SPEC.md](SPEC.md) NFR-05 to a measured target that the benchmark can enforce, such as:

```markdown
| NFR-05 | Processing speed | Track KB/s and files/sec estimate in `make benchmark`; no hard release gate until benchmark corpus reflects real projects |
```

Do not claim a hard performance target that CI does not check.

- [ ] **Step 8: Commit**

Run:

```bash
git add benchmarks/bench_rules.py Makefile SPEC.md tests/test_benchmarks.py
git commit -m "chore: refresh benchmark reporting"
```

Expected: one commit containing benchmark and NFR honesty updates. Omit `SPEC.md` if unchanged.

---

### Task 11: Final Full Verification

**Files:**
- No new edits unless verification exposes a defect.

- [ ] **Step 1: Run the full local quality gate**

Run:

```bash
make check
make coverage-analyze
make doc-audit
make spec-verify
make dogfood
make startup-check
make benchmark
```

Expected:

```text
All checks passed!
Success: no issues found in 26 source files
698 passed
Required test coverage of 90% reached
✓ Documentation structure verified
✓ CLI matches specification
```

The exact test count may increase after new tests are added. Coverage must remain at or above 90%.

- [ ] **Step 2: Verify CLI edge cases manually**

Run:

```bash
.venv/bin/slop-lint check --severity banana tests/fixtures/human_written/sample2.py
.venv/bin/slop-lint check --format xml tests/fixtures/human_written/sample2.py
.venv/bin/slop-lint check /private/tmp/slop-lint-path-that-does-not-exist.md
.venv/bin/slop-lint check --format json tests/fixtures/human_written/sample2.py
.venv/bin/slop-lint check --select S002 --severity info tests/fixtures/all_markdown_rules_fire.md
```

Expected:

```text
# invalid severity exits 2
# invalid format exits 2
# missing path exits 2
# clean JSON reports files_checked as 1
# info-only S002 exits 0 while still displaying the issue
```

- [ ] **Step 3: Inspect git diff**

Run:

```bash
git diff --stat master...HEAD
git diff master...HEAD -- .github/workflows/ci.yml .pre-commit-hooks.yaml src/slop_lint tests README.md SPEC.md docs Makefile benchmarks
```

Expected: changes match the tasks above; no unrelated formatting churn.

- [ ] **Step 4: Run full status check**

Run:

```bash
git status --short --branch
```

Expected: clean working tree on `codex/quality-reliability-plan`.

- [ ] **Step 5: Prepare summary**

Write a final implementation summary containing:

```markdown
## Summary
- Fixed CI/pre-commit package-name drift.
- Hardened CLI validation and friendly error reporting.
- Corrected severity-based exit codes and quiet mode.
- Reported true checked-file counts.
- Reduced Markdown syntax false positives in S010.
- Stabilized dogfood, docs, and benchmark signals.

## Verification
- make check
- make coverage-analyze
- make doc-audit
- make spec-verify
- make dogfood
- make startup-check
- make benchmark
```

---

## Execution Options

Plan complete and saved to `PLAN.md`. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.

Choose one execution mode before implementation begins.
