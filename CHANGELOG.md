# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- M006 detects explicit Markdown template residue at high confidence and
  standalone TODO/TBD placeholders at low confidence.
- M005 detects undefined Markdown reference labels at high confidence and
  conflicting duplicate definitions at low confidence.
- Canonical immutable rule metadata and deterministic generated rule-reference
  tables, maintained with `make rule-docs` and checked by `make check`.
- Built-in `general`, `technical-docs`, `academic`, `journalism`, and `business`
  rule profiles for config files and all scan commands.
- Structured version 2 baselines and `baseline create`, `update`, `prune`, and
  `summary` maintenance actions.
- `minimum_severity` configuration key, which can coexist with the per-rule
  `[tool.slop-lint.severity]` override table.
- Line-scoped Markdown and Python suppression directives with rule-ID and
  category-prefix validation.
- Reviewed rule-quality corpus and `make rule-quality` precision/recall report.
- New Makefile targets for TDD and validation workflows:
  - `test-tdd` (fast red/green loop)
  - `test-spec` (spec-focused regression subset)
  - `startup-check`, `perf-check`, `memory-check`, `nfr-check` (NFR probes)

### Fixed
- Duplicate same-rule findings from overlapping G002, S012, and V001 patterns.
- G003 false positives from unrelated progressive verbs and technical gerunds.
- M004 now reports explicit, empty, and bare-fragment Markdown link
  destinations at their source locations.

### Changed
- `rules` and `explain` now show canonical confidence, context, profile, and
  configuration metadata, while `--show-config` reports the effective profile
  and confidence policy; no-profile behavior remains unchanged.
- Baseline identity now uses repository-relative paths and normalized source
  context instead of diagnostic messages, line numbers, and adjacent lines.
- Explicit missing, malformed, unreadable, and unsupported baseline files now
  fail as configuration errors; version 1 files remain readable and migrate on
  maintenance writes.
- Configuration now rejects unknown keys and rule references, non-positive
  thresholds, blank per-file patterns, and ambiguous severity settings.
- Rule references are normalized to uppercase, and `--show-config` now reports
  the explicit or auto-discovered configuration source.
- Prose-scoped vocabulary, grammar, structure, and style rules now inspect
  source-mapped Python docstrings and comments as independent blocks.
- Python parsing is shared and boundedly cached across prose and code rules;
  `C001` now reports only docstring vocabulary not covered by `V001`.
- `check` and `watch` now share rule selection, severity, confidence, baseline,
  and text-reporting behavior; structured output diagnostics are kept on stderr.
- Markdown prose rules now preserve source columns and respect paragraph,
  heading, list, block-quote, code, HTML, table, front-matter, and MDX/JSX
  boundaries instead of joining unrelated text.
- Closed key SPEC gaps across discovery, output, and execution behavior:
  - FR-01: default discovery now includes `.mdx` and `.markdown`.
  - FR-03: default text output now includes explicit severity labels.
  - FR-07: directory discovery now respects `.gitignore`, including nested files
    and negation precedence (`!pattern`).
  - FR-08: file checking now uses parallel execution with deterministic
    result ordering.
- Config auto-discovery order now aligns with documented behavior:
  1. current `.slop-lint.toml`
  2. current `pyproject.toml` `[tool.slop-lint]`
  3. parent `.slop-lint.toml` (up to git root)
  4. user config
- NFR validation workflow now includes reproducible coverage/startup/throughput
  probes via `make nfr-check`.
- Documentation updated for new defaults and behavior:
  - Markdown extension coverage defaults
  - Severity tags in text output
  - `.gitignore` semantics and precedence

### Added
- **Phase 2: Low-Quality Academic Writing Tropes** — 5 new rules, 1 enhancement, vocabulary expansions:
  - G011 (nominalization overload: "the implementation of the analysis")
  - G012 (passive voice overuse: "it is suggested that", "it has been shown that")
  - G013 (gap ritual: "the literature has overlooked", "fills that gap")
  - T008 (sentence length: flags sentences exceeding 40 words)
  - S018 (citation name-dropping: 3+ consecutive "Author (Year) verb" sentences)
  - G002 enhanced with hedge stacking detection (2+ hedges per sentence)
  - Expanded Tier 1 vocabulary with academic jargon: problematize, destabilize
  - Expanded Tier 2 vocabulary with academic words: foreground, situate,
    operationalize, instantiate, reconceptualize, positionality, relationality,
    assemblage, praxis, facilitate, demonstrate, regarding, implement
  - New configurable thresholds: nominalization_overload, passive_voice_overuse,
    sentence_length_max, citation_name_drop
