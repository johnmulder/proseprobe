"""Tests for generated rule documentation."""

import re
from collections import Counter
from pathlib import Path

import pytest

from proseprobe._rule_docs import (
    MarkerError,
    _replace_generated_block,
    render_category_table,
    render_rule_inventory,
    synchronize_rule_docs,
)
from proseprobe.rules import get_all_rules, get_rule_metadata
from proseprobe.rules.base import Confidence

ROOT = Path(__file__).resolve().parents[1]


def _documented_rule_examples() -> list[tuple[str, str, str, str]]:
    reference = (ROOT / "docs" / "rules.md").read_text()
    section_pattern = re.compile(
        r"^### (?P<rule_id>[A-Z]\d{3}): .+?\n(?P<body>.*?)"
        r"(?=^### [A-Z]\d{3}:|\Z)",
        re.M | re.S,
    )
    example_pattern = re.compile(
        r"\*\*Example \((?P<label>[^)]+)\):\*\*\s*\n"
        r"(?P<fence>`{3,}|~{3,})(?P<language>[^\n]*)\n"
        r"(?P<content>.*?)(?:\n(?P=fence)[ \t]*(?=\n|\Z))",
        re.S,
    )
    pairs: list[tuple[str, str, str, str]] = []
    for section in section_pattern.finditer(reference):
        examples = list(example_pattern.finditer(section.group("body")))
        assert len(examples) == 2, section.group("rule_id")
        first, second = examples
        assert (first.group("label"), second.group("label")) in {
            ("bad", "good"),
            ("flagged", "not flagged"),
            ("unbounded", "bounded"),
            ("unsupported", "supported"),
        }
        language = first.group("language").strip()
        assert language == second.group("language").strip()
        pairs.append(
            (
                section.group("rule_id"),
                language,
                first.group("content"),
                second.group("content"),
            )
        )
    return pairs


def _seed_documents(root: Path) -> None:
    (root / "docs").mkdir()
    (root / "README.md").write_text(
        "before\n<!-- rule-docs:categories:start -->\nstale\n"
        "<!-- rule-docs:categories:end -->\nafter\n"
    )
    (root / "SPEC.md").write_text(
        "before\n<!-- rule-docs:categories:start -->\nstale\n"
        "<!-- rule-docs:categories:end -->\nafter\n"
    )
    (root / "docs" / "rules.md").write_text(
        "before\n<!-- rule-docs:inventory:start -->\nstale\n"
        "<!-- rule-docs:inventory:end -->\nafter\n"
    )


def test_category_table_is_derived_from_registry() -> None:
    rendered = render_category_table()

    assert "| `V` | Vocabulary | 16 |" in rendered
    assert "| `S` | Structure | 25 |" in rendered
    assert "| `T` | Style | 14 |" in rendered
    assert "| `M` | Markup | 10 |" in rendered
    assert "| `G` | Grammar | 25 |" in rendered
    assert "| `C` | Code | 7 |" in rendered
    assert "| **Total** | | **97** | |" in rendered


def test_rule_inventory_contains_canonical_metadata() -> None:
    rendered = render_rule_inventory()
    rule_rows = [line for line in rendered.splitlines() if line.startswith("| `")]

    assert len(rule_rows) == 97
    assert rule_rows[0].startswith("| `V001`")
    assert rule_rows[-1].startswith("| `M010`")
    assert any(
        "`S001`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        and "`thresholds.rule_of_three`" in row
        for row in rule_rows
    )
    assert any("`M001`" in row and "low" in row for row in rule_rows)
    assert any(
        "`C006`" in row and "info" in row and "low" in row and "python / raw" in row
        for row in rule_rows
    )
    assert any(
        "`C007`" in row and "info" in row and "medium" in row and "python / raw" in row
        for row in rule_rows
    )
    assert any(
        "`C008`" in row and "info" in row and "low" in row and "python / raw" in row
        for row in rule_rows
    )
    assert any(
        "`M009`" in row
        and "info" in row
        and "high" in row
        and "markdown / prose" in row
        for row in rule_rows
    )
    assert any(
        "`V009`" in row
        and "info" in row
        and "high" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`V010`" in row
        and "info" in row
        and "high" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`V011`" in row
        and "info" in row
        and "high" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`V013`" in row
        and "info" in row
        and "high" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`V014`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`V015`" in row
        and "info" in row
        and "low" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`V016`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`V017`" in row
        and "info" in row
        and "low" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`S022`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        and "`thresholds.wall_of_text_sentences`" in row
        for row in rule_rows
    )
    assert any(
        "`S025`" in row
        and "warning" in row
        and "high" in row
        and "markdown / raw" in row
        for row in rule_rows
    )
    assert any(
        "`S028`" in row
        and "info" in row
        and "medium" in row
        and "markdown / raw" in row
        for row in rule_rows
    )
    assert any(
        "`S029`" in row and "info" in row and "low" in row and "markdown / raw" in row
        for row in rule_rows
    )
    assert any(
        "`T013`" in row
        and "info" in row
        and "low" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G015`" in row
        and "info" in row
        and "medium" in row
        and "markdown / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G016`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G029`" in row
        and "info" in row
        and "high" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G017`" in row
        and "info" in row
        and "high" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G019`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G022`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G024`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G025`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G031`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G037`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`G038`" in row
        and "info" in row
        and "low" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`T010`" in row
        and "info" in row
        and "high" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`T012`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`T014`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`T015`" in row
        and "info" in row
        and "high" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )
    assert any(
        "`T016`" in row
        and "info" in row
        and "medium" in row
        and "markdown, python / prose" in row
        for row in rule_rows
    )


