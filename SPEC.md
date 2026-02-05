# slop-lint - Technical Specification

> Version: 0.1.0 (Draft)  
> Last Updated: 2026-01-31

## 1. Purpose

`slop-lint` is a command-line linting tool that detects bad writing practices in Markdown and Python files. It identifies overused vocabulary, structural clichés, stylistic problems, and markup errors.

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Scan Markdown files (`.md`, `.mdx`, `.markdown`) for bad writing practices | Must |
| FR-02 | Scan Python files (`.py`) for bad practices in docstrings and comments | Must |
| FR-03 | Report issues with file path, line number, column, and severity | Must |
| FR-04 | Support configurable rule selection via CLI and config file | Must |
| FR-05 | Output in text, JSON, and SARIF formats | Must |
| FR-06 | Auto-fix safe issues (vocabulary substitutions) with `--fix` flag | Should |
| FR-07 | Support `.slop-lint.toml` configuration file | Must |
| FR-08 | Respect `.gitignore` patterns for file discovery | Should |
| FR-09 | Process files in parallel for performance | Could |
| FR-10 | Provide `explain` command for rule documentation | Should |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Python version | 3.11+ |
| NFR-02 | Type checking | Strict mypy compliance |
| NFR-03 | Test coverage | ≥90% |
| NFR-04 | Startup time | <100ms |
| NFR-05 | Processing speed | >1000 files/second for typical docs |
| NFR-06 | Memory usage | <100MB for 10,000 file workspace |

## 3. Detection Rules

### 3.1 Rule Categories

| Prefix | Category | Count | Description |
|--------|----------|-------|-------------|
| `V` | Vocabulary | 5 | Overused and clichéd word patterns |
| `S` | Structure | 7 | Structural and organizational patterns |
| `T` | Style | 6 | Typographic and formatting issues |
| `G` | Grammar | 3 | Grammatical anti-patterns |
| `C` | Code | 4 | Python-specific documentation issues |
| `M` | Markup | 4 | Markdown artifacts and markup errors |
| **Total** | | **29** | |

### 3.2 Rule Severity Levels

| Level | Description | Default Exit Code Impact |
|-------|-------------|--------------------------|
| `error` | Critical issue | Contributes to exit code 1 |
| `warning` | Probable bad practice | Contributes to exit code 1 |
| `info` | Possible issue, review recommended | Does not affect exit code |
| `off` | Rule disabled | — |

### 3.3 Fixable Rules

The following rules support auto-fix with `--fix`:

| Rule | Fix Strategy |
|------|--------------|
| V001 | Replace overused vocabulary with suggested alternatives |
| V002 | Remove or rephrase collaborative phrases |
| M003 | Strip UTM parameters from URLs |
| T004 | Normalize quote characters |

## 4. Command-Line Interface

### 4.1 Commands

```
slop-lint check [OPTIONS] [PATHS]...   Check files for bad writing practices
slop-lint rules                        List all available rules
slop-lint explain RULE_ID              Show detailed rule documentation
slop-lint init                         Create .slop-lint.toml config file
slop-lint version                      Show version information
```

### 4.2 Check Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--fix` | flag | false | Apply auto-fixes for fixable issues |
| `--format` | choice | text | Output format: text, json, sarif |
| `--select` | string | all | Comma-separated rules/prefixes to enable |
| `--ignore` | string | none | Comma-separated rules/prefixes to disable |
| `--config` | path | auto | Path to configuration file |
| `--severity` | choice | warning | Minimum severity to report |
| `--quiet` | flag | false | Only output errors |
| `--verbose` | flag | false | Show additional diagnostic info |

### 4.3 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success, no issues found |
| 1 | Issues found (warning or error severity) |
| 2 | Configuration or usage error |
| 3 | Internal error |

## 5. Configuration

### 5.1 Config File Location

Search order (first found wins):
1. `--config` CLI argument
2. `.slop-lint.toml` in current directory
3. `pyproject.toml` `[tool.slop-lint]` section
4. `.slop-lint.toml` in parent directories (up to git root)
5. `~/.config/slop-lint/config.toml`

