# slop-lint - Technical Specification

> Version: 0.1.0
> Last Updated: 2026-08-06

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
| FR-10 | Support line-scoped Markdown and Python suppressions | Must |
| FR-11 | Provide built-in rule profiles for common document genres | Should |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Python version | 3.11+ |
| NFR-02 | Type checking | Strict mypy compliance |
| NFR-03 | Test coverage | ≥90% |
| NFR-04 | Startup time | <100ms |
| NFR-05 | Processing speed | Track KB/s and files/sec estimate in `make benchmark`; no hard release gate until the benchmark corpus reflects real projects |
| NFR-06 | Memory usage | <100MB for 10,000 file workspace |

`make nfr-check` enforces the coverage, startup, and memory targets. Processing
speed remains a tracked metric until the benchmark corpus reflects real projects.

## 3. Detection Rules

### 3.1 Rule Categories

<!-- rule-docs:categories:start -->

| Prefix | Category | Rules | Description |
|--------|----------|-------|-------------|
| `V` | Vocabulary | 8 | Overused and clichéd words and phrases |
| `S` | Structure | 21 | Organizational patterns |
| `T` | Style | 8 | Typographic issues |
| `G` | Grammar | 14 | Grammatical patterns |
| `C` | Code | 4 | Python docstring/comment issues |
| `M` | Markup | 4 | Markdown artifacts |
| **Total** | | **59** | |

<!-- rule-docs:categories:end -->

Prose-scoped `V`, `S`, `T`, and `G` rules inspect Markdown prose and
source-mapped Python docstrings and comments. Python blocks are evaluated
independently so thresholds do not combine unrelated documentation. `C` rules
cover Python-specific documentation issues; Markdown syntax rules remain
Markdown-only.

### 3.2 Rule Severity Levels

| Level | Description | Default Exit Code Impact |
|-------|-------------|--------------------------|
| `error` | Critical issue | Contributes to exit code 1 |
| `warning` | Probable bad practice | Contributes to exit code 1 |
| `info` | Possible issue, review recommended | Does not affect exit code |
| `off` | Rule disabled | — |

### 3.3 Built-in Profiles

| Profile | Selected rules | Minimum severity | Minimum confidence |
|---------|----------------|------------------|--------------------|
| `general` | General prose rules | info | medium |
| `technical-docs` | General plus C001-C004 and M001-M004 | info | low |
| `academic` | General plus G011-G013, S018, and T008 | info | medium |
| `journalism` | General plus G010, S017, and V008 | info | medium |
| `business` | General plus G014 and S019-S021 | info | low |

General prose rules are G001-G009, S001-S016, T001-T007, and V001-V007.
Running without a profile retains the legacy all-category selection, warning
minimum severity, and low minimum confidence.

## 4. Command-Line Interface

### 4.1 Commands

```
slop-lint check [OPTIONS] [PATHS]...   Check files for bad writing practices
slop-lint rules                        List all available rules
slop-lint explain RULE_ID              Show detailed rule documentation
slop-lint init                         Create .slop-lint.toml config file
slop-lint version                      Show version information
slop-lint watch [OPTIONS] [PATHS]...   Watch files and re-check changes
slop-lint baseline ACTION [OPTIONS] [PATHS]...
                                       Create and maintain a baseline
```

### 4.2 Check Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | choice | text | Output format: text, json, sarif |
| `--profile` | choice | none | Built-in rule profile |
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

### 4.3 Watch Command Options

`watch` supports the shared `--profile`, `--select`, `--ignore`, `--config`,
`--severity`, `--min-confidence`, `--hide-low`, `--baseline`, `--quiet`, and
`--verbose` options from `check`. It also accepts `--interval` (seconds, default
`2.0`) and `--no-clear`. Watch is text-only; `--format`,
`--generate-baseline`, and `--show-config` remain check-only.

### 4.4 Baseline Command

`ACTION` is one of `create`, `update`, `prune`, or `summary`. The command uses
the normal scan configuration and options but compares unbaselined findings:

- `create` replaces the target with all current findings.
- `summary` reports active, stale, and new counts without writing.
- `update` accepts new findings and retains stale version 2 entries.
- `prune` removes stale entries without accepting new findings.

Successful maintenance actions return 0. `--baseline` defaults to
`.slop-lint-baseline.json`. `check --generate-baseline` remains a compatibility
form for creating a version 2 file.

Version 2 entries contain a workspace-relative path, rule ID, normalized
matched source, and limited same-line context hash. Identity excludes line
numbers, diagnostic messages, severity, confidence, suggestions, and adjacent
lines. Input order does not affect workspace selection: a shared Git root wins,
otherwise the common scan root is used. Writes are atomic and deterministically
ordered.

Version 1 files remain readable for one compatibility cycle. A write migrates
currently matched hashes to version 2 and reports unmatched opaque hashes as
stale. Explicit missing, malformed, unreadable, and unsupported baseline files
are configuration errors before scanning begins.

