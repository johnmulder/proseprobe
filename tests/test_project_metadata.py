"""Project metadata regression tests."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_uses_slop_lint_names() -> None:
    """CI should exercise this package, not stale predecessor names."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "--cov=src/slop_lint" in workflow
    assert "slop-lint check README.md docs/" in workflow
    assert "humanize" not in workflow
    assert "src/humanize" not in workflow


def test_pre_commit_hook_uses_existing_cli() -> None:
    """Published pre-commit hook metadata should call the implemented CLI."""
    hooks = (ROOT / ".pre-commit-hooks.yaml").read_text()
    assert "id: slop-lint" in hooks
    assert "entry: slop-lint check" in hooks
    assert "humanize" not in hooks
    assert "--fix" not in hooks


def test_spec_matches_current_dependency_policy() -> None:
    """SPEC should document the current zero-runtime-dependency policy."""
    spec = (ROOT / "SPEC.md").read_text()
    assert "No third-party runtime dependencies" in spec
    assert "typer" not in spec
    assert "rich" not in spec
    assert "mistune" not in spec
    assert "regex" not in spec


def test_spec_mentions_existing_test_files() -> None:
    """SPEC test paths should match files that exist in this repository."""
    spec = (ROOT / "SPEC.md").read_text()
    assert "tests/test_cli.py" in spec
    assert "tests/test_linter.py" in spec
    assert "tests/test_property.py" in spec
    assert "tests/test_integration.py" not in spec
    assert "tests/test_properties.py" not in spec


def test_spec_documents_watch_command() -> None:
    """SPEC should include the implemented watch command."""
    spec = (ROOT / "SPEC.md").read_text()
    assert "slop-lint watch [OPTIONS] [PATHS]..." in spec
