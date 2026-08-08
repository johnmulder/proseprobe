"""Project metadata regression tests."""

import re
import tomllib
from pathlib import Path

from slop_lint.profiles import PROFILES

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


def test_spec_documents_baseline_lifecycle() -> None:
    """The specification should cover every implemented baseline action."""
    spec = (ROOT / "SPEC.md").read_text()
    makefile = (ROOT / "Makefile").read_text()

    assert "slop-lint baseline ACTION [OPTIONS] [PATHS]..." in spec
    for action in ("create", "update", "prune", "summary"):
        assert f"`{action}`" in spec
        assert f'grep -q "{action}"' in makefile


def test_public_docs_match_profile_catalog() -> None:
    """Public docs and release checks should name every built-in profile."""
    documents = [
        (ROOT / "README.md").read_text(),
        (ROOT / "SPEC.md").read_text(),
        (ROOT / "docs" / "configuration.md").read_text(),
    ]
    makefile = (ROOT / "Makefile").read_text()
    cli = (ROOT / "src" / "slop_lint" / "cli.py").read_text()

    for profile in PROFILES:
        assert all(profile in document for document in documents)
        assert profile in makefile
    assert "choices=tuple(PROFILES)" in cli
    assert '# profile = "technical-docs"' in cli


def test_docs_explain_python_prose_rule_scope() -> None:
    """Public docs should describe shared rules and C001's narrow ownership."""
    readme = (ROOT / "README.md").read_text()
    spec = (ROOT / "SPEC.md").read_text()
    rules = (ROOT / "docs" / "rules.md").read_text()

    for text in (readme, spec, rules):
        assert "source-mapped Python docstrings and comments" in text

    assert "src/main.py:45:8: V002" in readme
    assert "src/main.py:45:8: V002" in spec
    assert "C001: Docstring-Only Vocabulary" in rules
    assert "not covered by `V001`" in rules


def test_docs_explain_inline_suppression_contract() -> None:
    """Public docs should preserve both line-scoped directive forms."""
    paths = [ROOT / "README.md", ROOT / "SPEC.md", ROOT / "docs/configuration.md"]

    for path in paths:
        text = path.read_text()
        assert "<!-- slop-lint-ignore-next-line V001,S010 -->" in text
        assert "# slop-lint: ignore=V001,S010" in text
        assert "following physical line" in text
        assert "same physical line" in text


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


def test_agent_integration_guide_documents_supported_contract() -> None:
    """The agent guide should stay aligned with supported CLI behavior."""
    guide_path = ROOT / "docs" / "agent-integration.md"

    assert guide_path.is_file()
    guide = guide_path.read_text()

    for command in (
        "slop-lint check --format jsonl README.md docs/",
        "slop-lint check - --filename docs/draft.md --format jsonl",
        "slop-lint rules --format json",
        "slop-lint explain V001 --format json",
        "pre-commit run slop-lint",
    ):
        assert command in guide

    for row in (
        "| `0` | No warning or error findings; info findings may still be present. |",
        "| `1` | At least one warning or error finding was reported. |",
        "| `2` | Command usage or project configuration is invalid. |",
        "| `3` | An input could not be read. |",
    ):
        assert row in guide

    for statement in (
        "Run from the project root so configuration discovery matches normal project use.",
        "Handle high-confidence findings first, then medium, then low.",
        "Rerun the same command after every edit.",
        "slop-lint reports findings; it does not rewrite files.",
        "Do not add or switch to an `agent` profile.",
    ):
        assert statement in guide

    assert "--profile agent" not in guide


def test_readme_links_agent_integration_guide() -> None:
    """The public documentation index should expose the agent workflow."""
    readme = (ROOT / "README.md").read_text()

    assert "[Agent integration guide](docs/agent-integration.md)" in readme


def test_ci_enforces_coverage_threshold() -> None:
    """CI should use the same coverage threshold as local NFR checks."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "make coverage-analyze" in workflow
