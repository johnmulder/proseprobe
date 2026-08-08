# ProseProbe - Technical Specification

> Version: 0.1.0
> Last Updated: 2026-08-08

## 1. Purpose

`proseprobe` is a Unix-style linter for common prose, documentation, and Markdown problems. It detects overused vocabulary, structural clichés, repetitive patterns, style issues, and markup errors in Markdown and Python documentation.

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Scan Markdown files (`.md`, `.mdx`, `.markdown`) for configured prose and markup problems | Must |
| FR-02 | Scan Python files (`.py`) for configured problems in docstrings and comments | Must |
| FR-03 | Report issues with file path, line number, column, and severity | Must |
| FR-04 | Support configurable rule selection via CLI and config file | Must |
| FR-05 | Output in text, JSON, JSON Lines, and SARIF formats | Must |
| FR-06 | Support `.proseprobe.toml` configuration file | Must |
| FR-07 | Respect `.gitignore` patterns for file discovery | Should |
| FR-08 | Process files in parallel for performance | Could |
| FR-09 | Provide `explain` command for rule documentation | Should |
| FR-10 | Support line-scoped Markdown and Python suppressions | Must |
| FR-11 | Provide built-in rule profiles for common document genres | Should |
| FR-12 | Check one standard-input document through `-` with an explicit virtual filename | Should |

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
| `V` | Vocabulary | 10 | Overused and clichéd words and phrases |
| `S` | Structure | 22 | Organizational patterns |
| `T` | Style | 9 | Typographic issues |
| `G` | Grammar | 18 | Grammatical patterns |
| `C` | Code | 4 | Python docstring/comment issues |
| `M` | Markup | 9 | Markdown artifacts |
| **Total** | | **72** | |

<!-- rule-docs:categories:end -->

Most prose-scoped `V`, `S`, `T`, and `G` rules inspect Markdown prose and
source-mapped Python docstrings and comments; `G015` examines only Markdown
document openers. Python blocks are evaluated independently so thresholds do
not combine unrelated documentation. `C` rules cover Python-specific
documentation issues. `M001` checks Markdown syntax in Python comments, while
`M002`-`M008`, `M010`, and `S025` are Markdown-only.

Markdown and Python parsers cache source-mapped sentence records with exact
start and end line and column positions. Sentence segmentation uses
conservative standard-library handling for abbreviations, decimals, URLs,
trailing quotes, and hard prose-block boundaries; it does not require an NLP
dependency.

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
| `technical-docs` | General plus C001-C004, G017, G024, G029, M001-M008, M010, S025, T015, and V009-V010 | info | low |
| `academic` | General plus G011-G013, S018, and T008 | info | medium |
| `journalism` | General plus G010, S017, and V008 | info | medium |
| `business` | General plus G014 and S019-S021 | info | low |

General prose rules are G001-G009 and G015, S001-S016, T001-T007, and
V001-V007.
Running without a profile retains the legacy all-category selection, warning
minimum severity, and low minimum confidence.

## 4. Command-Line Interface

### 4.1 Commands

```
proseprobe check [OPTIONS] [PATHS]...   Check files for prose and documentation problems
proseprobe rules [--format text|json]   List all available rules
proseprobe explain RULE_ID [--format text|json]
                                       Show detailed rule documentation
proseprobe init                         Create .proseprobe.toml config file
proseprobe version                      Show version information
proseprobe watch [OPTIONS] [PATHS]...   Watch files and re-check changes
proseprobe baseline ACTION [OPTIONS] [PATHS]...
                                       Create and maintain a baseline
```

### 4.2 Check Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | choice | text | Output format: text, json, jsonl, sarif |
| `--filename` | path | none | Required virtual path and file type when the input path is `-` |
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
| `--quiet` | flag | false | In text reports, output only errors |
| `--verbose` | flag | false | Show additional diagnostic info |

