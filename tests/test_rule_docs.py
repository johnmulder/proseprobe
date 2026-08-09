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
from proseprobe.rules import get_rule_metadata

ROOT = Path(__file__).resolve().parents[1]


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

    assert "| `V` | Vocabulary | 14 |" in rendered
    assert "| `S` | Structure | 24 |" in rendered
    assert "| `T` | Style | 13 |" in rendered
    assert "| `M` | Markup | 10 |" in rendered
    assert "| `G` | Grammar | 18 |" in rendered
    assert "| **Total** | | **83** | |" in rendered


def test_rule_inventory_contains_canonical_metadata() -> None:
    rendered = render_rule_inventory()
    rule_rows = [line for line in rendered.splitlines() if line.startswith("| `")]

    assert len(rule_rows) == 83
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
        "`V016`" in row
        and "info" in row
        and "medium" in row
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
        "`G015`" in row
        and "info" in row
        and "medium" in row
        and "markdown / prose" in row
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
        "`G024`" in row
        and "info" in row
        and "medium" in row
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