def test_handwritten_rule_sections_match_registry_exactly() -> None:
    reference = (ROOT / "docs" / "rules.md").read_text()
    headings = re.findall(r"^### ([A-Z]\d{3}): (.+)$", reference, re.M)
    expected = [(item.id, item.name) for item in get_rule_metadata()]

    assert Counter(headings) == Counter(expected)
    assert len(headings) == len(expected)


@pytest.mark.parametrize(
    ("rule_id", "language", "bad_example", "good_example"),
    _documented_rule_examples(),
    ids=lambda value: value if re.fullmatch(r"[A-Z]\d{3}", value) else None,
)
def test_documented_examples_match_rule_behavior(
    rule_id: str,
    language: str,
    bad_example: str,
    good_example: str,
) -> None:
    """Each rule's examples should remain executable documentation."""
    rule = next(rule for rule in get_all_rules() if rule.id == rule_id)
    filename = "example.py" if language == "python" else "example.md"

    bad_issues = rule.check(bad_example, filename)
    good_issues = rule.check(good_example, filename)

    assert bad_issues
    if rule_id == "V014":
        assert good_issues
        assert all(issue.confidence is Confidence.LOW for issue in good_issues)
    else:
        assert good_issues == []


def test_write_is_deterministic_and_check_detects_no_changes(tmp_path: Path) -> None:
    _seed_documents(tmp_path)

    changed = synchronize_rule_docs(tmp_path, write=True)
    first = {
        path: (tmp_path / path).read_bytes()
        for path in ("README.md", "SPEC.md", "docs/rules.md")
    }
    changed_again = synchronize_rule_docs(tmp_path, write=True)

    assert changed == ("README.md", "SPEC.md", "docs/rules.md")
    assert changed_again == ()
    assert synchronize_rule_docs(tmp_path, write=False) == ()
    assert first == {path: (tmp_path / path).read_bytes() for path in first}


def test_check_reports_stale_files_without_writing(tmp_path: Path) -> None:
    _seed_documents(tmp_path)
    before = (tmp_path / "README.md").read_bytes()

    stale = synchronize_rule_docs(tmp_path, write=False)

    assert stale == ("README.md", "SPEC.md", "docs/rules.md")
    assert (tmp_path / "README.md").read_bytes() == before


@pytest.mark.parametrize(
    "text",
    [
        "no markers",
        "<!-- rule-docs:sample:start -->\nonly start",
        (
            "<!-- rule-docs:sample:start -->\n"
            "<!-- rule-docs:sample:start -->\n"
            "<!-- rule-docs:sample:end -->"
        ),
        "<!-- rule-docs:sample:end -->\n<!-- rule-docs:sample:start -->",
        (
            "<!-- rule-docs:sample:start -->\n"
            "<!-- rule-docs:nested:start -->\n"
            "<!-- rule-docs:nested:end -->\n"
            "<!-- rule-docs:sample:end -->"
        ),
    ],
)
def test_generated_block_rejects_invalid_markers(text: str) -> None:
    with pytest.raises(MarkerError):
        _replace_generated_block(text, "sample", "generated")
