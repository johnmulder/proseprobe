# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- **Interactive fix**: `--fix --interactive` to confirm each fix individually
- `--dry-run` flag to preview fixes without modifying files
- `--show-config` flag to display current configuration
- Pre-commit hook configuration (`.pre-commit-hooks.yaml`)
- GitHub Actions CI workflow for testing on Python 3.11, 3.12, 3.13
- Complete documentation for all 29 rules with examples
- Full CLI options reference in configuration docs
- Property-based tests using Hypothesis (265 additional tests)
- Benchmark suite (`make benchmark`) for performance tracking
- `py.typed` marker for PEP 561 type checking support

### Changed
- Total test count: 436 tests passing
- Improved package metadata and URLs

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
- Auto-fix support for fixable rules
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
