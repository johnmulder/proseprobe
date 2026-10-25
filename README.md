# ProseProbe

A Unix-style linter for common prose, documentation, and Markdown problems.

[![CI](https://github.com/johnmulder/proseprobe/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/johnmulder/proseprobe/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/johnmulder/proseprobe/blob/master/LICENSE)

## Overview

Overused vocabulary, structural clichés, promotional language, and careless markup creep into documentation and code all the time. **ProseProbe** detects these bad practices and helps you write clearer, more direct prose.

## Features

- 🔍 **102 detection rules** across 6 categories
- 📝 Scans Markdown prose and source-mapped Python docstrings and comments
- 🎯 **Confidence levels** (high/medium/low) to reduce noise
- 🗂️ Built-in profiles for general, technical, academic, journalism, and business prose
- ⚙️ Configurable via `.proseprobe.toml`
- 📊 Multiple output formats (text, JSON, JSON Lines, SARIF)
- 🚀 Fast, parallel file processing
- 🧭 Directory discovery respects `.gitignore` patterns

## Current status

The autonomous merge work is complete on `master`. Its
[completion record](https://github.com/johnmulder/proseprobe/blob/master/quality/reviews/2026-10-16-completion/README.md)
preserves the engineering evidence and evaluation limits. The October 25, 2026
source preflight at `2fff536944bb91dff0d5012625b337b2f6979bba` passed 3,996 tests,
quality gates, and isolated package checks; the same commit passed the
[hosted CI matrix](https://github.com/johnmulder/proseprobe/actions/runs/39544639711).

Independent human annotation and suggestion-usefulness evaluation remain
unfinished. Curated regressions and agent reviews do not establish those human
outcomes. Publication is also pending; the
[release status](https://github.com/johnmulder/proseprobe/blob/master/RELEASE_BLOCKERS.md)
separates verified preparation from the remaining release work.

## Installation

ProseProbe has not been published to PyPI. Install the current source revision
from GitHub:

```bash
python -m pip install "proseprobe @ git+https://github.com/johnmulder/proseprobe.git"
```

## Quick Start

```bash
proseprobe check .
proseprobe check --profile technical-docs README.md docs/
proseprobe explain V001
```

See the
[configuration guide](https://github.com/johnmulder/proseprobe/blob/master/docs/configuration.md)
for watch mode, standard input, baselines, filters, output formats, and
integrations.

## Detection Categories

<!-- rule-docs:categories:start -->

| Prefix | Category | Rules | Description |
|--------|----------|-------|-------------|
| `V` | Vocabulary | 16 | Overused and clichéd words and phrases |
| `S` | Structure | 25 | Organizational patterns |
| `T` | Style | 14 | Typographic issues |
| `G` | Grammar | 26 | Grammatical patterns |
| `C` | Code | 9 | Python docstring/comment issues |
| `M` | Markup | 12 | Markdown artifacts |
| **Total** | | **102** | |

<!-- rule-docs:categories:end -->

Most prose-scoped `V`, `S`, `T`, and `G` rules run on Markdown prose and
source-mapped Python docstrings and comments; `G015` examines only Markdown
document openers. `C` rules cover Python-specific documentation issues. `M001`
checks Markdown syntax in Python comments, while `M002`-`M010`, `S025`, `S028`, and `S029` are
Markdown-only.
Wrapped prose is segmented once into cached sentences that retain start and end
line and column positions. Conservative standard-library handling keeps common
abbreviations, decimals, URLs, trailing quotes, and hard prose-block boundaries
without adding an NLP dependency.

### Example output

```text
docs/guide.md:15:10: V001 [warning] Overused word: 'delve' → consider 'explore'
docs/guide.md:23:1: S001 [info] Triadic pattern (rule of three): 'fast, safe, and clear'
src/main.py:45:8: V002 [warning] Collaborative phrase: 'I hope this helps'
```

## Configuration

Add a `.proseprobe.toml` to the project root:

```toml
[tool.proseprobe]
profile = "technical-docs"
minimum_severity = "warning"
ignore = ["T001", "T005"]
```

The
[configuration reference](https://github.com/johnmulder/proseprobe/blob/master/docs/configuration.md)
documents every setting, profile, suppression, precedence rule, and exit code.

## Development

```bash
# Clone and install development dependencies
git clone https://github.com/johnmulder/proseprobe.git
cd proseprobe
make dev

# Full local check
make check

# Reject new curated quality mismatches under both reviewed policies
make rule-quality-regression
```

Rule classes are the source of truth for IDs, names, descriptions, default
severity and confidence, file contexts, and optional configuration keys. After
adding or changing a rule, register it in `get_all_rules()`, update its profile
membership, and run `make rule-docs`. Do not edit content between
`rule-docs` markers by hand; `make check` rejects stale generated content.

## Documentation

- [Technical specification](https://github.com/johnmulder/proseprobe/blob/master/SPEC.md)
- [Rule reference](https://github.com/johnmulder/proseprobe/blob/master/docs/rules.md)
- [Configuration reference](https://github.com/johnmulder/proseprobe/blob/master/docs/configuration.md)
- [Agent integration guide](https://github.com/johnmulder/proseprobe/blob/master/docs/agent-integration.md)
- [Portable Agent Skill](https://github.com/johnmulder/proseprobe/blob/master/skills/proseprobe/SKILL.md)

The `skills/proseprobe/` directory is the copyable distribution unit. Copy it
into the skills location documented by your agent.
Install the `proseprobe` executable separately before using the skill.
The Python wheel does not install the skill or add provider-specific plugin
metadata.

### Codex plugin marketplace

Codex users can install the same skill through the
[Codex plugin marketplace](https://github.com/johnmulder/proseprobe/blob/master/.agents/plugins/marketplace.json) checked into this
repository. From the root of a cloned checkout, run:

```bash
codex plugin marketplace add "$PWD/.agents/plugins"
codex plugin add proseprobe@proseprobe
```

Install the `proseprobe` executable separately before using the plugin.
The Codex wrapper is not included in the Python wheel.
Start a new Codex thread after installation so it loads the skill.

## License

MIT License. See the
[license text](https://github.com/johnmulder/proseprobe/blob/master/LICENSE)
for details.
