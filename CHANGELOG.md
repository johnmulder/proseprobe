# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.1.0 - Unreleased

### Added

- The ProseProbe CLI with `check`, `watch`, `rules`, `explain`, `init`, `version`,
  and `baseline` commands.
- 97 detection rules across vocabulary, structure, style, grammar, Python code,
  and Markdown markup categories.
- Markdown, MDX, and Python scanning with source-mapped prose blocks, sentences,
  docstrings, comments, and exact diagnostic spans.
- Built-in `general`, `technical-docs`, `academic`, `journalism`, and `business`
  profiles.
- Confidence levels, configurable severity, per-rule overrides, per-file ignores,
  custom vocabulary, thresholds, and validated rule selection.
- `.proseprobe.toml`, `[tool.proseprobe]`, and user-level configuration discovery.
- Line-scoped Markdown and Python suppression directives with rule-ID and
  category-prefix validation.
- Version 2 baselines with `create`, `update`, `prune`, and `summary` maintenance
  actions; version 1 baselines remain readable and migrate when written.
- Text, JSON, JSON Lines, and SARIF output with versioned structured schemas.
- Standard-input scanning with a virtual filename for generated documents.
- Parallel, deterministic directory scanning that respects nested `.gitignore`
  rules and negation.
- Canonical rule metadata plus generated rule-reference tables checked by CI.
- A portable Agent Skill, provider-neutral agent integration guide, and
  repo-local Codex marketplace plugin.
- A pre-commit hook definition and GitHub Actions checks for Python
  3.11, 3.12, and 3.13.
- Property-based tests, a reviewed rule-quality corpus, coverage enforcement,
  throughput benchmarks, startup and memory probes, and TDD Makefile targets.
- A `py.typed` marker for PEP 561 type checking support.

### Changed

- Renamed the project, distribution, import package, executable, configuration,
  directives, baseline, integrations, and metadata to ProseProbe/`proseprobe`.
- Shared and bounded Python and Markdown parsing caches across applicable rules.
- Preserved Markdown paragraph, heading, list, block-quote, code, HTML, table,
  front-matter, and MDX/JSX boundaries during prose analysis.
- Applied vocabulary, grammar, structure, and style rules to source-mapped Python
  docstrings and comments while keeping Python-specific rule ownership narrow.
- Unified `check` and `watch` selection, severity, confidence, baseline, and text
  reporting behavior.
- Based baseline identity on repository-relative paths and normalized source
  context instead of diagnostic wording or line numbers.
- Made configuration reject unknown keys and rules, invalid thresholds, blank
  patterns, and ambiguous severity settings.
- Expanded rule metadata, help output, and effective-configuration reporting.

### Fixed

- Removed duplicate same-rule findings from overlapping patterns.
- Reduced false positives for progressive verbs, technical gerunds, ordinary
  release dates, literal gap or dilemma references, restructuring terms, and
  evidence-backed claims.
- Reported malformed Markdown links, reference definitions, templates, unclosed
  fences, and skipped heading levels at their source locations.
- Preserved source columns and sentence boundaries through wrapped Markdown and
  Python prose.

### Removed

- Auto-fix behavior and its `--fix`, `--dry-run`, and `--interactive` options.
- The fixer module and `fixable` rule metadata.
- All third-party runtime dependencies; ProseProbe uses the Python standard
  library at runtime.
