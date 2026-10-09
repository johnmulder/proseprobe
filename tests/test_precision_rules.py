"""Integration contracts for the experimental precision rules."""

import json
from pathlib import Path

import pytest
from benchmarks.quality_scoring import Annotations, ExpectedFinding
from benchmarks.rule_quality import eligible_annotations, prepare_evaluation_scan

from proseprobe.config import Config, PerFileIgnore
from proseprobe.core.baseline import Baseline
from proseprobe.core.policy import prepare_scan
from proseprobe.profiles import EXPERIMENTAL_RULES, PROFILES
from proseprobe.rules import get_all_rules, get_rule_metadata_by_id
from proseprobe.rules.base import Severity
from tests.test_cli import run_cli

CASES = [
    ("G039", "case.md", "Read the the configuration.", "the", 10),
    (
        "C009",
        "case.py",
        'def read(path):\n    """:param stale: Path."""\n',
        "stale",
        15,
    ),
    ("M011", "case.md", "Read [installation](#install).", "#install", 21),
]


@pytest.mark.parametrize(("rule_id", "filename", "content", "token", "column"), CASES)
@pytest.mark.parametrize("output_format", ["jsonl", "sarif"])
def test_precision_rule_cli_spans(
    tmp_path: Path,
    rule_id: str,
    filename: str,
    content: str,
    token: str,
    column: int,
    output_format: str,
) -> None:
    path = tmp_path / filename
    path.write_text(content)
    config = tmp_path / "config.toml"
    config.write_text('markdown_anchor_style = "github"\n')
    result = run_cli(
        "check",
        str(path),
        "--config",
        str(config),
        "--select",
        rule_id,
        "--severity",
        "info",
        "--min-confidence",
        "high",
        "--format",
        output_format,
    )
    assert result.exit_code == 0, result.stderr
    line = 2 if rule_id == "C009" else 1
    if output_format == "jsonl":
        [record] = [json.loads(item) for item in result.stdout.splitlines()]
        assert record["rule_id"] == rule_id
        assert (record["line"], record["column"], record["end_column"]) == (
            line,
            column,
            column + len(token),
        )
    else:
        [record] = json.loads(result.stdout)["runs"][0]["results"]
        assert record["ruleId"] == rule_id
        region = record["locations"][0]["physicalLocation"]["region"]
        assert (region["startLine"], region["startColumn"], region["endColumn"]) == (
            line,
            column,
            column + len(token),
        )


@pytest.mark.parametrize(("rule_id", "filename", "content", "token", "column"), CASES)
def test_precision_rule_selection_ignore_override_and_baseline(
    tmp_path: Path,
    rule_id: str,
    filename: str,
    content: str,
    token: str,
    column: int,
) -> None:
    path = tmp_path / filename
    config = Config(select=[rule_id], severity="info", markdown_anchor_style="github")
    _, linter, _ = prepare_scan(config)
    [issue] = linter.check_content(content, path)
    assert issue.rule_id == rule_id
    assert issue.column == column
    baseline = Baseline(tmp_path / "baseline.json")
    baseline.add_issue(issue, path, content, tmp_path)
    assert baseline.entries[0].match == token
    baseline.save()
    loaded = Baseline(baseline.baseline_path)
    assert loaded.load()
    assert not loaded.is_new_issue(issue, path, content, tmp_path)
    _, ignored, _ = prepare_scan(
        Config(
            select=[rule_id],
            ignore=[rule_id],
            severity="info",
            markdown_anchor_style="github",
        )
    )
    assert ignored.check_content(content, path) == []
    _, per_file, _ = prepare_scan(
        Config(
            select=[rule_id],
            severity="info",
            markdown_anchor_style="github",
            per_file_ignores=[PerFileIgnore(filename, [rule_id])],
        )
    )
    assert per_file.check_content(content, path) == []
    _, overridden, _ = prepare_scan(
        Config(
            select=[rule_id],
            severity="error",
            markdown_anchor_style="github",
            severity_overrides={rule_id: "error"},
        )
    )
    assert overridden.check_content(content, path)[0].severity is Severity.ERROR


def test_precision_rules_are_experimental_with_canonical_metadata() -> None:
    registered = {rule.id for rule in get_all_rules()}
    for rule_id in ("G039", "C009", "M011"):
        assert rule_id in registered
        assert rule_id in EXPERIMENTAL_RULES
        assert all(rule_id not in profile.rules for profile in PROFILES.values())
        metadata = get_rule_metadata_by_id(rule_id)
        assert metadata is not None
        assert metadata.default_severity is Severity.INFO
        assert metadata.default_confidence.value == "high"


def test_fragment_renderer_off_cannot_be_enabled_by_severity_override() -> None:
    _, linter, rules = prepare_scan(
        Config(select=["M011"], severity="info", severity_overrides={"M011": "error"})
    )
    assert "M011" not in {rule.id for rule in rules}
    assert linter.check_content("[Read](#missing)", Path("case.md")) == []


def test_all_rule_evaluation_explicitly_enables_anchor_policy() -> None:
    config, linter, rules = prepare_evaluation_scan()
    assert config.markdown_anchor_style == "github"
    assert "M011" in {rule.id for rule in rules}
    assert any(
        issue.rule_id == "M011"
        for issue in linter.check_content("[Read](#missing)", Path("case.md"))
    )
    production, _, rules = prepare_evaluation_scan(mode="production", severity="info")
    assert production.markdown_anchor_style == "off"
    assert "M011" not in {rule.id for rule in rules}


def test_disabled_renderer_labels_are_ineligible_before_scoring(tmp_path: Path) -> None:
    path = tmp_path / "case.md"
    path.write_text("[Read](#missing)")
    annotations = Annotations((path,), (ExpectedFinding("case.md", "M011", 1, 8),), ())
    _, linter, rules = prepare_evaluation_scan(mode="production", severity="info")
    eligible = eligible_annotations(annotations, tmp_path, linter, rules)
    assert eligible.expected == ()
    assert eligible.scopes is not None
    assert all("M011" not in scope.rules for scope in eligible.scopes)


def test_show_config_displays_renderer_policy(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('markdown_anchor_style = "github"\n')
    result = run_cli("check", ".", "--config", str(config), "--show-config")
    assert result.exit_code == 0
    assert "Markdown anchor style: github" in result.stdout


@pytest.mark.parametrize(
    ("rule_id", "filename", "content"),
    [
        (
            "G039",
            "case.md",
            "<!-- proseprobe-ignore-next-line G039 -->\nRead the the configuration.",
        ),
        (
            "C009",
            "case.py",
            'def read(path):\n    """:param stale: Path."""  # proseprobe: ignore=C009\n',
        ),
        (
            "M011",
            "case.md",
            "<!-- proseprobe-ignore-next-line M011 -->\n[Read](#missing)",
        ),
    ],
)
def test_precision_rule_inline_suppression(
    rule_id: str, filename: str, content: str
) -> None:
    _, linter, _ = prepare_scan(
        Config(select=[rule_id], severity="info", markdown_anchor_style="github")
    )
    assert linter.check_content(content, Path(filename)) == []
