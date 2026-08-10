# Configuration Reference

ProseProbe can be configured via a `.proseprobe.toml` file or the `[tool.proseprobe]` section of `pyproject.toml`.

## Config File Discovery

Config files are discovered in this order:

1. `--config` CLI argument
2. `.proseprobe.toml` in current directory
3. `pyproject.toml` in current directory with `[tool.proseprobe]` section
4. `.proseprobe.toml` in parent directories (up to git root)
5. `~/.config/proseprobe/config.toml`

Directory scanning in Git worktrees also respects `.gitignore` patterns, including nested
`.gitignore` files in subdirectories. Patterns are applied in parent-to-child
order, and negation (`!pattern`) can re-include files that were ignored by
earlier matches.

## Configuration Options

### Built-in Profiles

Profiles are fixed presets for rule selection, minimum severity, and minimum
confidence:

```toml
[tool.proseprobe]
profile = "technical-docs"
```

| Profile | Selected rules | Minimum severity | Minimum confidence |
|---------|----------------|------------------|--------------------|
| `general` | General prose rules | `info` | `medium` |
| `technical-docs` | General plus technical-documentation rules | `info` | `low` |
| `academic` | General plus academic rules | `info` | `medium` |
| `journalism` | General plus journalism rules | `info` | `medium` |
| `business` | General plus business rules | `info` | `low` |

The exact classification is:

- general: `G001`-`G009`, `G015`, `S001`-`S016`, `T001`-`T007`, and
  `V001`-`V007`;
- technical documentation: `C001`-`C004`, `C007`-`C008`, `G016`-`G017`, `G019`, `G022`, `G024`-`G025`, `G029`, `G031`, `G037`,
  `M001`-`M010`, `S022`, `S025`, `S028`, `T010`, `T012`, `T014`-`T016`,
  `V009`-`V011`, `V013`-`V014`, and `V016`;
- academic: `G011`-`G013`, `S018`, and `T008`;
- journalism: `G010`, `S017`, and `V008`;
- business: `G014` and `S019`-`S021`.

Each specialized profile includes the general set plus its listed rules.
Running without a profile preserves the all-category selection, warning
minimum severity, and low minimum confidence.

`G038`, `S029`, `T013`, `V015`, and `V017` are experimental and are not included
in any built-in profile. Enable an experimental rule explicitly, including its
informational severity and low confidence:

```toml
[tool.proseprobe]
select = ["G038"]
minimum_severity = "info"
min_confidence = "low"
```

### File Patterns

```toml
[tool.proseprobe]
# Glob patterns for files to include
include = ["*.md", "*.mdx", "*.markdown", "*.py"]

# Glob patterns for files to exclude
exclude = ["venv/**", ".venv/**", "node_modules/**", ".git/**"]
```

`include` controls files discovered from directory arguments. An explicitly
named file bypasses `include` and `.gitignore`, but still respects `exclude`.

### Rule Selection

```toml
[tool.proseprobe]
# Rule prefixes or specific rules to enable
select = ["V", "S", "T", "G", "C", "M"]

# Rules to disable
ignore = ["T001", "T005"]
```

Selectors are case-insensitive and must be an existing full rule ID or
one-letter category prefix. Unknown selectors are configuration errors and
likely typos include a close-match suggestion.

### Severity Configuration

```toml
[tool.proseprobe]
# Minimum severity to report
minimum_severity = "warning"  # error, warning, info
```

Per-rule severity overrides use a nested table:

```toml
# Per-rule severity overrides
[tool.proseprobe.severity]
V001 = "error"      # Upgrade to error
S002 = "info"       # Downgrade to info
```

Override keys must be full rule IDs. The legacy scalar form
`severity = "warning"` remains accepted for one deprecation cycle, but cannot
be combined with `minimum_severity`; use the form above for new configuration.

### Custom Vocabulary

These settings customize `V001`; `allowed` and `additional` also keep `C001`
from duplicating vocabulary findings owned by `V001`.

```toml
[tool.proseprobe.vocabulary]
# Additional words to flag
additional = ["synergy", "utilize"]

# Domain-specific words to allow
allowed = ["crucial", "comprehensive"]

# Exact phrases V001 should skip (case-insensitive substring match)
allowed_phrases = ["All notable changes", "Critical issue"]
```

### Confidence Filtering

```toml
[tool.proseprobe]
# Minimum confidence to report (low, medium, high)
min_confidence = "low"  # default: show all
```

### Per-File Ignores

```toml
[[tool.proseprobe.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004"]

[[tool.proseprobe.per-file-ignores]]
pattern = "tests/**"
ignore = ["C001", "C002"]
```

### Inline Suppressions

Use a line-scoped directive when a single intentional finding should remain in
the source. Markdown targets the immediately following physical line:

```markdown
<!-- proseprobe-ignore-next-line V001,S010 -->
This documentation delves into three related concerns.
```

Python targets the same physical line as a real comment token:

```python
"""This documentation delves into the API."""  # proseprobe: ignore=V001,S010
```

