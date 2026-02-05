# slop-lint

A Unix-style command-line tool to detect AI-generated content patterns in Markdown and Python files.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

Wikipedia editors have identified numerous patterns that reveal AI-generated content—overused vocabulary, structural tells, promotional language, and markup artifacts. **slop-lint** helps developers and writers detect these patterns in their documentation and code.

## Features

- 🔍 **29 detection rules** across 6 categories
- 📝 Scans Markdown (`.md`, `.mdx`) and Python (`.py`) files
- 🔧 Auto-fix for safe vocabulary substitutions
- ⚙️ Configurable via `.slop-lint.toml`
- 📊 Multiple output formats (text, JSON, SARIF)
- 🚀 Fast, parallel file processing

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

# Auto-fix safe issues
slop-lint check --fix .

# Interactive fix (confirm each change)
slop-lint check --fix --interactive .

# Output as JSON
slop-lint check --format json .

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
| `V` | Vocabulary | 5 | AI-specific words and phrases |
| `S` | Structure | 7 | Organizational patterns |
| `T` | Style | 6 | Typographic issues |
| `G` | Grammar | 3 | Grammatical patterns |
| `C` | Code | 4 | Python docstring/comment issues |
| `M` | Markup | 4 | Markdown artifacts |

### Example Detections

```
docs/guide.md:15:10: V001 AI vocabulary: 'delve' → consider 'explore'
docs/guide.md:23:1: S001 Rule of three pattern detected
src/main.py:45:5: C001 AI vocabulary in docstring: 'crucial'
```

## Configuration

Create a `.slop-lint.toml` in your project root:

```toml
[tool.slop-lint]
include = ["*.md", "*.py"]
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
- name: Check for AI patterns
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
# Clone and install
git clone https://github.com/yourusername/slop-lint.git
cd slop-lint
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Lint
ruff check src/
```

## Documentation

- [SPEC.md](SPEC.md) — Technical specification
- [PLAN.md](PLAN.md) — Implementation plan and AI coding agent guide
- [docs/rules.md](docs/rules.md) — Detailed rule documentation
- [docs/configuration.md](docs/configuration.md) — Configuration reference

## Why "slop-lint"?

The tool helps you *clean up* your writing by removing patterns that make text sound machine-generated. Clear, direct writing is better writing—whether for documentation, READMEs, or code comments.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

Detection patterns are based on research by Wikipedia editors documenting [signs of AI-generated content](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_use) and the characteristics of [large language model](https://en.wikipedia.org/wiki/Large_language_model) outputs.
