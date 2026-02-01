# Configuration Reference

humanize can be configured via a `.humanize.toml` file or the `[tool.humanize]` section of `pyproject.toml`.

## Config File Discovery

Config files are discovered in this order:

1. `--config` CLI argument
2. `.humanize.toml` in current directory
3. `pyproject.toml` with `[tool.humanize]` section
4. `.humanize.toml` in parent directories (up to git root)
5. `~/.config/humanize/config.toml`

## Configuration Options

### File Patterns

```toml
[tool.humanize]
# Glob patterns for files to include
include = ["*.md", "*.py"]

# Glob patterns for files to exclude
exclude = ["venv/**", "node_modules/**", ".git/**"]
```

### Rule Selection

```toml
[tool.humanize]
# Rule prefixes or specific rules to enable
select = ["V", "S", "T", "G", "C", "M"]

# Rules to disable
ignore = ["T001", "T005"]
```

### Severity Configuration

```toml
[tool.humanize]
# Minimum severity to report
severity = "warning"  # error, warning, info

# Per-rule severity overrides
[tool.humanize.severity]
V001 = "error"      # Upgrade to error
S002 = "info"       # Downgrade to info
```

### Custom Vocabulary

```toml
[tool.humanize.vocabulary]
# Additional words to flag
additional = ["synergy", "utilize"]

# Domain-specific words to allow
allowed = ["crucial", "comprehensive"]
```

### Per-File Ignores

```toml
[[tool.humanize.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004"]

[[tool.humanize.per-file-ignores]]
pattern = "tests/**"
ignore = ["C001", "C002"]
```

## Example Configuration

```toml
[tool.humanize]
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

[tool.humanize.severity]
V001 = "error"
M002 = "error"
M004 = "error"

[tool.humanize.vocabulary]
additional = ["leverage", "synergy"]
allowed = ["comprehensive"]

[[tool.humanize.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004", "V004"]

[[tool.humanize.per-file-ignores]]
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
humanize check --select T001 .
```

## CLI Options Reference

| Option | Short | Description |
|--------|-------|-------------|
| `--fix` | | Apply auto-fixes for fixable issues |
| `--dry-run` | | Show what fixes would be applied without writing |
| `--show-config` | | Display configuration and exit |
| `--format` | `-f` | Output format: text, json, sarif |
| `--select` | `-s` | Rules to enable (comma-separated) |
| `--ignore` | `-i` | Rules to disable (comma-separated) |
| `--config` | `-c` | Path to configuration file |
| `--severity` | | Minimum severity: error, warning, info |
| `--quiet` | `-q` | Only output errors |
| `--verbose` | `-v` | Show additional diagnostic info |

## Output Formats

### Text (default)

```
docs/guide.md:15:5: V001 Avoid overused AI word "delve"
docs/guide.md:23:1: S001 Rule of three pattern detected
Found 2 issue(s)
```

### JSON

```bash
humanize check --format json . > report.json
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
          "message": "Avoid overused AI word \"delve\"",
          "line": 15,
          "column": 5,
          "severity": "warning",
          "fixable": true
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
humanize check --format sarif . > results.sarif
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
  - repo: https://github.com/yourusername/humanize-cli
    rev: v1.0.0
    hooks:
      - id: humanize
        args: [--select, "V001,V002,M002,M003"]
```

## GitHub Actions Integration

```yaml
# .github/workflows/lint.yml
name: Lint for AI Content
on: [push, pull_request]

jobs:
  humanize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install humanize-cli
      - run: humanize check --format sarif docs/ > results.sarif
        continue-on-error: true
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```
