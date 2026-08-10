"""Project metadata regression tests."""

import json
import re
import tomllib
from pathlib import Path

from proseprobe.profiles import PROFILES

ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_uses_proseprobe_names() -> None:
    """CI should exercise this package, not stale predecessor names."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    makefile = (ROOT / "Makefile").read_text()

    assert "make coverage-analyze" in workflow
    assert "make dogfood" in workflow
    assert "--cov=src/proseprobe" in makefile
    assert "proseprobe check README.md docs/" in makefile
    assert "humanize" not in workflow
    assert "src/humanize" not in workflow
    assert "humanize" not in makefile
    assert "src/humanize" not in makefile


def test_pre_commit_hook_uses_existing_cli() -> None:
    """Published pre-commit hook metadata should call the implemented CLI."""
    hooks = (ROOT / ".pre-commit-hooks.yaml").read_text()
    assert "id: proseprobe" in hooks
    assert "entry: proseprobe check" in hooks
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
    assert "proseprobe watch [OPTIONS] [PATHS]..." in spec


def test_spec_documents_baseline_lifecycle() -> None:
    """The specification should cover every implemented baseline action."""
    spec = (ROOT / "SPEC.md").read_text()
    makefile = (ROOT / "Makefile").read_text()

    assert "proseprobe baseline ACTION [OPTIONS] [PATHS]..." in spec
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
    cli = (ROOT / "src" / "proseprobe" / "cli.py").read_text()

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
        assert "<!-- proseprobe-ignore-next-line V001,S010 -->" in text
        assert "# proseprobe: ignore=V001,S010" in text
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


def test_changelog_release_counts_match_current_project() -> None:
    """Changelog should not advertise stale rule or test counts."""
    changelog = (ROOT / "CHANGELOG.md").read_text()

    assert "97 detection rules" in changelog
    assert "96 detection rules" not in changelog
    assert "95 detection rules" not in changelog
    assert "94 detection rules" not in changelog
    assert "93 detection rules" not in changelog
    assert "92 detection rules" not in changelog
    assert "91 detection rules" not in changelog
    assert "90 detection rules" not in changelog
    assert "89 detection rules" not in changelog
    assert "88 detection rules" not in changelog
    assert "87 detection rules" not in changelog
    assert "86 detection rules" not in changelog
    assert "85 detection rules" not in changelog
    assert "84 detection rules" not in changelog
    assert "83 detection rules" not in changelog
    assert "82 detection rules" not in changelog
    assert "81 detection rules" not in changelog
    assert "80 detection rules" not in changelog
    assert "59 rules" not in changelog
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


def test_release_workflow_uses_trusted_publishing() -> None:
    """Release artifacts should be built once and published without API tokens."""
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()

    assert "types: [published]" in workflow
    assert "needs: build" in workflow
    assert workflow.count("name: python-package-distributions") == 3
    assert "environment:\n      name: pypi" in workflow
    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "gh release upload" in workflow
    assert "PYPI_TOKEN" not in workflow
    assert "workflow_dispatch" not in workflow
    assert "push:" not in workflow


def test_agent_skill_uses_portable_minimal_structure() -> None:
    """The portable skill should use only standard Agent Skills metadata."""
    skill_dir = ROOT / "skills" / "proseprobe"
    files = {
        path.relative_to(skill_dir).as_posix()
        for path in skill_dir.rglob("*")
        if path.is_file()
    }

    assert files == {"SKILL.md"}

    skill = (skill_dir / "SKILL.md").read_text()
    opening, raw_frontmatter, body = skill.split("---", 2)
    frontmatter = dict(
        line.split(": ", 1) for line in raw_frontmatter.strip().splitlines()
    )

    assert opening == ""
    assert frontmatter == {
        "name": "proseprobe",
        "description": (
            "Use when an agent generates, edits, or reviews prose in Markdown "
            "or Python docstrings and comments in a project that uses proseprobe."
        ),
        "license": "MIT",
    }
    assert frontmatter["description"].startswith("Use when ")
    assert len(frontmatter["description"]) <= 1024
    assert body.strip()


def test_agent_skill_documents_supported_workflow() -> None:
    """The portable skill should match the supported agent CLI contract."""
    skill = (ROOT / "skills" / "proseprobe" / "SKILL.md").read_text()
    guide = (ROOT / "docs" / "agent-integration.md").read_text()

    literals = (
        "proseprobe check --format jsonl README.md docs/",
        "proseprobe check - --filename docs/draft.md --format jsonl",
        "proseprobe rules --format json",
        "proseprobe explain V001 --format json",
        "pre-commit run proseprobe",
        "| `0` | No warning or error findings; info findings may still be present. |",
        "| `1` | At least one warning or error finding was reported. |",
        "| `2` | Command usage or project configuration is invalid. |",
        "| `3` | An input could not be read. |",
        "Run from the project root so configuration discovery matches normal project use.",
        "Handle high-confidence findings first, then medium, then low.",
        "Rerun the same command after every edit.",
        "ProseProbe reports findings; it does not rewrite files.",
        "Do not add or switch to an `agent` profile.",
    )

    for literal in literals:
        assert literal in guide
        assert literal in skill

    assert "--profile agent" not in skill
    assert "plugin.json" not in skill


def test_codex_plugin_wrapper_is_minimal_and_in_sync() -> None:
    """The Codex adapter should contain only metadata and the portable skill."""
    plugin_root = ROOT / ".agents" / "plugins" / "plugins" / "proseprobe"
    files = {
        path.relative_to(plugin_root).as_posix()
        for path in plugin_root.rglob("*")
        if path.is_file()
    }

    assert files == {
        ".codex-plugin/plugin.json",
        "skills/proseprobe/SKILL.md",
    }
    assert (plugin_root / "skills" / "proseprobe" / "SKILL.md").read_bytes() == (
        ROOT / "skills" / "proseprobe" / "SKILL.md"
    ).read_bytes()


def test_codex_plugin_metadata_matches_project() -> None:
    """The marketplace and plugin manifest should stay aligned with the project."""
    marketplace_root = ROOT / ".agents" / "plugins"
    plugin_root = marketplace_root / "plugins" / "proseprobe"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    manifest = json.loads((plugin_root / ".codex-plugin" / "plugin.json").read_text())
    marketplace = json.loads((marketplace_root / "marketplace.json").read_text())

    manifest_version = manifest.pop("version")
    assert manifest_version.startswith(f"{project['version']}+codex.")
    assert manifest == {
        "name": project["name"],
        "description": project["description"],
        "author": {"name": project["authors"][0]["name"]},
        "homepage": project["urls"]["Homepage"],
        "repository": project["urls"]["Repository"],
        "license": project["license"],
        "skills": "./skills/",
        "interface": {
            "displayName": "ProseProbe",
            "shortDescription": "Lint Markdown and Python prose.",
            "longDescription": (
                "Review Markdown and Python prose with structured ProseProbe "
                "diagnostics."
            ),
            "developerName": project["authors"][0]["name"],
            "category": "Productivity",
            "capabilities": ["Write"],
            "defaultPrompt": ["Review my changed prose with ProseProbe."],
        },
    }
    assert marketplace == {
        "name": "proseprobe",
        "interface": {"displayName": "ProseProbe"},
        "plugins": [
            {
                "name": manifest["name"],
                "source": {
                    "source": "local",
                    "path": "./plugins/proseprobe",
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Productivity",
            }
        ],
    }
    source = marketplace_root / marketplace["plugins"][0]["source"]["path"]
    assert source.resolve() == plugin_root.resolve()


def test_agent_integration_guide_documents_supported_contract() -> None:
    """The agent guide should stay aligned with supported CLI behavior."""
    guide_path = ROOT / "docs" / "agent-integration.md"

    assert guide_path.is_file()
    guide = guide_path.read_text()

    for command in (
        "proseprobe check --format jsonl README.md docs/",
        "proseprobe check - --filename docs/draft.md --format jsonl",
        "proseprobe rules --format json",
        "proseprobe explain V001 --format json",
        "pre-commit run proseprobe",
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
        "ProseProbe reports findings; it does not rewrite files.",
        "Do not add or switch to an `agent` profile.",
    ):
        assert statement in guide

    assert "--profile agent" not in guide


def test_readme_links_agent_integration_guide() -> None:
    """The public documentation index should expose the agent workflow."""
    readme = (ROOT / "README.md").read_text()

    assert "[Agent integration guide](docs/agent-integration.md)" in readme


def test_readme_documents_portable_agent_skill() -> None:
    """The README should expose the skill artifact and installation boundary."""
    readme = (ROOT / "README.md").read_text()

    for statement in (
        "[Portable Agent Skill](skills/proseprobe/SKILL.md)",
        "The `skills/proseprobe/` directory is the copyable distribution unit.",
        "Install the `proseprobe` executable separately before using the skill.",
    ):
        assert statement in readme


def test_readme_documents_codex_plugin_marketplace() -> None:
    """Public docs should explain the Codex install and packaging boundary."""
    readme = (ROOT / "README.md").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()

    for statement in (
        "[Codex plugin marketplace](.agents/plugins/marketplace.json)",
        'codex plugin marketplace add "$PWD/.agents/plugins"',
        "codex plugin add proseprobe@proseprobe",
        "The Codex wrapper is not included in the Python wheel.",
        "Start a new Codex thread after installation so it loads the skill.",
    ):
        assert statement in readme

    assert "repo-local Codex marketplace plugin" in changelog


def test_ci_enforces_coverage_threshold() -> None:
    """CI should use the same coverage threshold as local NFR checks."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "make coverage-analyze" in workflow