### 5.2 Config Schema

```toml
[tool.slop-lint]
# File patterns (glob syntax)
include = ["*.md", "*.py"]
exclude = ["venv/**", "node_modules/**", ".git/**"]

# Rule selection
select = ["V", "S", "T", "G", "C", "M"]
ignore = []

# Minimum severity to report
severity = "warning"

# Severity overrides per rule
[tool.slop-lint.severity]
V001 = "error"
S002 = "info"

# Custom vocabulary additions
[tool.slop-lint.vocabulary]
additional = []  # Extra words to flag
allowed = []     # Domain-specific words to permit

# Per-file rule overrides
[[tool.slop-lint.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004"]
```

## 6. Output Formats

### 6.1 Text (Default)

```
docs/api.md:15:10: V001 Overused word: 'delve' → consider 'explore'
docs/api.md:23:1: S001 Rule of three pattern detected
src/main.py:45:5: C001 Overused word in docstring: 'crucial'

Found 3 issues (2 warnings, 1 info) in 2 files
```

### 6.2 JSON

```json
{
  "version": "0.1.0",
  "files": [
    {
      "path": "docs/api.md",
      "issues": [
        {
          "rule_id": "V001",
          "message": "Overused word: 'delve' → consider 'explore'",
          "line": 15,
          "column": 10,
          "severity": "warning",
          "fixable": true
        }
      ]
    }
  ],
  "summary": {
    "total_issues": 3,
    "files_checked": 2,
    "errors": 0,
    "warnings": 2,
    "info": 1
  }
}
```

### 6.3 SARIF

Standard SARIF 2.1.0 format for GitHub Code Scanning integration.

## 7. Architecture

### 7.1 Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `cli` | Command parsing, argument validation |
| `config` | Configuration loading and merging |
| `core/linter` | File discovery, rule orchestration |
| `core/reporter` | Output formatting (text/JSON/SARIF) |
| `core/fixer` | Apply fixes to files |
| `rules/base` | Abstract rule interface |
| `rules/*` | Rule implementations by category |
| `parsers/*` | Markdown and Python AST parsing |
| `data/*` | Vocabulary lists and patterns |

### 7.2 Rule Protocol

All rules must implement:

```python
class Rule(Protocol):
    id: str           # e.g., "V001"
    name: str         # e.g., "Overused Vocabulary"
    description: str  # Full description
    severity: Severity
    fixable: bool
    
    def check(self, content: str, filename: str) -> list[Issue]: ...
    def fix(self, content: str, issue: Issue) -> str: ...
```

## 8. Testing Strategy

### 8.1 Test Categories

| Category | Purpose | Location |
|----------|---------|----------|
| Unit tests | Individual rule behavior | `tests/test_rules/` |
| Integration tests | CLI and full pipeline | `tests/test_integration.py` |
| Fixture tests | Known bad/clean samples | `tests/fixtures/` |
| Property tests | Edge cases via hypothesis | `tests/test_properties.py` |

### 8.2 Fixtures

- `tests/fixtures/ai_generated/` — Samples with known bad practices
- `tests/fixtures/human_written/` — Clean samples for false positive testing

## 9. Dependencies

### 9.1 Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| typer | ^0.9.0 | CLI framework |
| rich | ^13.0 | Terminal formatting |
| tomli | ^2.0 | TOML parsing (Python <3.11 only) |
| mistune | ^3.0 | Markdown parsing |
| regex | ^2023.0 | Advanced regex (Unicode categories) |

### 9.2 Development Dependencies

| Package | Purpose |
|---------|---------|
| pytest | Testing framework |
| pytest-cov | Coverage reporting |
| mypy | Static type checking |
| ruff | Linting and formatting |
| hypothesis | Property-based testing |

## 10. Versioning

- Follows Semantic Versioning 2.0.0
- Rule additions are minor version bumps
- Rule behavior changes are noted in CHANGELOG.md
- Configuration format changes require major version bump

---

*This specification is derived from [PLAN.md](PLAN.md). For implementation details and development workflow, see the plan document.*
