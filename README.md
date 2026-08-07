# slop-lint

A Unix-style command-line tool to detect bad writing practices in Markdown and Python files.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

Overused vocabulary, structural clichés, promotional language, and sloppy markup creep into documentation and code all the time. **slop-lint** detects these bad practices and helps you write clearer, more direct prose.

## Features

- 🔍 **59 detection rules** across 6 categories
- 📝 Scans Markdown prose and source-mapped Python docstrings and comments
- 🎯 **Confidence levels** (high/medium/low) to reduce noise
- 🗂️ Built-in profiles for general, technical, academic, journalism, and business prose
- ⚙️ Configurable via `.slop-lint.toml`
- 📊 Multiple output formats (text, JSON, SARIF)
- 🚀 Fast, parallel file processing
- 🧭 Directory discovery respects `.gitignore` patterns

## Installation

```bash
pip install slop-lint
```

Or with [pipx](https://pipx.pypa.io/):

```bash
pipx install slop-lint
```

## Quick Start

```bash
# Check current directory
slop-lint check .

# Check specific files
slop-lint check README.md docs/

# Output as JSON
slop-lint check --format json .

# Filter by confidence level
slop-lint check --min-confidence high .
slop-lint check --hide-low .

# Apply a built-in rule profile
slop-lint check --profile technical-docs .

# Watch mode (continuous checking)
slop-lint watch .

# Watch with the same filters used by check
slop-lint watch --severity error --min-confidence high \
  --baseline .slop-lint-baseline.json .

# Create a baseline for gradual adoption
slop-lint baseline create --baseline .slop-lint-baseline.json .

# Check only new issues (not in baseline)
slop-lint check --baseline .slop-lint-baseline.json .

# Inspect, accept, or remove baseline entries
slop-lint baseline summary --baseline .slop-lint-baseline.json .
slop-lint baseline update --baseline .slop-lint-baseline.json .
slop-lint baseline prune --baseline .slop-lint-baseline.json .

# List all rules
slop-lint rules

# Explain a specific rule
slop-lint explain V001
```

`check` and `watch` apply rule selection, severity, inline suppressions,
confidence, and baseline filters in the same order. Watch output is text-only;
JSON and SARIF are complete `check` reports, with diagnostics kept on stderr so
redirected stdout remains valid structured data.

Baselines use repository-relative source identity rather than line numbers or
diagnostic wording. `update` explicitly accepts new findings, while `prune`
removes stale entries without accepting new ones. The older
`check --generate-baseline` form remains supported.

## Detection Categories

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

Prose-scoped `V`, `S`, `T`, and `G` rules run on Markdown prose and
source-mapped Python docstrings and comments. `C` rules cover Python-specific
documentation issues, while Markdown syntax rules remain Markdown-only.

### Example Detections

```
docs/guide.md:15:10: V001 [warning] Overused word: 'delve' → consider 'explore'
docs/guide.md:23:1: S001 [warning] Rule of three pattern detected
src/main.py:45:8: V002 [warning] Collaborative phrase: 'I hope this helps'
```

## Configuration

Create a `.slop-lint.toml` in your project root:

```toml
[tool.slop-lint]
include = ["*.md", "*.mdx", "*.markdown", "*.py"]
exclude = ["venv/**", "node_modules/**"]
profile = "technical-docs"
minimum_severity = "warning"

# Disable specific rules
ignore = ["T001", "T005"]

# Upgrade severity
[tool.slop-lint.severity]
V001 = "error"

# Allow domain-specific vocabulary
[tool.slop-lint.vocabulary]
allowed = ["crucial", "comprehensive"]

# Per-file overrides
[[tool.slop-lint.per-file-ignores]]
pattern = "CHANGELOG.md"
ignore = ["S004"]
```

Rule IDs and one-letter category prefixes are case-insensitive. Unknown keys,
unknown rule references, and non-positive thresholds are configuration errors;
`slop-lint check --show-config` prints the normalized policy and its source.

The built-in profiles are `general`, `technical-docs`, `academic`,
`journalism`, and `business`. A profile supplies rule, severity, and confidence
defaults. Explicit configuration keys override a configured profile; a CLI
`--profile` overrides that lower policy, and direct CLI filter flags win last.

Or add to `pyproject.toml`:

```toml
[tool.slop-lint]
ignore = ["T001"]
```

## Inline Suppressions

Use an existing rule ID or one-letter category prefix when one intentional
finding should not require a wider ignore. Markdown targets the immediately
following physical line:

```markdown
<!-- slop-lint-ignore-next-line V001,S010 -->
This documentation delves into three related concerns.
```

Python targets the same physical line as a real comment token:

```python
"""This documentation delves into the API."""  # slop-lint: ignore=V001,S010
```

Directives are applied before confidence and baseline filtering. Empty,
malformed, or unknown tokens are configuration errors; markers in Markdown
code fences and Python strings are inert examples.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No issues found |
| 1 | Issues found |
| 2 | Configuration error |
| 3 | Internal error |

## CI/CD Integration

### GitHub Actions

```yaml
- name: Check for bad writing practices
  run: |
    pip install slop-lint
    slop-lint check --format sarif . > results.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

### Pre-commit

```yaml
repos:
  - repo: https://github.com/slop-lint/slop-lint
    rev: v0.1.0
    hooks:
      - id: slop-lint
```

## Development

```bash
# Clone and install development dependencies
git clone https://github.com/slop-lint/slop-lint.git
cd slop-lint
make dev

# Run tests
make test

# Type checking
make typecheck

# Lint
make lint

# Full local check
make check
```

Rule classes are the source of truth for IDs, names, descriptions, default
severity and confidence, file contexts, and optional configuration keys. After
adding or changing a rule, register it in `get_all_rules()`, update its profile
membership, and run `make rule-docs`. Do not edit content between
`rule-docs` markers by hand; `make check` rejects stale generated content.

## Documentation

- [SPEC.md](SPEC.md) — Technical specification
- [docs/rules.md](docs/rules.md) — Detailed rule documentation
- [docs/configuration.md](docs/configuration.md) — Configuration reference

## Why "slop-lint"?

Sloppy writing is everywhere—vague buzzwords, wall-of-text paragraphs, promotional fluff, broken markup. slop-lint catches these patterns so you can write documentation and code comments that are clear, direct, and worth reading.

## License

MIT License. See [LICENSE](LICENSE) for details.
