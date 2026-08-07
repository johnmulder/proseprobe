"""Project metadata regression tests."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_uses_slop_lint_names() -> None:
    """CI should exercise this package, not stale predecessor names."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    makefile = (ROOT / "Makefile").read_text()

    assert "make coverage-analyze" in workflow
    assert "make dogfood" in workflow
    assert "--cov=src/slop_lint" in makefile
    assert "slop_lint check README.md docs/" in makefile
    assert "humanize" not in workflow
    assert "src/humanize" not in workflow
    assert "humanize" not in makefile
    assert "src/humanize" not in makefile


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
    assert "make rule-quality" in spec
    assert "tests/test_integration.py" not in spec
    assert "tests/test_properties.py" not in spec


def test_spec_documents_watch_command() -> None:
    """SPEC should include the implemented watch command."""
    spec = (ROOT / "SPEC.md").read_text()
    assert "slop-lint watch [OPTIONS] [PATHS]..." in spec


def test_public_docs_do_not_contain_placeholder_repository_names() -> None:
    """Public docs should not ship template repository placeholders."""
    paths = [
        ROOT / "README.md",
        ROOT / "docs" / "configuration.md",
        ROOT / ".pre-commit-hooks.yaml",
    ]

    for path in paths:
        text = path.read_text()
        assert "yourusername" not in text


def test_changelog_unreleased_counts_match_current_project() -> None:
    """Changelog should not advertise stale rule or test counts."""
    changelog = (ROOT / "CHANGELOG.md").read_text()

    assert "Complete documentation for all 59 rules" in changelog
    assert "all 55 rules" not in changelog
    assert "596 tests passing" not in changelog


def _toml_blocks(path: Path) -> list[str]:
    text = path.read_text()
    return re.findall(r"```toml\n(.*?)\n```", text, flags=re.DOTALL)


def test_documented_toml_examples_parse() -> None:
    """TOML examples in public docs should be valid TOML."""
    docs = [
        ROOT / "README.md",
        ROOT / "docs" / "configuration.md",
        ROOT / "SPEC.md",
    ]

    for path in docs:
        for block in _toml_blocks(path):
            tomllib.loads(block)


def test_dogfood_ci_is_enforced() -> None:
    """Dogfood docs linting should fail CI on new issues."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "make dogfood" in workflow
    assert "continue-on-error: true" not in workflow


def test_ci_enforces_coverage_threshold() -> None:
    """CI should use the same coverage threshold as local NFR checks."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "make coverage-analyze" in workflow
