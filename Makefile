.DEFAULT_GOAL := help

.PHONY: help install dev test test-tdd test-spec test-cov lint typecheck format check all clean build dogfood quick benchmark rule-quality rule-docs rule-docs-check test-tropes test-tropes-integration doc-audit spec-verify coverage-analyze startup-check perf-check memory-check nfr-check

VENV ?= .venv
VENV_BIN = $(VENV)/bin

PYTHON = $(VENV_BIN)/python
PIP = $(VENV_BIN)/pip
PYTEST = $(VENV_BIN)/pytest
RUFF = $(VENV_BIN)/ruff
MYPY = $(VENV_BIN)/mypy
TIME = /usr/bin/time

PYTEST_ARGS ?= tests/

ifeq ($(wildcard $(PYTHON)),)
PYTHON = python
PIP = pip
PYTEST = pytest
RUFF = ruff
MYPY = mypy
endif

help: ## Show available development commands
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup:"
	@echo "  install              Install package in editable mode"
	@echo "  dev                  Install package with development dependencies"
	@echo ""
	@echo "Core checks:"
	@echo "  test                 Run the test suite"
	@echo "  test-tdd             Run the fast TDD test loop"
	@echo "  lint                 Run ruff"
	@echo "  typecheck            Run mypy"
	@echo "  check                Run lint, typecheck, and tests"
	@echo "  all                  Alias for check"
	@echo ""
	@echo "Maintenance:"
	@echo "  format               Format code and apply ruff fixes"
	@echo "  clean                Remove generated build, test, and cache artifacts"
	@echo "  build                Build source and wheel distributions"
	@echo "  dogfood              Run proseprobe on its own docs"
	@echo "  rule-docs            Update generated rule documentation"
	@echo "  rule-docs-check      Verify generated rule documentation"
	@echo ""
	@echo "Analysis:"
	@echo "  test-cov             Run tests with coverage reports"
	@echo "  coverage-analyze     Enforce the coverage threshold"
	@echo "  benchmark            Run throughput benchmarks"
	@echo "  rule-quality         Measure rule precision and recall"
	@echo "  nfr-check            Run coverage, startup, performance, and memory probes"

# Install production dependencies
install: ## Install package in editable mode
	$(PIP) install -e .

# Install development dependencies
dev: ## Install package with development dependencies
	$(PIP) install -e ".[dev]"

# Run tests
test: ## Run tests
	$(PYTEST) $(PYTEST_ARGS) -v

# Fast TDD loop: stop on first failure with concise output
test-tdd: ## Run fast TDD loop
	$(PYTEST) $(PYTEST_ARGS) -x -q

# SPEC-alignment regression tests
test-spec: ## Run SPEC-alignment regression tests
	$(PYTEST) tests/test_cli.py tests/test_config.py tests/test_linter.py -q

# Run tests with coverage
test-cov: ## Run tests with coverage reports
	$(PYTEST) tests/ -v --cov=src/proseprobe --cov-report=term-missing --cov-report=html --cov-report=xml

# Run linter
lint: ## Run ruff
	$(RUFF) check src/ tests/

# Run type checker
typecheck: ## Run mypy
	$(MYPY) src/

# Format code
format: ## Format code
	$(RUFF) format src/ tests/
	$(RUFF) check --fix src/ tests/

# Run all checks
check: rule-docs-check lint typecheck test ## Run generated-doc, lint, type, and test checks

# Clean build artifacts
clean: ## Remove generated artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .hypothesis/
	rm -rf .tox/
	rm -rf .nox/
	rm -rf .cache/
	rm -f .coverage
	rm -f .coverage.*
	rm -f coverage.xml
	rm -f junit.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name "*.egg-info" -prune -exec rm -rf {} +
	find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

# Build package
build: clean ## Build package
	$(PYTHON) -m build

# Run proseprobe on itself (dogfooding)
dogfood: ## Run proseprobe on its own docs
	$(PYTHON) -m proseprobe check README.md docs/ --baseline .proseprobe-baseline.json

# Quick check for development
quick: ## Run quick local fix-and-test loop
	$(RUFF) check src/ --fix
	$(PYTEST) tests/ -x -q

# Run benchmarks
benchmark: ## Run benchmarks
	$(PYTHON) -m benchmarks.bench_rules

# Measure rule precision and recall on the reviewed corpus
rule-quality: ## Measure rule precision and recall
	$(PYTHON) -m benchmarks.rule_quality

# Generate repetitive rule reference content from canonical metadata
rule-docs: ## Update generated rule documentation
	$(PYTHON) -m proseprobe._rule_docs --write

rule-docs-check: ## Verify generated rule documentation
	$(PYTHON) -m proseprobe._rule_docs --check

# Run only trope-related tests (fast TDD loop)
test-tropes: ## Run trope-related rule tests
	$(PYTEST) tests/test_rules/ -v -k "S008 or S009 or S010 or S011 or S012 or S013 or S014 or S015 or S016 or S017 or S018 or G004 or G005 or G006 or G007 or G008 or G009 or G010 or G011 or G012 or G013 or T007 or T008 or V006 or V007 or V008 or magic_adverb or grandiose or invented_concept or patronizing or futurist or false_suspense or pedagogical or asserted_simplicity or false_vulnerability or punchy or gerund_litany or anaphora or rhetorical_self or dramatic_countdown or listicle_prose or analogy_stack or signposted or fractal_summary or content_duplication or trend_overclaim or false_balance or anecdote_evidence or bombshell or firestorm or anonymous_source or nominalization or passive_voice or hedge_stacking or gap_ritual or sentence_length or citation_name"

