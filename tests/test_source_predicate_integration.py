"""Verify source-backed predicates through the CLI and effective scan policy."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from proseprobe import __version__
from proseprobe.config import load_config
from proseprobe.core.policy import filter_by_confidence, prepare_scan
from proseprobe.rules.base import Confidence, Issue, Severity
from tests.test_cli import run_cli


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """Keep these authored examples independent of repository config discovery."""
    path = tmp_path / "config.toml"
    path.write_text("")
    return path


def assert_scan(
    config_path: Path,
    source: str,
    selected: str,
    expected: list[Issue],
    *,
    filename: str = "case.md",
    minimum: str = "low",
) -> None:
    """Compare complete CLI records and linter findings to authored expectations."""
    result = run_cli(
        "check",
        "-",
        "--filename",
        filename,
        "--config",
        str(config_path),
        "--select",
        selected,
        "--severity",
        "info",
        "--min-confidence",
        minimum,
        "--format",
        "jsonl",
        stdin=source,
    )
    assert result.exit_code == 0
    assert result.stderr == ""
    records = []
    for issue in expected:
        record = asdict(issue)
        record["severity"] = issue.severity.value
        record["confidence"] = issue.confidence.value
        records.append(
            {
                "schema_version": 1,
                "version": __version__,
                "path": filename,
                **record,
            }
        )
    assert [json.loads(line) for line in result.stdout.splitlines()] == records

    config, linter, _rules = prepare_scan(
        load_config(config_path),
        select=selected,
        severity="info",
        min_confidence=minimum,
    )
    path = Path(filename)
    raw = linter.check_content(source, path)
    filtered = filter_by_confidence({path: raw}, config.min_confidence)
    assert filtered.get(path, []) == expected


@pytest.mark.parametrize(
    ("source", "filename", "expected", "source_span"),
    [
        pytest.param(
            "It must\nbe ensured that Équipe restarts.",
            "case.md",
            Issue(
                "G024",
                "Unclear actor in requirement: 'It must be ensured that'",
                1,
                1,
                2,
                16,
                Severity.INFO,
                Confidence.MEDIUM,
                "Name the actor responsible for the requirement",
            ),
            "It must\nbe ensured that",
            id="unclear-actor",
        ),
        pytest.param(
            "Équipe: You will\nneed to restart.",
            "case.md",
            Issue(
                "G025",
                "Weak instruction phrase: 'You will need to'",
                1,
                9,
                2,
                8,
                Severity.INFO,
                Confidence.MEDIUM,
                "Use a direct imperative",
            ),
            "You will\nneed to",
            id="weak-instruction",
        ),
        pytest.param(
            "Équipe must\nnormally restart.",
            "case.md",
            Issue(
                "G037",
                "Hedged requirement: 'must normally'",
                1,
                8,
                2,
                9,
                Severity.INFO,
                Confidence.MEDIUM,
                "Choose one requirement strength",
            ),
            "must\nnormally",
            id="hedged-requirement",
        ),
        pytest.param(
            "# Équipe must\n# normally restart.",
            "case.py",
            Issue(
                "G037",
                "Hedged requirement: 'must normally'",
                1,
                10,
                2,
                11,
                Severity.INFO,
                Confidence.MEDIUM,
                "Choose one requirement strength",
            ),
            "must\n# normally",
            id="comment-continuation-prefix",
        ),
        pytest.param(
            "> > Équipe must\n> > normally restart.",
            "case.md",
            Issue(
                "G037",
                "Hedged requirement: 'must normally'",
                1,
                12,
                2,
                13,
                Severity.INFO,
                Confidence.MEDIUM,
                "Choose one requirement strength",
            ),
            "must\n> > normally",
            id="nested-quote-continuation-prefix",
        ),
        pytest.param(
            "Équipe handles a large\nnumber of requests.",
            "case.md",
            Issue(
                "V014",
                "Imprecise quantity: 'a large number of'",
                1,
                16,
                2,
                10,
                Severity.INFO,
                Confidence.MEDIUM,
                "Use a measured quantity or cite the source",
            ),
            "a large\nnumber of",
            id="quantity",
        ),
        pytest.param(
            "Équipe is\nthe most\nreliable parser.",
            "case.md",
            Issue(
                "V015",
                "Unbounded superlative: 'the most reliable'",
                2,
                1,
                3,
                9,
                Severity.INFO,
                Confidence.LOW,
                "Name the comparison set and supporting evidence",
            ),
            "the most\nreliable",
            id="superlative-diagnostic-subgroup",
        ),
        pytest.param(
            'def résumé():\n    """Équipe never\n    fails."""\n',
            "case.py",
            Issue(
                "V016",
                "Absolute reliability claim: 'never fails'",
                2,
                15,
                3,
                10,
                Severity.INFO,
                Confidence.MEDIUM,
                "State the tested scope and observed result",
            ),
            "never\n    fails",
            id="docstring-reliability",
        ),
        pytest.param(
            "Équipe is more\nreliable.",
            "case.md",
            Issue(
                "G038",
                "Undefined comparative: 'more reliable'",
                1,
                11,
                2,
                9,
                Severity.INFO,
                Confidence.LOW,
                "Name the comparison target",
            ),
            "more\nreliable",
            id="comparative",
        ),
    ],
)
def test_wrapped_unicode_predicates_keep_complete_records(
    config_path: Path,
    source: str,
    filename: str,
    expected: Issue,
    source_span: str,
) -> None:
    assert_scan(config_path, source, expected.rule_id, [expected], filename=filename)
    assert expected.end_line is not None
    assert expected.end_column is not None
    lines = source.splitlines(keepends=True)
    literal = lines[expected.line - 1][expected.column - 1 :]
    literal += "".join(lines[expected.line : expected.end_line - 1])
    literal += lines[expected.end_line - 1][: expected.end_column - 1]
    assert literal == source_span


@pytest.mark.parametrize(
    ("selected", "source"),
    [
        ("G024", "It must `not` be ensured that clients restart."),
        ("G025", "You `should reconsider` will need to restart."),
        ("G037", "Clients must `not` normally restart."),
        ("G037", "Clients must\n`not`\nnormally restart."),
        ("V014", "A large `unexpected` number of requests failed."),
        ("V015", "Équipe is `not`\nthe most\nreliable parser."),
        ("V016", "The system never `not` fails."),
        ("V016", "The system always `not` succeeds."),
        ("G038", "Atlas is `not` more reliable."),
        ("G038", "Atlas is safer than Boreal."),
        ("G038", "# Comparison target: Boreal parser\n\nAtlas parser is safer."),
        ("G038", "We compared Atlas and Boreal. Atlas is safer."),
        ("V015", "Atlas is best compared with Boreal."),
        ("V016", "The system never fails during 100 tests."),
    ],
)
def test_masked_predicates_and_supported_bounds_remain_clean(
    config_path: Path, selected: str, source: str
) -> None:
    assert_scan(config_path, source, selected, [])


def test_comparison_target_only_bounds_its_attached_claim(config_path: Path) -> None:
    assert_scan(
        config_path,
        "Atlas is safer than Boreal, but Cobalt is slower.",
        "G038",
        [
            Issue(
                "G038",
                "Undefined comparative: 'slower'",
                1,
                43,
                1,
                49,
                Severity.INFO,
                Confidence.LOW,
                "Name the comparison target",
            )
        ],
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "Clients must normally `not` means required.",
            Issue(
                "G037",
                "Hedged requirement: 'must normally'",
                1,
                9,
                1,
                22,
                Severity.INFO,
                Confidence.MEDIUM,
                "Choose one requirement strength",
            ),
        ),
        (
            "The parser is best compared `not` with Boreal.",
            Issue(
                "V015",
                "Unbounded superlative: 'best'",
                1,
                15,
                1,
                19,
                Severity.INFO,
                Confidence.LOW,
                "Name the comparison set and supporting evidence",
            ),
        ),
        (
            "The system never fails in `only` 100 tests.",
            Issue(
                "V016",
                "Absolute reliability claim: 'never fails'",
                1,
                12,
                1,
                23,
                Severity.INFO,
                Confidence.LOW,
                "State the tested scope and observed result",
            ),
        ),
        (
            "Atlas is safer than `Boreal`.",
            Issue(
                "G038",
                "Undefined comparative: 'safer'",
                1,
                10,
                1,
                15,
                Severity.INFO,
                Confidence.LOW,
                "Name the comparison target",
            ),
        ),
    ],
)
def test_masked_evidence_cannot_exempt_literal_claims(
    config_path: Path, source: str, expected: Issue
) -> None:
    assert_scan(config_path, source, expected.rule_id, [expected])


@pytest.mark.parametrize("selected", ["G037", "G038"])
def test_explicit_rule_selection_limits_source_backed_findings(
    config_path: Path, selected: str
) -> None:
    expected = (
        Issue(
            "G037",
            "Hedged requirement: 'must normally'",
            1,
            8,
            2,
            9,
            Severity.INFO,
            Confidence.MEDIUM,
            "Choose one requirement strength",
        )
        if selected == "G037"
        else Issue(
            "G038",
            "Undefined comparative: 'more reliable'",
            4,
            11,
            5,
            9,
            Severity.INFO,
            Confidence.LOW,
            "Name the comparison target",
        )
    )
    assert_scan(
        config_path,
        "Équipe must\nnormally restart.\n\nÉquipe is more\nreliable.",
        selected,
        [expected],
    )


@pytest.mark.parametrize("minimum", ["low", "medium", "high"])
def test_effective_confidence_policy_filters_comparative_separately(
    config_path: Path, minimum: str
) -> None:
    expected = []
    if minimum != "high":
        expected.append(
            Issue(
                "G037",
                "Hedged requirement: 'must normally'",
                1,
                8,
                2,
                9,
                Severity.INFO,
                Confidence.MEDIUM,
                "Choose one requirement strength",
            )
        )
    if minimum == "low":
        expected.append(
            Issue(
                "G038",
                "Undefined comparative: 'more reliable'",
                4,
                11,
                5,
                9,
                Severity.INFO,
                Confidence.LOW,
                "Name the comparison target",
            )
        )
    assert_scan(
        config_path,
        "Équipe must\nnormally restart.\n\nÉquipe is more\nreliable.",
        "G037,G038",
        expected,
        minimum=minimum,
    )


@pytest.mark.parametrize(
    ("filename", "source"),
    [
        (
            "case.md",
            "<!-- proseprobe-ignore-next-line G037 -->\nÉquipe must\nnormally restart.",
        ),
        (
            "case.py",
            "# Équipe must normally restart.  # proseprobe: ignore=G037\n",
        ),
    ],
)
def test_suppression_uses_diagnostic_start(
    config_path: Path, filename: str, source: str
) -> None:
    assert_scan(config_path, source, "G037", [], filename=filename)


def test_python_suppression_does_not_target_next_line(config_path: Path) -> None:
    assert_scan(
        config_path,
        "# proseprobe: ignore=G037\n# Équipe must\n# normally restart.",
        "G037",
        [
            Issue(
                "G037",
                "Hedged requirement: 'must normally'",
                2,
                10,
                3,
                11,
                Severity.INFO,
                Confidence.MEDIUM,
                "Choose one requirement strength",
            )
        ],
        filename="case.py",
    )


def test_superlative_suppression_retains_reported_subgroup_start(
    config_path: Path,
) -> None:
    assert_scan(
        config_path,
        "<!-- proseprobe-ignore-next-line V015 -->\n"
        "Équipe is\nthe most\nreliable parser.",
        "V015",
        [
            Issue(
                "V015",
                "Unbounded superlative: 'the most reliable'",
                3,
                1,
                4,
                9,
                Severity.INFO,
                Confidence.LOW,
                "Name the comparison set and supporting evidence",
            )
        ],
    )


def test_comparative_suppression_leaves_other_claims_visible(config_path: Path) -> None:
    assert_scan(
        config_path,
        "<!-- proseprobe-ignore-next-line G038 -->\n"
        "Atlas is safer.\n\nCobalt is slower.",
        "G038",
        [
            Issue(
                "G038",
                "Undefined comparative: 'slower'",
                4,
                11,
                4,
                17,
                Severity.INFO,
                Confidence.LOW,
                "Name the comparison target",
            )
        ],
    )
