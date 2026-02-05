.PHONY: install dev test lint typecheck format clean build all doc-audit spec-verify coverage-analyze

VENV ?= .venv
VENV_BIN = $(VENV)/bin

PYTHON = $(VENV_BIN)/python
PIP = $(VENV_BIN)/pip
PYTEST = $(VENV_BIN)/pytest
RUFF = $(VENV_BIN)/ruff
MYPY = $(VENV_BIN)/mypy

ifeq ($(wildcard $(PYTHON)),)
PYTHON = python
PIP = pip
PYTEST = pytest
RUFF = ruff
MYPY = mypy
endif

# Install production dependencies
install:
	$(PIP) install -e .

# Install development dependencies
dev:
	$(PIP) install -e ".[dev]"

# Run tests
test:
	$(PYTEST) tests/ -v

# Run tests with coverage
test-cov:
	$(PYTEST) tests/ -v --cov=src/slop_lint --cov-report=term-missing --cov-report=html

# Run linter
lint:
	$(RUFF) check src/ tests/

# Run type checker
typecheck:
	$(MYPY) src/

# Format code
format:
	$(RUFF) format src/ tests/
	$(RUFF) check --fix src/ tests/

# Run all checks
check: lint typecheck test

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

# Build package
build: clean
	$(PYTHON) -m build

# Run slop-lint on itself (dogfooding)
dogfood:
	$(PYTHON) -m slop_lint check README.md docs/ --baseline .slop-lint-baseline.json

# Quick check for development
quick:
	$(RUFF) check src/ --fix
	$(PYTEST) tests/ -x -q

# Run benchmarks
benchmark:
	$(PYTHON) -m benchmarks.bench_rules
# Full validation (lint + type-check + test)
all: lint typecheck test

# Verify README/SPEC structure matches expected sections
doc-audit:
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
spec-verify:
	@echo "Verifying CLI commands match SPEC.md..."
	@$(PYTHON) -m slop_lint --help | grep -q "check" || (echo "ERROR: 'check' command missing" && exit 1)
	@$(PYTHON) -m slop_lint --help | grep -q "rules" || (echo "ERROR: 'rules' command missing" && exit 1)
	@$(PYTHON) -m slop_lint --help | grep -q "explain" || (echo "ERROR: 'explain' command missing" && exit 1)
	@$(PYTHON) -m slop_lint --help | grep -q "init" || (echo "ERROR: 'init' command missing" && exit 1)
	@$(PYTHON) -m slop_lint --help | grep -q "version" || (echo "ERROR: 'version' command missing" && exit 1)
	@echo "Verifying check command options..."
	@$(PYTHON) -m slop_lint check --help | grep -q "\-\-fix" || (echo "ERROR: --fix option missing" && exit 1)
	@$(PYTHON) -m slop_lint check --help | grep -q "\-\-format" || (echo "ERROR: --format option missing" && exit 1)
	@$(PYTHON) -m slop_lint check --help | grep -q "\-\-select" || (echo "ERROR: --select option missing" && exit 1)
	@$(PYTHON) -m slop_lint check --help | grep -q "\-\-ignore" || (echo "ERROR: --ignore option missing" && exit 1)
	@$(PYTHON) -m slop_lint check --help | grep -q "\-\-config" || (echo "ERROR: --config option missing" && exit 1)
	@$(PYTHON) -m slop_lint check --help | grep -q "\-\-severity" || (echo "ERROR: --severity option missing" && exit 1)
	@echo "✓ CLI matches specification"

# Check test coverage meets threshold (90%)
coverage-analyze:
	@echo "Running coverage analysis..."
	@$(PYTEST) tests/ --cov=src/slop_lint --cov-report=term-missing --cov-fail-under=90 -q || \
		(echo "WARNING: Coverage below 90% threshold. Run 'make test-cov' for details." && exit 1)
	@echo "✓ Coverage meets 90% threshold"
