# Simplification Plan

1. Replace custom Git ignore parsing with `git check-ignore`, retain configured glob exclusions, and replace the `LintResults` dictionary subclass with a dataclass. Run focused linter tests and quality checks; commit.
2. Replace reflective rule discovery and constructor inspection with an explicit rule list, and replace lazy scope-extractor registration with direct dispatch. Run focused rule and parser tests plus quality checks; commit.
3. Remove undocumented legacy configuration shapes and keep the documented TOML schema. Update focused tests and documentation as needed; run quality checks; commit.
4. Replace the reporter facade/registry with one formatting function and replace the baseline fingerprint transfer object with a plain dictionary. Update focused tests and callers; run quality checks; commit.
5. Run the complete quality and correctness suite, remove this plan, and commit the completed cleanup.
