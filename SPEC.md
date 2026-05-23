# slop-lint - Technical Specification

> Version: 0.1.0
> Last Updated: 2026-03-10

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
| FR-06 | Support `.slop-lint.toml` configuration file | Must |
| FR-07 | Respect `.gitignore` patterns for file discovery | Should |
| FR-08 | Process files in parallel for performance | Could |
| FR-09 | Provide `explain` command for rule documentation | Should |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Python version | 3.11+ |
| NFR-02 | Type checking | Strict mypy compliance |
| NFR-03 | Test coverage | ≥90% |
| NFR-04 | Startup time | <100ms |
| NFR-05 | Processing speed | Track KB/s and files/sec estimate in `make benchmark`; no hard release gate until the benchmark corpus reflects real projects |
| NFR-06 | Memory usage | <100MB for 10,000 file workspace |

## 3. Detection Rules

### 3.1 Rule Categories

| Prefix | Category | Count | Description |
|--------|----------|-------|-------------|
| `V` | Vocabulary | 8 | Overused and clichéd word patterns |
| `S` | Structure | 21 | Structural and organizational patterns |
| `T` | Style | 8 | Typographic and formatting issues |
| `G` | Grammar | 14 | Grammatical anti-patterns |
| `C` | Code | 4 | Python-specific documentation issues |
| `M` | Markup | 4 | Markdown artifacts and markup errors |
| **Total** | | **59** | |

### 3.2 Rule Severity Levels

| Level | Description | Default Exit Code Impact |
|-------|-------------|--------------------------|
| `error` | Critical issue | Contributes to exit code 1 |
| `warning` | Probable bad practice | Contributes to exit code 1 |
| `info` | Possible issue, review recommended | Does not affect exit code |
| `off` | Rule disabled | — |

## 4. Command-Line Interface

### 4.1 Commands

```
slop-lint check [OPTIONS] [PATHS]...   Check files for bad writing practices
slop-lint rules                        List all available rules
slop-lint explain RULE_ID              Show detailed rule documentation
slop-lint init                         Create .slop-lint.toml config file
slop-lint version                      Show version information
slop-lint watch [OPTIONS] [PATHS]...   Watch files and re-check changes
```

### 4.2 Check Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | choice | text | Output format: text, json, sarif |
| `--select` | string | all | Comma-separated rules/prefixes to enable |
| `--ignore` | string | none | Comma-separated rules/prefixes to disable |
| `--config` | path | auto | Path to configuration file |
| `--severity` | choice | warning | Minimum severity to report |
| `--min-confidence` | choice | low | Minimum confidence: high, medium, low |
| `--hide-low` | flag | false | Hide low-confidence issues |
| `--baseline` | path | none | Path to baseline file for incremental adoption |
| `--generate-baseline` | flag | false | Generate baseline from current issues |
| `--show-config` | flag | false | Display resolved configuration and exit |
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

# Minimum confidence to report
min_confidence = "low"  # low, medium, high

# Severity overrides per rule
[tool.slop-lint.severity]
V001 = "error"
S002 = "info"

# Custom vocabulary additions
[tool.slop-lint.vocabulary]
additional = []  # Extra words to flag
allowed = []     # Domain-specific words to permit
allowed_phrases = ["All notable changes"]  # Exact phrases to skip

# Per-file rule overrides
[[tool.slop-lint.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004"]
```

## 6. Output Formats

### 6.1 Text (Default)

```
docs/api.md:15:10: V001 [high] Overused word: 'delve' → consider 'explore'
docs/api.md:23:1: S001 Rule of three pattern detected
src/main.py:45:5: C001 Overused word in docstring: 'crucial'

Found 3 issues (2 warnings, 1 info) in 2 files
Confidence: 1 high, 2 medium, 0 low
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
          "confidence": "high"
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

    def check(self, content: str, filename: str) -> list[Issue]: ...
```

### 7.3 Confidence Levels

Each `Issue` carries a `confidence` field (`high`, `medium`, or `low`)
indicating how certain the rule is that the match is a real problem.

| Level | Meaning | Example |
|-------|---------|--------|
| `high` | Strong signal | V001 with tier-1 word ("delve") |
| `medium` | Likely issue | V001 with tier-2 word ("crucial") |
| `low` | Tentative | V001 with tier-3 word ("notable"), M001 in Python |

## 8. Testing Strategy

### 8.1 Test Categories

| Category | Purpose | Location |
|----------|---------|----------|
| Unit tests | Individual rule behavior | `tests/test_rules/` |
| CLI and pipeline tests | Command-line and linter behavior | `tests/test_cli.py`, `tests/test_linter.py` |
| Fixture tests | Known bad/clean samples | `tests/fixtures/`, `tests/test_fixtures.py` |
| Property tests | Edge cases via hypothesis | `tests/test_property.py` |

### 8.2 Fixtures

- `tests/fixtures/ai_generated/` — Samples with known bad practices
- `tests/fixtures/human_written/` — Clean samples for false positive testing

## 9. Dependencies

### 9.1 Runtime Dependencies

No third-party runtime dependencies are required. `slop-lint` uses the Python
standard library for CLI parsing, TOML parsing on Python 3.11+, Markdown-oriented
scanning, ANSI formatting, file discovery, and concurrency.

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
