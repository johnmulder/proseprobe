"""Verify V001 source spans for record identities and literal CLI flags."""

from pathlib import Path

import pytest

from proseprobe.config import Config
from proseprobe.core.linter import Linter
from proseprobe.rules.vocab import AIVocabularyRule

Span = tuple[str, int, int, int | None, int | None]


def _spans(source: str, filename: str) -> list[Span]:
    linter = Linter(Config(select=["V001"]))
    linter.register_rule(AIVocabularyRule())
    issues = linter.check_content(source, Path(filename))
    assert all(issue.rule_id == "V001" for issue in issues)
    return [
        (
            issue.message.split("'")[1],
            issue.line,
            issue.column,
            issue.end_line,
            issue.end_column,
        )
        for issue in issues
    ]


def test_jsonl_diff_cli_comments_preserve_only_the_unqualified_key_prompt() -> None:
    source = (
        "    # --mode keyed requires --key\n"
        "    # --mode multiset with --key: warn and ignore key\n"
        "    # --array-key without --normalize sorted: warn and ignore\n"
    )

    assert _spans(source, "cli.py") == [("key", 2, 51, None, 54)]


@pytest.mark.parametrize(
    ("source", "filename", "expected"),
    [
        (
            "Use duplicate\nkey and a key benefit with robust defaults.\n",
            "guide.md",
            [("key", 2, 11, None, 14), ("robust", 2, 28, None, 34)],
        ),
        (
            "> Use duplicate\n> key and a key benefit with robust defaults.\n",
            "guide.md",
            [("key", 2, 13, None, 16), ("robust", 2, 30, None, 36)],
        ),
        (
            "    # Use duplicate\n    # key and a key benefit with robust defaults.\n",
            "guide.py",
            [("key", 2, 17, None, 20), ("robust", 2, 34, None, 40)],
        ),
        (
            'def read():\n    """Use record\n'
            '    identity key and a key role with robust defaults.\n    """\n',
            "guide.py",
            [("key", 3, 24, None, 27), ("robust", 3, 38, None, 44)],
        ),
        (
            "Use the key\npath and a key insight.\n",
            "guide.md",
            [("key", 2, 12, None, 15)],
        ),
        (
            "# Use the key\n# path and a key insight.\n",
            "guide.py",
            [("key", 2, 14, None, 17)],
        ),
        (
            '"""Use the key\npath and a key insight.\n"""',
            "guide.py",
            [("key", 2, 12, None, 15)],
        ),
    ],
)
def test_wrapped_technical_context_keeps_exact_generic_and_adjacent_spans(
    source: str, filename: str, expected: list[Span]
) -> None:
    assert _spans(source, filename) == expected


@pytest.mark.parametrize(
    ("source", "filename", "expected"),
    [
        (
            "Use --key for identity and --array-key for sorting; a key factor remains.",
            "guide.md",
            [("key", 1, 55, None, 58)],
        ),
        (
            "# Use --key for identity and --array-key for sorting; a key factor remains.",
            "guide.py",
            [("key", 1, 57, None, 60)],
        ),
        (
            '"""Use --key for identity and --array-key for sorting; a key factor remains."""',
            "guide.py",
            [("key", 1, 58, None, 61)],
        ),
        (
            "The record key has a key factor and a key insight.",
            "guide.md",
            [("key", 1, 22, None, 25), ("key", 1, 39, None, 42)],
        ),
        (
            "# The record key has a key factor and a key insight.",
            "guide.py",
            [("key", 1, 24, None, 27), ("key", 1, 41, None, 44)],
        ),
        (
            '"""The record key has a key factor and a key insight."""',
            "guide.py",
            [("key", 1, 25, None, 28), ("key", 1, 42, None, 45)],
        ),
        (
            "İ/O: record key and a key factor.",
            "guide.md",
            [("key", 1, 23, None, 26)],
        ),
        (
            "# İ/O: record key and a key factor.",
            "guide.py",
            [("key", 1, 25, None, 28)],
        ),
        (
            '"""İ/O: record key and a key factor."""',
            "guide.py",
            [("key", 1, 26, None, 29)],
        ),
    ],
)
def test_supported_occurrences_do_not_hide_generic_uses_in_the_same_block(
    source: str, filename: str, expected: list[Span]
) -> None:
    assert _spans(source, filename) == expected


@pytest.mark.parametrize(
    ("source", "filename", "expected"),
    [
        (
            "Use --key-key=key with a key role and robust defaults.",
            "guide.md",
            [
                ("key", 1, 15, None, 18),
                ("key", 1, 26, None, 29),
                ("robust", 1, 39, None, 45),
            ],
        ),
        (
            "# Use --KEY-key=key with a key role and robust defaults.",
            "guide.py",
            [
                ("key", 1, 17, None, 20),
                ("key", 1, 28, None, 31),
                ("robust", 1, 41, None, 47),
            ],
        ),
        (
            "The key\npath to success has a key factor.",
            "guide.md",
            [("key", 1, 5, None, 8), ("key", 2, 23, None, 26)],
        ),
    ],
)
def test_option_names_do_not_exempt_values_and_figurative_paths_stay_reviewable(
    source: str, filename: str, expected: list[Span]
) -> None:
    assert _spans(source, filename) == expected


