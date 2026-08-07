"""Regression tests for the project Makefile."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"


def _makefile_text() -> str:
    return MAKEFILE.read_text()


def _target_names() -> set[str]:
    text = _makefile_text()
    targets: set[str] = set()
    for line in text.splitlines():
        if line.startswith(("\t", ".")):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):(?:\s|$)", line)
        if match:
            targets.add(match.group(1))
    return targets


def _phony_names() -> set[str]:
    text = _makefile_text()
    names: set[str] = set()
    for line in text.splitlines():
        if line.startswith(".PHONY:"):
            names.update(line.split(":", 1)[1].split())
    return names


def test_default_goal_is_help() -> None:
    """Bare `make` should be discoverable, not install dependencies."""
    assert ".DEFAULT_GOAL := help" in _makefile_text()


def test_all_public_targets_are_phony() -> None:
    """Command targets should not conflict with files of the same name."""
    public_targets = _target_names() - {"help"}
    phony = _phony_names()

    missing = sorted(public_targets - phony)

    assert missing == []


def test_help_target_lists_common_workflows() -> None:
    """`make help` should show the commands new contributors need."""
    result = subprocess.run(
        ["make", "help"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "Usage: make <target>" in result.stdout
    for target in [
        "dev",
        "test",
        "check",
        "clean",
        "build",
        "dogfood",
        "benchmark",
        "rule-quality",
    ]:
        assert target in result.stdout


def test_clean_dry_run_removes_known_generated_artifacts() -> None:
    """`make clean` should cover generated artifacts without touching the venv."""
    result = subprocess.run(
        ["make", "-n", "clean"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    clean_script = result.stdout
    for artifact in [
        "build/",
        "dist/",
        "htmlcov/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        ".hypothesis/",
        "coverage.xml",
        ".coverage.*",
        "__pycache__",
        "*.pyc",
        "*.egg-info",
    ]:
        assert artifact in clean_script
    assert ".venv" not in clean_script


def test_readme_development_section_prefers_make_targets() -> None:
    """README development commands should point users at the Makefile."""
    readme = (ROOT / "README.md").read_text()

    for command in [
        "make dev",
        "make test",
        "make typecheck",
        "make lint",
        "make check",
    ]:
        assert command in readme


def test_makefile_does_not_reference_missing_trope_document() -> None:
    """Make targets should not depend on files absent from the repository."""
    makefile = _makefile_text()
    assert "low_quality_journalism_tropes.md" not in makefile


def test_ci_uses_make_targets_for_local_parity() -> None:
    """CI should reuse local Makefile targets for routine checks."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    for command in [
        "make lint",
        "make typecheck",
        "make coverage-analyze",
        "make dogfood",
        "make rule-quality",
        "make build",
    ]:
        assert command in workflow


def test_memory_check_runs_probe_instead_of_skipping() -> None:
    """The memory NFR target should execute a real probe."""
    makefile = _makefile_text()

    assert "benchmarks.memory_probe" in makefile
    assert "Memory probe is not implemented yet" not in makefile


def test_nfr_targets_show_gate_policy() -> None:
    """NFR targets should make release gates explicit."""
    makefile = _makefile_text()

    assert "benchmarks.startup_probe" in makefile
    assert "benchmarks.memory_probe" in makefile
    assert "--limit-ms 100" in makefile
    assert "--limit-mb 100" in makefile
    assert "coverage-analyze" in makefile


def test_coverage_analyze_emits_xml_for_ci_upload() -> None:
    """Coverage threshold target should still produce Codecov XML."""
    makefile = _makefile_text()
    match = re.search(r"^coverage-analyze:.*?(?=^\S|\Z)", makefile, re.S | re.M)

    assert match is not None
    coverage_target = match.group(0)
    assert "--cov-fail-under=90" in coverage_target
    assert "--cov-report=xml" in coverage_target