- **Phase 1: Low-Quality Journalism Tropes** — 3 new rules and data expansions:
  - V008 (trend overclaim: "more and more people", "a growing number of")
  - G010 (false balance: "supporters say X, critics say Y", "the truth lies in the middle")
  - S017 (anecdote as evidence: "For Sarah of Ohio…", "Take Marcus, a…", "Meet Lisa")
  - Expanded V001 Tier 2 with journalism impact words (bombshell, shocking, devastating,
    explosive, stunning, firestorm, backlash, uproar) and pseudo-tech jargon
    (ecosystem, stakeholders, narrative)
  - Expanded V005 with anonymous source patterns (sources close to, a person familiar
    with the matter, officials speaking on condition of anonymity)
  - Added inflammatory cliché detection to V004 (sparked a firestorm, triggered
    widespread outrage, storm of criticism, sparked backlash)
- **Confidence levels**: Each issue now carries a `confidence` field (high, medium, low)
  - V001 assigns confidence by vocabulary tier (tier 1 → high, tier 2 → medium, tier 3 → low)
  - M001 issues in Python files default to low confidence
  - Issues under example headings in Markdown are downgraded to low
- **`--min-confidence`** CLI flag to filter issues by confidence level
- **`--hide-low`** flag as shorthand for `--min-confidence medium`
- **`min_confidence`** config option in `.slop-lint.toml`
- **`allowed_phrases`** vocabulary option to skip lines containing exact phrases
  - Ships with defaults: "All notable changes", "Critical issue"
- Confidence breakdown in text output summary line
- Confidence field in JSON and SARIF output
- M001 now skips `#`-prefixed lines inside Python string literals
- **Watch mode**: `slop-lint watch <paths>` for continuous file monitoring
- **Baseline mode**: `--baseline` and `--generate-baseline` for gradual adoption
- `--show-config` flag to display current configuration
- Pre-commit hook configuration (`.pre-commit-hooks.yaml`)
- GitHub Actions CI workflow for testing on Python 3.11, 3.12, 3.13
- **22 new AI-writing-trope rules** based on [tropes.fyi](https://tropes.fyi) catalogue:
  - V006-V007 (grandiose stakes, invented concept labels)
  - S008-S016 (dramatic countdown, rhetorical self-answer, anaphora abuse,
    gerund fragment litany, listicle in prose, historical analogy stacking,
    signposted conclusion, fractal summary, content duplication)
  - S019 (corporate euphemism)
  - S020 (alignment ritual)
  - S021 (slide deck fragment)
  - T007 (short punchy fragments)
  - G004-G009 (false suspense, patronizing analogy, futurist invitation,
    false vulnerability, asserted simplicity, pedagogical voice)
  - G014 (impersonal corporate passive)
- Complete documentation for all 59 rules with examples
- Full CLI options reference in configuration docs
- Property-based tests using Hypothesis (265 additional tests)
- Benchmark suite (`make benchmark`) for performance tracking
- `py.typed` marker for PEP 561 type checking support

### Changed
- Expanded regression coverage for CLI semantics, NFR probes, documentation,
  CI policy, and configuration validation.
- Improved package metadata and URLs

### Removed
- Auto-fix mechanism (`--fix`, `--dry-run`, `--interactive` flags)
- `core/fixer` module and `fix()` method on rules
- `fixable` field from `Issue` dataclass and rule classes

## [0.1.0] - 2026-02-01

### Added
- Initial release of slop-lint CLI
- 29 detection rules across 6 categories:
  - **V (Vocabulary)**: V001-V005 - Overused and clichéd words and phrases
  - **S (Structure)**: S001-S007 - Organizational patterns
  - **T (Style)**: T001-T006 - Formatting and style issues
  - **G (Grammar)**: G001-G003 - Grammar patterns
  - **C (Code)**: C001-C004 - Python code-specific issues
  - **M (Markup)**: M001-M004 - Markdown artifacts
- CLI commands:
  - `check` - Lint files for bad writing practices
  - `rules` - List all available rules
  - `explain` - Explain a specific rule
  - `init` - Create a `.slop-lint.toml` config file
  - `version` - Show version information
- Output formats: text, JSON, SARIF
- Configuration via `.slop-lint.toml` or `pyproject.toml`
- Per-file ignore patterns
- Custom vocabulary (additional/allowed words)
- 129 tests with 90%+ code coverage

### Technical
- Python 3.11+ required
- Strict mypy type checking
- Dependencies: typer, rich, tomli, mistune, regex

[Unreleased]: https://github.com/slop-lint/slop-lint/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/slop-lint/slop-lint/releases/tag/v0.1.0
