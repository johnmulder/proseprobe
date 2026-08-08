# slop-lint

A Unix-style command-line tool to detect bad writing practices in Markdown and Python files.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

Overused vocabulary, structural clichés, promotional language, and sloppy markup creep into documentation and code all the time. **slop-lint** detects these bad practices and helps you write clearer, more direct prose.

## Features

- 🔍 **64 detection rules** across 6 categories
- 📝 Scans Markdown prose and source-mapped Python docstrings and comments
- 🎯 **Confidence levels** (high/medium/low) to reduce noise
- 🗂️ Built-in profiles for general, technical, academic, journalism, and business prose
- ⚙️ Configurable via `.slop-lint.toml`
- 📊 Multiple output formats (text, JSON, JSON Lines, SARIF)
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

# Output one JSON diagnostic per line
slop-lint check --format jsonl .

# Check one document from standard input
printf 'This documentation delves into the API.\n' | \
  slop-lint check - --filename draft.md --format json

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
slop-lint rules --format json

# Explain a specific rule
slop-lint explain V001
slop-lint explain V001 --format json
```

`rules --format json` and `explain RULE --format json` expose the canonical
default rule metadata for machine consumers; human-readable output remains the
default.

`check` and `watch` apply rule selection, severity, inline suppressions,
confidence, and baseline filters in the same order. Watch output is text-only;
grouped JSON and SARIF are complete `check` reports, while JSON Lines emits one
diagnostic per line and no output for a clean run. Operational errors and
verbose status messages go to stderr so redirected stdout remains valid
structured data. The versioned JSON contracts and field semantics are
documented in the [configuration guide](docs/configuration.md#output-formats).

Standard input uses `-` with a required `--filename` virtual path. It cannot be
mixed with filesystem paths or baselines; project configuration is still
discovered from the current working directory.

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
| `G` | Grammar | 15 | Grammatical patterns |
| `C` | Code | 4 | Python docstring/comment issues |
| `M` | Markup | 8 | Markdown artifacts |
| **Total** | | **64** | |

<!-- rule-docs:categories:end -->

Most prose-scoped `V`, `S`, `T`, and `G` rules run on Markdown prose and
source-mapped Python docstrings and comments; `G015` examines only Markdown
document openers. `C` rules cover Python-specific documentation issues. `M001`
checks Markdown syntax in Python comments, while `M002`-`M008` are Markdown-only.
Wrapped prose is segmented once into cached sentences that retain start and end
line and column positions. Conservative standard-library handling keeps common
abbreviations, decimals, URLs, trailing quotes, and hard prose-block boundaries
without adding an NLP dependency.

### Example Detections

```
docs/guide.md:15:10: V001 [warning] Overused word: 'delve' → consider 'explore'
docs/guide.md:23:1: S001 [info] Triadic pattern (rule of three): 'fast, safe, and clear'
src/main.py:45:8: V002 [warning] Collaborative phrase: 'I hope this helps'
```

## Configuration

Create a `.slop-lint.toml` in your project root:

```toml
[tool.slop-lint]
include = ["*.md", "*.mdx", "*.markdown", "*.py"]
exclude = ["venv/**", ".venv/**", "node_modules/**", ".git/**"]
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
| 0 | No warning or error findings (info findings may still be reported) |
| 1 | Warning or error findings reported |
| 2 | Configuration or usage error |
| 3 | An input file could not be read |

## CI/CD Integration

### GitHub Actions

```yaml
permissions:
  contents: read
  security-events: write

steps:
  - uses: actions/checkout@v7

  - name: Install slop-lint
    run: pip install slop-lint

  - name: Check for bad writing practices
    run: slop-lint check --format sarif . > results.sarif || test $? -eq 1

  - name: Upload SARIF
    uses: github/codeql-action/upload-sarif@v4
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
- [Agent integration guide](docs/agent-integration.md) — Portable lint-and-repair workflow for coding agents
- [Portable Agent Skill](skills/slop-lint/SKILL.md) — Installable workflow for skills-compatible agents

The `skills/slop-lint/` directory is the copyable distribution unit. Copy it
into the skills location documented by your agent.
Install the `slop-lint` executable separately before using the skill.
The Python wheel does not install the skill or add provider-specific plugin
metadata.

### Codex plugin marketplace

Codex users can install the same skill through the
[Codex plugin marketplace](.agents/plugins/marketplace.json) checked into this
repository. From the root of a cloned checkout, run:

```bash
codex plugin marketplace add "$PWD/.agents/plugins"
codex plugin add slop-lint@slop-lint
```

Install the `slop-lint` executable separately before using the plugin.
The Codex wrapper is not included in the Python wheel.
Start a new Codex thread after installation so it loads the skill.

## Why "slop-lint"?

Sloppy writing is everywhere—vague buzzwords, wall-of-text paragraphs, promotional fluff, broken markup. slop-lint catches these patterns so you can write documentation and code comments that are clear, direct, and worth reading.

## License

MIT License. See [LICENSE](LICENSE) for details.
