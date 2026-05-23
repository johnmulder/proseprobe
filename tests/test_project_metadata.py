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