# Integration: verify all-rules fixture still reports issues
test-tropes-integration: ## Verify the all-rules Markdown fixture still reports issues
	@$(PYTHON) -m proseprobe check tests/fixtures/all_markdown_rules_fire.md --format json --severity info >/tmp/proseprobe-tropes.json || test $$? -eq 1
	@$(PYTHON) -c "import json; data=json.load(open('/tmp/proseprobe-tropes.json')); assert data['summary']['total_issues'] > 0"

# Full validation (lint + type-check + test)
all: check ## Alias for check

# Verify README/SPEC structure matches expected sections
doc-audit: rule-docs-check ## Verify generated docs and README/SPEC structure
	@echo "Checking README.md structure..."
	@grep -q "## Overview" README.md || (echo "ERROR: README missing ## Overview" && exit 1)
	@grep -q "## Installation" README.md || (echo "ERROR: README missing ## Installation" && exit 1)
	@grep -q "## Quick Start" README.md || (echo "ERROR: README missing ## Quick Start" && exit 1)
	@grep -q "## Configuration" README.md || (echo "ERROR: README missing ## Configuration" && exit 1)
	@echo "Checking SPEC.md structure..."
	@grep -q "## 1. Purpose" SPEC.md || (echo "ERROR: SPEC missing ## 1. Purpose" && exit 1)
	@grep -q "## 2. Requirements" SPEC.md || (echo "ERROR: SPEC missing ## 2. Requirements" && exit 1)
	@grep -q "## 3. Detection Rules" SPEC.md || (echo "ERROR: SPEC missing ## 3. Detection Rules" && exit 1)
	@grep -q "## 4. Command-Line Interface" SPEC.md || (echo "ERROR: SPEC missing ## 4. Command-Line Interface" && exit 1)
	@echo "✓ Documentation structure verified"

# Verify CLI matches documented commands
spec-verify: ## Verify documented CLI commands
	@echo "Verifying CLI commands match SPEC.md..."
	@$(PYTHON) -m proseprobe --help | grep -q "check" || (echo "ERROR: 'check' command missing" && exit 1)
	@$(PYTHON) -m proseprobe --help | grep -q "rules" || (echo "ERROR: 'rules' command missing" && exit 1)
	@$(PYTHON) -m proseprobe --help | grep -q "explain" || (echo "ERROR: 'explain' command missing" && exit 1)
	@$(PYTHON) -m proseprobe --help | grep -q "init" || (echo "ERROR: 'init' command missing" && exit 1)
	@$(PYTHON) -m proseprobe --help | grep -q "version" || (echo "ERROR: 'version' command missing" && exit 1)
	@$(PYTHON) -m proseprobe --help | grep -q "baseline" || (echo "ERROR: 'baseline' command missing" && exit 1)
	@echo "Verifying check command options..."
	@$(PYTHON) -m proseprobe check --help | grep -q "\-\-format" || (echo "ERROR: --format option missing" && exit 1)
	@$(PYTHON) -m proseprobe check --help | grep -q "\-\-select" || (echo "ERROR: --select option missing" && exit 1)
	@$(PYTHON) -m proseprobe check --help | grep -q "\-\-ignore" || (echo "ERROR: --ignore option missing" && exit 1)
	@$(PYTHON) -m proseprobe check --help | grep -q "\-\-config" || (echo "ERROR: --config option missing" && exit 1)
	@$(PYTHON) -m proseprobe check --help | grep -q "\-\-severity" || (echo "ERROR: --severity option missing" && exit 1)
	@$(PYTHON) -m proseprobe check --help | grep -q "\-\-profile" || (echo "ERROR: --profile option missing" && exit 1)
	@for profile in academic business general journalism technical-docs; do \
		$(PYTHON) -m proseprobe check --help | grep -q "$$profile" || (echo "ERROR: profile $$profile missing" && exit 1); \
	done
	@echo "Verifying baseline actions..."
	@$(PYTHON) -m proseprobe baseline --help | grep -q "create" || (echo "ERROR: baseline create missing" && exit 1)
	@$(PYTHON) -m proseprobe baseline --help | grep -q "update" || (echo "ERROR: baseline update missing" && exit 1)
	@$(PYTHON) -m proseprobe baseline --help | grep -q "prune" || (echo "ERROR: baseline prune missing" && exit 1)
	@$(PYTHON) -m proseprobe baseline --help | grep -q "summary" || (echo "ERROR: baseline summary missing" && exit 1)
	@echo "✓ CLI matches specification"

# Check test coverage meets threshold (90%)
coverage-analyze: ## Enforce coverage threshold
	@echo "Running coverage analysis..."
	@$(PYTEST) tests/ --cov=src/proseprobe --cov-report=term-missing --cov-report=xml --cov-fail-under=90 -q || \
		(echo "WARNING: Coverage below 90% threshold. Run 'make test-cov' for details." && exit 1)
	@echo "✓ Coverage meets 90% threshold"

# NFR probes (best-effort checks; hardware-dependent)
startup-check: ## Measure startup latency
	@echo "Measuring startup latency..."
	@$(PYTHON) -m benchmarks.startup_probe --limit-ms 100

perf-check: ## Run throughput benchmark
	@echo "Running throughput benchmark..."
	@$(PYTHON) -m benchmarks.bench_rules

memory-check: ## Measure peak memory on a synthetic workspace
	@echo "Running memory probe..."
	@$(PYTHON) -m benchmarks.memory_probe --files 10000 --limit-mb 100

nfr-check: coverage-analyze startup-check perf-check memory-check ## Run NFR probes