### 4.5 Scan Policy

All scan commands load configuration, apply its profile defaults and explicit
policy, then apply a CLI profile and direct CLI rule overrides. They construct
rules with severity overrides, apply the minimum severity, scan with file and
per-file ignore policy, apply inline suppressions, filter by confidence, apply
the baseline, and finally report the ordered findings. A watch iteration uses
the same batch pipeline as `check`.

### 4.6 Exit Codes

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
profile = "technical-docs"
# select = ["V", "S", "T", "G", "C", "M"]  # replaces profile selection
ignore = []

# Minimum severity to report
minimum_severity = "warning"

# Minimum confidence to report
min_confidence = "low"  # low, medium, high
```

Severity overrides use a nested table:

```toml
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

Only documented keys are valid in the slop-lint table and its nested tables.
All numeric thresholds are positive integers. `select`, `ignore`, and per-file
ignore entries accept case-insensitive full rule IDs or one-letter category
prefixes; severity override keys accept full rule IDs only. References are
normalized to uppercase and checked against the complete built-in registry.
Unknown keys and references are configuration errors, with a close-match hint
when available.

Profiles are fixed built-in presets. For a configured profile, explicit
`select`, `minimum_severity`, and `min_confidence` keys override preset values.
A CLI `--profile` replaces the configured profile and its three policy values;
direct CLI `--select`, `--ignore`, `--severity`, `--min-confidence`, and
`--hide-low` options apply last. Independent file, vocabulary, threshold,
per-file-ignore, and per-rule severity settings remain active.

The legacy scalar `severity = "warning"` remains valid for one deprecation
cycle. It cannot be combined with `minimum_severity`; the latter can coexist
with the `[tool.slop-lint.severity]` override table. `--show-config` displays
the normalized effective policy and the explicit or discovered source file,
or `default` when no file was loaded.

### 5.3 Inline Suppressions

A standalone Markdown directive suppresses matching findings reported on the
immediately following physical line:

```markdown
<!-- slop-lint-ignore-next-line V001,S010 -->
This documentation delves into three related concerns.
```

A Python directive must be a real comment token and suppresses matching
findings reported on the same physical line:

```python
"""This documentation delves into the API."""  # slop-lint: ignore=V001,S010
```

Tokens are case-insensitive rule IDs or one-letter category prefixes. Empty,
malformed, and unknown tokens are configuration errors. Fenced Markdown
examples and Python string contents do not act as directives. Suppressions run
before confidence and baseline filtering.

## 6. Output Formats

### 6.1 Text (Default)

```
docs/api.md:15:10: V001 [high] [warning] Overused word: 'delve' → consider 'explore'
docs/api.md:23:1: S001 [warning] Rule of three pattern detected
src/main.py:45:8: V002 [warning] Collaborative phrase: 'I hope this helps'

Found 3 issue(s) (0 error, 2 warning, 1 info) in 2 file(s)
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
JSON and SARIF are complete `check` documents written to stdout. Operational
diagnostics are written to stderr so structured stdout remains parseable.

## 7. Architecture

### 7.1 Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `cli` | Command parsing, argument validation |
| `config` | Configuration loading and merging |
| `core/linter` | File discovery, rule orchestration |
| `core/reporter` | Output formatting (text/JSON/SARIF) |
| `rules/base` | Abstract rule interface |
| `rules/__init__` | Rule registry and immutable metadata projection |
| `rules/*` | Rule implementations by category |
| `parsers/*` | Markdown and Python AST parsing |
| `data/*` | Vocabulary lists and patterns |
| `_rule_docs` | Deterministic generated-document synchronization |

### 7.2 Rule Protocol

All rules must implement:

```python
class Rule(Protocol):
    id: str           # e.g., "V001"
    name: str         # e.g., "Overused Vocabulary"
    description: str  # Full description
    severity: Severity
    default_confidence: Confidence
    applies_to: set[str]
    content_scope: str
    config_key: str | None

    def check(self, content: str, filename: str) -> list[Issue]: ...
```

Rule classes and `get_all_rules()` are the canonical source for rule metadata.
`get_rule_metadata()` exposes an immutable projection used by the CLI and the
documentation generator. Generated blocks are bounded by `rule-docs` markers;
`make rule-docs` updates them and `make rule-docs-check` verifies them without
writing.

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
| Rule-quality benchmark | Reviewed per-rule precision and recall | `quality/`, `make rule-quality` |
| Documentation synchronization | Metadata projection, markers, and deterministic output | `tests/test_rule_docs.py` |

The rule-quality benchmark reports true positives, false positives, false
negatives, precision, recall, and explicit negative-case coverage for every
registered rule. Its first version validates corpus integrity and reports
metrics without enforcing a numeric threshold; thresholds will be added only
after the corpus contains enough reviewed examples to represent real usage.

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