`check - --filename PATH` reads one UTF-8 document from standard input. The
virtual path selects file-specific rules and per-file ignores and is reported
as the file identity. Standard input is mutually exclusive with filesystem
paths, `--baseline`, and `--generate-baseline`; configuration discovery remains
rooted at the current working directory.

### 4.3 Rule Metadata Command Options

| Option | Type | Default | Commands | Description |
|--------|------|---------|----------|-------------|
| `--format` | choice | text | rules, explain | Metadata output format: text, json |

Both commands retain human-readable text by default. JSON output contains
canonical defaults and does not load project configuration.

### 4.4 Watch Command Options

`watch` supports the shared `--profile`, `--select`, `--ignore`, `--config`,
`--severity`, `--min-confidence`, `--hide-low`, `--baseline`, `--quiet`, and
`--verbose` options from `check`. It also accepts `--interval` (seconds, default
`2.0`) and `--no-clear`. Watch is text-only; `--format`,
`--generate-baseline`, and `--show-config` remain check-only.

### 4.5 Baseline Command

`ACTION` is one of `create`, `update`, `prune`, or `summary`. The command uses
the normal scan configuration and options but compares unbaselined findings:

- `create` replaces the target with all current findings.
- `summary` reports active, stale, and new counts without writing.
- `update` accepts new findings and retains stale version 2 entries.
- `prune` removes stale entries without accepting new findings.

Successful maintenance actions return 0. `--baseline` defaults to
`.proseprobe-baseline.json`. `check --generate-baseline` remains a compatibility
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

### 4.6 Scan Policy

All scan commands load configuration, apply its profile defaults and explicit
policy, then apply a CLI profile and direct CLI rule overrides. They construct
rules with severity overrides, apply the minimum severity, scan with file and
per-file ignore policy, apply inline suppressions, filter by confidence, apply
the baseline, and finally report the ordered findings. A watch iteration uses
the same batch pipeline as `check`.

### 4.7 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No warning or error findings; info findings may still be reported |
| 1 | Issues found (warning or error severity) |
| 2 | Configuration or usage error |
| 3 | An input file could not be read |

## 5. Configuration

### 5.1 Config File Location

Search order (first found wins):
1. `--config` CLI argument
2. `.proseprobe.toml` in current directory
3. `pyproject.toml` `[tool.proseprobe]` section
4. `.proseprobe.toml` in parent directories (up to git root)
5. `~/.config/proseprobe/config.toml`

### 5.2 Config Schema

```toml
[tool.proseprobe]
# File patterns (glob syntax)
include = ["*.md", "*.mdx", "*.markdown", "*.py"]
exclude = ["venv/**", ".venv/**", "node_modules/**", ".git/**"]

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
[tool.proseprobe.severity]
V001 = "error"
S002 = "info"

# Custom vocabulary additions
[tool.proseprobe.vocabulary]
additional = []  # Extra words to flag
allowed = []     # Domain-specific words to permit
allowed_phrases = ["All notable changes"]  # Exact phrases V001 should skip

# Per-file rule overrides
[[tool.proseprobe.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004"]
```

Only documented keys are valid in the proseprobe table and its nested tables.
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
with the `[tool.proseprobe.severity]` override table. `--show-config` displays
the normalized effective policy and the explicit or discovered source file,
or `default` when no file was loaded.

### 5.3 Inline Suppressions

A standalone Markdown directive suppresses matching findings reported on the
immediately following physical line:

```markdown
<!-- proseprobe-ignore-next-line V001,S010 -->
This documentation delves into three related concerns.
```

A Python directive must be a real comment token and suppresses matching
findings reported on the same physical line:

```python
"""This documentation delves into the API."""  # proseprobe: ignore=V001,S010
```

Tokens are case-insensitive rule IDs or one-letter category prefixes. Empty,
malformed, and unknown tokens are configuration errors. Fenced Markdown
examples and Python string contents do not act as directives. Suppressions run
before confidence and baseline filtering.

## 6. Output Formats