Each token must be an existing rule ID or one-letter category prefix. Tokens
are case-insensitive. Empty, malformed, or unknown tokens are configuration
errors. Directives inside Markdown code fences or Python strings have no
effect. Wider regions should continue to use per-file ignores.

### Thresholds

```toml
[tool.proseprobe.thresholds]
# S001: Rule of three - max triads per document
rule_of_three = 3
# S004: Inline header lists - min consecutive inline headers to flag
inline_header_lists = 3
# T002: Bold overuse - max bold phrases per paragraph
bold_overuse = 3
# T003: Em dash overuse - max em dashes per document
em_dash_overuse = 5
# G011: Nominalization overload - min nominalizations to flag
nominalization_overload = 3
# G012: Passive voice overuse - min formulaic passives to flag
passive_voice_overuse = 5
# T008: Sentence length - max words per sentence
sentence_length_max = 40
# S018: Citation name-dropping - min consecutive citations to flag
citation_name_drop = 3
# S010: Anaphora abuse - min repeated sentence openings to flag
anaphora_abuse = 3
# S011: Gerund fragment litany - min consecutive gerund fragments to flag
gerund_fragment_litany = 3
# S013: Historical analogy stacking - min company name-drops to flag
historical_analogy_stacking = 3
# T007: Short punchy fragments - min consecutive short paragraphs to flag
short_punchy_fragments = 3
# V007: Invented concept labels - min pseudo-analytical labels to flag
invented_concept_labels = 2
# S022: Wall-of-text paragraph - min sentences per paragraph to flag
wall_of_text_sentences = 6
```

Every threshold must be a positive integer. Zero, negative values, booleans,
and unknown threshold keys are configuration errors.

### Validation

Only documented keys are accepted in the proseprobe configuration table and its
nested vocabulary, threshold, and per-file-ignore tables. Rule IDs and category
prefixes are normalized to uppercase; repeated references are collapsed.
Unknown profiles, keys, or rule references stop scan commands with exit code 2.
`--show-config` prints the effective normalized policy and the explicit or
auto-discovered source path, or `default` when no file was loaded.

## Example Configuration

```toml
[tool.proseprobe]
include = ["*.md", "*.mdx", "*.markdown", "*.py"]
exclude = [
    "venv/**",
    ".venv/**",
    "node_modules/**",
    ".git/**",
    "*.min.js",
    "docs/_build/**",
]

profile = "technical-docs"
ignore = ["T001", "T005"]
minimum_severity = "warning"

[tool.proseprobe.severity]
V001 = "error"
M002 = "error"
M004 = "error"

[tool.proseprobe.vocabulary]
additional = ["leverage", "synergy"]
allowed = ["comprehensive"]
allowed_phrases = ["All notable changes"]

[[tool.proseprobe.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004", "V004"]

[[tool.proseprobe.per-file-ignores]]
pattern = "tests/**"
ignore = ["C001", "C002", "C003"]
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NO_COLOR` | Disable colored output |
| `FORCE_COLOR` | Force colored output |

## CLI Precedence

CLI arguments override config file settings:

```bash
# Config says ignore T001, but CLI enables it
proseprobe check --select T001 .
```

All scan commands use the resulting policy in this order:

1. Start with legacy defaults, then apply a configured profile.
2. Apply explicit config `select`, `minimum_severity`, and `min_confidence` keys.
3. Apply a CLI `--profile`, then direct CLI selection, ignore, severity, and
   confidence flags.
4. Apply per-rule severity overrides and the effective minimum severity.
5. Scan files using include, exclude, `.gitignore`, and per-file ignore rules.
6. Remove findings covered by valid inline suppressions.
7. Remove findings below the effective confidence threshold.
8. Remove findings already present in an optional baseline.

Independent config overlays—global and per-file ignores, per-rule severity,
file patterns, vocabulary, and thresholds—remain active under a CLI profile.

This order makes one watch iteration report the same ordered findings as
`check` when given the same paths and shared options.

## Baseline Lifecycle

Create a version 2 baseline and use it to report only new findings:

```bash
proseprobe baseline create --baseline .proseprobe-baseline.json .
proseprobe check --baseline .proseprobe-baseline.json .
```

Maintain it with one of three explicit actions:

```bash
# Report active, stale, and new counts without writing
proseprobe baseline summary --baseline .proseprobe-baseline.json .

# Accept new findings and retain stale entries
proseprobe baseline update --baseline .proseprobe-baseline.json .

# Remove stale entries without accepting new findings
proseprobe baseline prune --baseline .proseprobe-baseline.json .
```

The baseline command applies the normal configuration, rule selection,
severity, inline suppression, and confidence filters before comparing entries.
All successful maintenance actions return 0 and print active, stale, new, and
final entry counts.

Version 2 stores deterministic entries containing a repository-relative path,
rule ID, normalized matched source, and a hash of limited same-line context. It
does not depend on line numbers, diagnostic messages, severity, confidence, or
neighboring lines. A shared Git root is preferred as the workspace; non-Git
inputs use their common scan root, independent of argument order.

