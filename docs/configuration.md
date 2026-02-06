# Configuration Reference

slop-lint can be configured via a `.slop-lint.toml` file or the `[tool.slop-lint]` section of `pyproject.toml`.

## Config File Discovery

Config files are discovered in this order:

1. `--config` CLI argument
2. `.slop-lint.toml` in current directory
3. `pyproject.toml` with `[tool.slop-lint]` section
4. `.slop-lint.toml` in parent directories (up to git root)
5. `~/.config/slop-lint/config.toml`

## Configuration Options

### File Patterns

```toml
[tool.slop-lint]
# Glob patterns for files to include
include = ["*.md", "*.py"]

# Glob patterns for files to exclude
exclude = ["venv/**", "node_modules/**", ".git/**"]
```

### Rule Selection

```toml
[tool.slop-lint]
# Rule prefixes or specific rules to enable
select = ["V", "S", "T", "G", "C", "M"]

# Rules to disable
ignore = ["T001", "T005"]
```

### Severity Configuration

```toml
[tool.slop-lint]
# Minimum severity to report
severity = "warning"  # error, warning, info

# Per-rule severity overrides
[tool.slop-lint.severity]
V001 = "error"      # Upgrade to error
S002 = "info"       # Downgrade to info
```

### Custom Vocabulary

```toml
[tool.slop-lint.vocabulary]
# Additional words to flag
additional = ["synergy", "utilize"]

# Domain-specific words to allow
allowed = ["crucial", "comprehensive"]

# Exact phrases to skip (line is not checked if it contains one)
allowed_phrases = ["All notable changes", "Critical issue"]
```

### Confidence Filtering

```toml
[tool.slop-lint]
# Minimum confidence to report (low, medium, high)
min_confidence = "low"  # default: show all
```

### Per-File Ignores

```toml
[[tool.slop-lint.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004"]

[[tool.slop-lint.per-file-ignores]]
pattern = "tests/**"
ignore = ["C001", "C002"]
```

## Example Configuration

```toml
[tool.slop-lint]
include = ["*.md", "*.py", "*.rst"]
exclude = [
    "venv/**",
    "node_modules/**",
    ".git/**",
    "*.min.js",
    "docs/_build/**",
]

select = ["V", "S", "T", "G", "C", "M"]
ignore = ["T001", "T005"]
severity = "warning"

[tool.slop-lint.severity]
V001 = "error"
M002 = "error"
M004 = "error"

[tool.slop-lint.vocabulary]
additional = ["leverage", "synergy"]
allowed = ["comprehensive"]
allowed_phrases = ["All notable changes"]

[[tool.slop-lint.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004", "V004"]

[[tool.slop-lint.per-file-ignores]]
pattern = "tests/**"
ignore = ["C001", "C002", "C003"]
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HUMANIZE_CONFIG` | Path to config file |
| `NO_COLOR` | Disable colored output |
| `FORCE_COLOR` | Force colored output |

## CLI Precedence

CLI arguments override config file settings:

```bash
# Config says ignore T001, but CLI enables it
slop-lint check --select T001 .
```

## CLI Options Reference

| Option | Short | Description |
|--------|-------|-------------|
| `--show-config` | | Display configuration and exit |
| `--format` | `-f` | Output format: text, json, sarif |
| `--select` | `-s` | Rules to enable (comma-separated) |
| `--ignore` | `-i` | Rules to disable (comma-separated) |
| `--config` | `-c` | Path to configuration file |
| `--severity` | | Minimum severity: error, warning, info |
| `--min-confidence` | | Minimum confidence: high, medium, low |
| `--hide-low` | | Hide low-confidence issues |
| `--quiet` | `-q` | Only output errors |
| `--verbose` | `-v` | Show additional diagnostic info |

## Output Formats

### Text (default)

```
docs/guide.md:15:5: V001 Overused word: 'delve'
docs/guide.md:23:1: S001 Rule of three pattern detected
Found 2 issue(s)
```

### JSON

```bash
slop-lint check --format json . > report.json
```

```json
{
  "version": "0.1.0",
  "files": [
    {
      "path": "docs/guide.md",
      "issues": [
        {
          "rule_id": "V001",
          "message": "Overused word: 'delve'",
          "line": 15,
          "column": 5,
          "severity": "warning",
          "confidence": "high"
        }
      ]
    }
  ],
  "summary": {
    "total_issues": 2,
    "errors": 0,
    "warnings": 2
  }
}
```

### SARIF

For GitHub Code Scanning integration:

```bash
slop-lint check --format sarif . > results.sarif
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success, no issues found |
| `1` | Issues found |
| `2` | Configuration or usage error |
| `3` | Internal error |

## Pre-commit Integration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/yourusername/slop-lint
    rev: v1.0.0
    hooks:
      - id: slop-lint
        args: [--select, "V001,V002,M002,M003"]
```

## GitHub Actions Integration

```yaml
# .github/workflows/lint.yml
name: Lint for Bad Writing Practices
on: [push, pull_request]

jobs:
  slop-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install slop-lint
      - run: slop-lint check --format sarif docs/ > results.sarif
        continue-on-error: true
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```
