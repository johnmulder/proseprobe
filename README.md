# slop-lint

A Unix-style command-line tool to detect bad writing practices in Markdown and Python files.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

Overused vocabulary, structural clichés, promotional language, and sloppy markup creep into documentation and code all the time. **slop-lint** detects these bad practices and helps you write clearer, more direct prose.

## Features

- 🔍 **59 detection rules** across 6 categories
- 📝 Scans Markdown (`.md`, `.mdx`, `.markdown`) and Python (`.py`) files
- 🎯 **Confidence levels** (high/medium/low) to reduce noise
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

# Watch mode (continuous checking)
slop-lint watch .

# Generate baseline for gradual adoption
slop-lint check --generate-baseline .

# Check only new issues (not in baseline)
slop-lint check --baseline .slop-lint-baseline.json .

# List all rules
slop-lint rules

# Explain a specific rule
slop-lint explain V001
```

## Detection Categories

| Prefix | Category | Rules | Description |
|--------|----------|-------|-------------|
| `V` | Vocabulary | 8 | Overused and clichéd words and phrases |
| `S` | Structure | 21 | Organizational patterns |
| `T` | Style | 8 | Typographic issues |
| `G` | Grammar | 14 | Grammatical patterns |
| `C` | Code | 4 | Python docstring/comment issues |
| `M` | Markup | 4 | Markdown artifacts |

### Example Detections

```
docs/guide.md:15:10: V001 [warning] Overused word: 'delve' → consider 'explore'
docs/guide.md:23:1: S001 [warning] Rule of three pattern detected
src/main.py:45:5: C001 [warning] Overused word in docstring: 'crucial'
```

## Configuration

Create a `.slop-lint.toml` in your project root:

```toml
[tool.slop-lint]
include = ["*.md", "*.mdx", "*.markdown", "*.py"]
exclude = ["venv/**", "node_modules/**"]

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

Or add to `pyproject.toml`:

```toml
[tool.slop-lint]
ignore = ["T001"]
```

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
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: results.sarif
```

### Pre-commit

```yaml
repos:
  - repo: https://github.com/yourusername/slop-lint
    rev: v0.1.0
    hooks:
      - id: slop-lint
```

## Development

```bash
# Clone and install development dependencies
git clone https://github.com/yourusername/slop-lint.git
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

## Documentation

- [SPEC.md](SPEC.md) — Technical specification
- [docs/rules.md](docs/rules.md) — Detailed rule documentation
- [docs/configuration.md](docs/configuration.md) — Configuration reference

## Why "slop-lint"?

Sloppy writing is everywhere—vague buzzwords, wall-of-text paragraphs, promotional fluff, broken markup. slop-lint catches these patterns so you can write documentation and code comments that are clear, direct, and worth reading.

## License

MIT License. See [LICENSE](LICENSE) for details.