Version 1 fingerprint files remain readable for one compatibility cycle.
`update` or `prune` migrates observable active findings to version 2 and reports
unmatched opaque hashes as stale. Baseline writes use atomic replacement and
deterministic ordering. An explicitly requested missing, malformed, unreadable,
or unsupported file is a configuration error (exit code 2); it is never treated
as an optional warning.

`check --generate-baseline` remains a compatibility alias for creating a
version 2 file and retains its existing overwrite behavior.

## CLI Options Reference

| Option | Short | Commands | Description |
|--------|-------|----------|-------------|
| `--profile` | | all scans | Built-in profile: general, technical-docs, academic, journalism, business |
| `--select` | `-s` | all scans | Rules to enable (comma-separated) |
| `--ignore` | `-i` | all scans | Rules to disable (comma-separated) |
| `--config` | `-c` | all scans | Path to configuration file |
| `--severity` | | all scans | Minimum severity: error, warning, info |
| `--min-confidence` | | all scans | Minimum confidence: high, medium, low |
| `--hide-low` | | all scans | Shorthand for `--min-confidence medium` |
| `--baseline` | `-b` | all scans | Path to baseline file for incremental adoption |
| `--quiet` | `-q` | all scans | In text reports, output only errors |
| `--verbose` | `-v` | all scans | Show additional diagnostic info |
| `--show-config` | | check | Display configuration and exit |
| `--format` | `-f` | check | Output format: text, json, jsonl, sarif |
| `--format` | `-f` | rules, explain | Metadata output format: text, json |
| `--filename` | | check | Required virtual path and file type for standard input `-` |
| `--generate-baseline` | | check | Generate baseline file from current issues |
| `--interval` | `-n` | watch | Check interval in seconds |
| `--no-clear` | | watch | Do not clear the screen between checks |

Watch is text-only because its output is a continuous stream. For `check`,
grouped JSON and SARIF reports and JSON Lines records are written to stdout,
while operational errors and verbose status messages are written to stderr.

## Standard Input

Lint one generated document without creating a temporary file:

```bash
generate-draft | proseprobe check - --filename docs/draft.md --format json
```

`--filename` is required and controls file-type rules, per-file ignores, and
the reported path. Standard input cannot be mixed with filesystem paths or used
with baseline filtering or generation. Configuration is discovered from the
current working directory.

## Output Formats

### Text (default)

```
docs/guide.md:15:5: V001 [high] [warning] Overused word: 'delve' → consider 'explore'
docs/guide.md:23:1: S001 [info] Triadic pattern (rule of three): 'fast, safe, and clear'

Found 2 issue(s) (0 error, 1 warning, 1 info) in 1 file(s)
Confidence: 1 high, 1 medium, 0 low
```

### JSON

```bash
proseprobe check --format json . > report.json
```

```json
{
  "schema_version": 1,
  "version": "0.1.0",
  "files": [
    {
      "path": "docs/guide.md",
      "issues": [
        {
          "rule_id": "V001",
          "message": "Overused word: 'delve' → consider 'explore'",
          "line": 15,
          "column": 5,
          "end_line": null,
          "end_column": 10,
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

### JSON Lines

Use JSON Lines for line-oriented subprocess and agent integrations:

```bash
proseprobe check --format jsonl . > diagnostics.jsonl
```

Each line is one complete diagnostic object:

```json
{"schema_version":1,"version":"0.1.0","path":"docs/guide.md","rule_id":"V001","message":"Overused word: 'delve' → consider 'explore'","line":15,"column":5,"end_line":null,"end_column":10,"severity":"warning","confidence":"high","suggestion":"explore"}
```

Records use the same `schema_version`, package `version`, diagnostic fields,
position semantics, and nullable fields as grouped JSON. Files are ordered by
path, issue order within each file is preserved, and every record ends with one
newline. JSON Lines has no wrapper, summary, or metadata record; use grouped
JSON when run totals are required. A clean run writes no stdout. Operational
and configuration diagnostics stay on stderr. Exit `0` may include info
records, while warning or error records produce exit `1`.

### SARIF

For GitHub Code Scanning integration:

```bash
proseprobe check --format sarif . > results.sarif
```

### Rule Metadata JSON

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

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | No warning or error findings; info findings may still be reported |
| `1` | Warning or error findings reported |
| `2` | Configuration or usage error |
| `3` | An input file could not be read |

## Pre-commit Integration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/johnmulder/proseprobe
    rev: v0.1.0
    hooks:
      - id: proseprobe
        args: [--select, "V001,V002,M002,M003"]
```

## GitHub Actions Integration

```yaml
# .github/workflows/lint.yml
name: Lint prose and documentation
on: [push, pull_request]

jobs:
  proseprobe:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'
      - run: pip install proseprobe
      - run: proseprobe check --format sarif docs/ > results.sarif || test $? -eq 1
      - uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: results.sarif
```
