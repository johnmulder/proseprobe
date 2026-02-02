.PHONY: install dev test lint typecheck format clean build all doc-audit spec-verify coverage-analyze

# Install production dependencies
install:
	pip install -e .

# Install development dependencies
dev:
	pip install -e ".[dev]"

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
test-cov:
	pytest tests/ -v --cov=src/humanize --cov-report=term-missing --cov-report=html

# Run linter
lint:
	ruff check src/ tests/

# Run type checker
typecheck:
	mypy src/

# Format code
format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

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
	python -m build

# Run humanize on itself (dogfooding)
dogfood:
	python -m humanize check README.md PLAN.md docs/

# Quick check for development
quick:
	ruff check src/ --fix
	pytest tests/ -x -q

# Run benchmarks
benchmark:
	python -m benchmarks.bench_rules
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
	@humanize --help | grep -q "check" || (echo "ERROR: 'check' command missing" && exit 1)
	@humanize --help | grep -q "rules" || (echo "ERROR: 'rules' command missing" && exit 1)
	@humanize --help | grep -q "explain" || (echo "ERROR: 'explain' command missing" && exit 1)
	@humanize --help | grep -q "init" || (echo "ERROR: 'init' command missing" && exit 1)
	@humanize --help | grep -q "version" || (echo "ERROR: 'version' command missing" && exit 1)
	@echo "Verifying check command options..."
	@humanize check --help | grep -q "\-\-fix" || (echo "ERROR: --fix option missing" && exit 1)
	@humanize check --help | grep -q "\-\-format" || (echo "ERROR: --format option missing" && exit 1)
	@humanize check --help | grep -q "\-\-select" || (echo "ERROR: --select option missing" && exit 1)
	@humanize check --help | grep -q "\-\-ignore" || (echo "ERROR: --ignore option missing" && exit 1)
	@humanize check --help | grep -q "\-\-config" || (echo "ERROR: --config option missing" && exit 1)
	@humanize check --help | grep -q "\-\-severity" || (echo "ERROR: --severity option missing" && exit 1)
	@echo "✓ CLI matches specification"

# Check test coverage meets threshold (90%)
coverage-analyze:
	@echo "Running coverage analysis..."
	@pytest tests/ --cov=src/humanize --cov-report=term-missing --cov-fail-under=90 -q || \
		(echo "WARNING: Coverage below 90% threshold. Run 'make test-cov' for details." && exit 1)
	@echo "✓ Coverage meets 90% threshold"