### 6.1 Text (Default)

```
docs/api.md:15:10: V001 [high] [warning] Overused word: 'delve' → consider 'explore'
docs/api.md:23:1: S001 [info] Triadic pattern (rule of three): 'fast, safe, and clear'
src/main.py:45:8: V002 [warning] Collaborative phrase: 'I hope this helps'

Found 3 issue(s) (0 error, 2 warning, 1 info) in 2 file(s)
Confidence: 1 high, 2 medium, 0 low
```

### 6.2 JSON

```json
{
  "schema_version": 1,
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
          "end_line": null,
          "end_column": 15,
          "severity": "warning",
          "confidence": "high",
          "suggestion": "explore"
        }
      ]
    }
  ],
  "summary": {
    "total_issues": 1,
    "files_checked": 1,
    "errors": 0,
    "warnings": 1,
    "info": 0
  }
}
```

`schema_version` identifies the machine-output contract; `version` identifies
the proseprobe package that produced the report. `line` and `column` are 1-based
start positions. `end_line` is the endpoint line, and `end_column` is a 1-based
exclusive endpoint. `end_line`, `end_column`, and `suggestion` are always
present and may be `null`. The schema version changes only for incompatible
contract changes.

### 6.3 JSON Lines

JSON Lines (`--format jsonl`) writes one complete diagnostic object per line:

```json
{"schema_version":1,"version":"0.1.0","path":"docs/guide.md","rule_id":"V001","message":"Overused word: 'delve' → consider 'explore'","line":15,"column":5,"end_line":null,"end_column":10,"severity":"warning","confidence":"high","suggestion":"explore"}
```

Records use the same version, diagnostic fields, position semantics, and
nullable fields as grouped JSON. Files are ordered by path, issue order within
each file is preserved, and every record ends with one newline. There is no
wrapper, summary, or metadata record; a clean run writes no stdout. Exit `0`
may include info records, while warning or error records produce exit `1`.

### 6.4 SARIF

Standard SARIF 2.1.0 format for GitHub Code Scanning integration.
Grouped JSON and SARIF are complete `check` documents written to stdout. JSON
Lines is a diagnostic stream. Operational diagnostics are written to stderr so
structured stdout remains parseable.

### 6.5 Rule Metadata JSON

`rules --format json` returns all canonical rule defaults in a deterministic
`rules` array. `explain RULE --format json` returns the same object shape for
one rule:

```json
{
  "schema_version": 1,
  "version": "0.1.0",
  "rule": {
    "id": "V001",
    "category": "Vocabulary",
    "name": "Overused Vocabulary",
    "description": "Detects overused and clichéd words",
    "default_severity": "warning",
    "default_confidence": "medium",
    "applies_to": ["markdown", "python"],
    "content_scope": "prose",
    "profiles": [
      "academic",
      "business",
      "general",
      "journalism",
      "technical-docs"
    ],
    "config_key": null
  }
}
```

The `rules` envelope contains `schema_version`, package `version`, and `rules`.
Each rule object has the fields shown above. Enum values are lowercase, tuple
metadata is serialized as arrays, and `config_key` is nullable. These are
canonical defaults: project configuration and CLI severity overrides do not
affect them. Text remains the default format. An unknown explanation ID exits
with code 1, writes no stdout, and writes a diagnostic to stderr. The schema
version changes only for incompatible contract changes.

## 7. Architecture

### 7.1 Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `cli` | Command parsing, argument validation |
| `config` | Configuration loading and merging |
| `core/linter` | File discovery, rule orchestration |
| `core/reporter` | Output formatting (text/JSON/JSONL/SARIF) |
| `rules/base` | Abstract rule interface |
| `rules/__init__` | Rule registry and immutable metadata projection |
| `rules/*` | Rule implementations by category |
| `parsers/*` | Markdown parsing and Python AST/source extraction |
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

No third-party runtime dependencies are required. `proseprobe` uses the Python
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