@pytest.mark.parametrize(
    "noun",
    [
        "**benefits**",
        "*roles*",
        "[insights](insights.md)",
        "~~benefits~~",
        "<em>benefits</em>",
    ],
)
def test_formatted_and_linked_generic_nouns_keep_the_key_prompt(noun: str) -> None:
    source = f"Record key {noun} before the workshop."

    assert _spans(source, "guide.md") == [("key", 1, 8, None, 11)]


@pytest.mark.parametrize(
    "preposition",
    [
        "**to**",
        "*for*",
        "[towards](next.md)",
        "~~for~~",
        "<strong>to</strong>",
    ],
)
def test_formatted_and_linked_path_prepositions_keep_the_key_prompt(
    preposition: str,
) -> None:
    source = f"The key path {preposition} success is documented."

    assert _spans(source, "guide.md") == [("key", 1, 5, None, 8)]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "Record key `hidden` benefits before the workshop.",
            [("key", 1, 8, None, 11)],
        ),
        (
            "The key path `hidden` to success is documented.",
            [("key", 1, 5, None, 8)],
        ),
        ("The record key `id` identifies this row.", []),
    ],
)
def test_code_gaps_do_not_hide_guarded_uses_or_exempt_the_entire_line(
    source: str, expected: list[Span]
) -> None:
    assert _spans(source, "guide.md") == expected


@pytest.mark.parametrize(
    ("source", "filename", "expected"),
    [
        ("Use duplicate\n\nkey as a label.", "guide.md", ("key", 3, 1, None, 4)),
        ("- duplicate\n- key as a label.", "guide.md", ("key", 2, 3, None, 6)),
        (
            "Use duplicate `hidden` key as a label.",
            "guide.md",
            ("key", 1, 24, None, 27),
        ),
        (
            "Use duplicate <code>hidden</code> key as a label.",
            "guide.md",
            ("key", 1, 35, None, 38),
        ),
        (
            "duplicate\n```text\nhidden\n```\nkey as a label.",
            "guide.md",
            ("key", 5, 1, None, 4),
        ),
        (
            "> duplicate\n>\n> key as a label.",
            "guide.md",
            ("key", 3, 3, None, 6),
        ),
        (
            "Use --array-\nkey as a label.",
            "guide.md",
            ("key", 2, 1, None, 4),
        ),
        (
            "Use --array-`hidden`key as a label.",
            "guide.md",
            ("key", 1, 21, None, 24),
        ),
        (
            'label = "duplicate"\n# key as a label.\n',
            "guide.py",
            ("key", 2, 3, None, 6),
        ),
        (
            '# duplicate\nlabel = "ignored"\n# key as a label.\n',
            "guide.py",
            ("key", 3, 3, None, 6),
        ),
        (
            '"""duplicate"""\n\n# key as a label.\n',
            "guide.py",
            ("key", 3, 3, None, 6),
        ),
        ("# duplicate\n\n# key as a label.\n", "guide.py", ("key", 3, 3, None, 6)),
        (
            '"""Use duplicate\n\nkey as a label.\n"""',
            "guide.py",
            ("key", 3, 1, None, 4),
        ),
    ],
)
def test_separate_prose_regions_and_masked_gaps_cannot_supply_key_context(
    source: str, filename: str, expected: Span
) -> None:
    assert _spans(source, filename) == [expected]


@pytest.mark.parametrize(
    ("source", "filename", "expected"),
    [
        (
            "The dictionary key and cache key identify each row.\nA key role remains.",
            "guide.md",
            [("key", 2, 3, None, 6)],
        ),
        (
            "# The dictionary key and cache key identify each row.\n# A key role remains.",
            "guide.py",
            [("key", 2, 5, None, 8)],
        ),
        (
            '"""The dictionary key and cache key identify each row.\nA key role remains."""',
            "guide.py",
            [("key", 2, 3, None, 6)],
        ),
        (
            "The hash table stores each key with its value.\nA key role remains.",
            "guide.md",
            [("key", 2, 3, None, 6)],
        ),
        (
            "# The hash table stores each key with its value.\n# A key role remains.",
            "guide.py",
            [("key", 2, 5, None, 8)],
        ),
        (
            '"""The hash table stores each key with its value.\nA key role remains."""',
            "guide.py",
            [("key", 2, 3, None, 6)],
        ),
    ],
)
def test_existing_typed_key_exceptions_remain_span_specific(
    source: str, filename: str, expected: list[Span]
) -> None:
    assert _spans(source, filename) == expected


def test_ordinary_python_strings_do_not_become_prose_findings() -> None:
    source = (
        'label = "A key benefit with robust defaults."\n'
        "# The record key identifies this row.\n"
    )

    assert _spans(source, "guide.py") == []
