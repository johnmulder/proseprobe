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
