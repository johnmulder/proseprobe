import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from benchmarks.corpora import CorpusError, Source
from benchmarks.review_readings import build_reading


def _source(tmp_path: Path, raw: bytes, *, format: str = "markdown") -> Source:
    path = "sample.py" if format == "python" else "sample.md"
    (tmp_path / path).write_bytes(raw)
    return Source(
        "authored:sample",
        "authored",
        "authored:sample-pair",
        path,
        hashlib.sha256(raw).hexdigest(),
        "development",
        format,
        {},
    )


def _reading(source: Source, tmp_path: Path, **kwargs: object) -> dict:
    arguments = {
        "start_line": 1,
        "end_line": 1,
        "rule_ids": ["G039"],
        "instructions": "Read this source without detector predictions.",
        "questions": "List every repeated-word issue, or say none.",
    }
    arguments.update(kwargs)
    return build_reading(source, tmp_path, **arguments)


@pytest.mark.parametrize("format", ["markdown", "python"])
def test_reading_binds_exact_original_and_selected_full_lines(
    tmp_path: Path, format: str
) -> None:
    source = _source(
        tmp_path, b"Outside.\n  Read read this.  \nOutside again.\n", format=format
    )
    reading = _reading(source, tmp_path, start_line=2, end_line=2)

    assert reading["source_id"] == source.identity
    assert reading["sha256"] == source.sha256
    assert reading["source_group"] == source.source_group
    assert reading["pair_group"] == source.pair_group
    assert reading["rule_ids"] == ["G039"]
    assert reading["region"] == {
        "line": 2,
        "column": 1,
        "end_line": 2,
        "end_column": 20,
    }
    assert [row["text"] for row in reading["rows"]] == ["  Read read this.  "]
    assert "Outside" not in reading["rendered_text"]
    assert (
        reading["rendered_sha256"]
        == hashlib.sha256(reading["rendered_text"].encode("utf-8")).hexdigest()
    )
    assert json.loads(json.dumps(reading)) == reading
    assert "reviewed_rules" not in reading
    assert "expected" not in reading


@pytest.mark.parametrize(
    ("split", "format"),
    [
        ("holdout", "markdown"),
        ("holdout", "python"),
        ("development", "codesearchnet"),
        ("development", "m2"),
        ("development", "jfleg"),
        ("development", "asset"),
    ],
)
def test_ineligible_sources_are_rejected_before_reading_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, split: str, format: str
) -> None:
    source = _source(tmp_path, b"Never open this.")
    source = replace(source, split=split, format=format, path="absent.md")

    def fail_read(*_args: object) -> bytes:
        raise AssertionError("Ineligible source bytes were opened")

    monkeypatch.setattr("benchmarks.review_readings._checked_bytes", fail_read)
    with pytest.raises(CorpusError, match=r"development|raw Markdown or Python"):
        _reading(source, tmp_path)


def test_changed_original_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path, b"Original.")
    (tmp_path / source.path).write_bytes(b"Changed.")
    with pytest.raises(CorpusError, match="checksum mismatch"):
        _reading(source, tmp_path)


def test_source_path_escape_is_rejected(tmp_path: Path) -> None:
    source = replace(_source(tmp_path, b"Original."), path="../escape.md")
    with pytest.raises(CorpusError, match="escapes"):
        _reading(source, tmp_path)


def test_unicode_continuations_keep_whitespace_and_physical_line_endings(
    tmp_path: Path,
) -> None:
    selected = "😀 café  \t" + "x" * 160 + "  \r\n\r\nEnd.\t \n"
    source = _source(tmp_path, ("Before.\n" + selected + "After.").encode("utf-8"))
    reading = _reading(source, tmp_path, start_line=2, end_line=4)

    rebuilt = "".join(
        row["text"] + row["source_line_ending"] for row in reading["rows"]
    )
    assert rebuilt == selected
    assert len(reading["rows"]) > 3
    assert reading["rows"][0]["column"] == 1
    assert reading["rows"][0]["text"].startswith("😀 café  \t")
    assert reading["rows"][0]["source_line_ending"] == ""
    assert reading["rows"][-1]["source_line_ending"] == "\n"
    physical = selected.splitlines()
    displayed = reading["rendered_text"].splitlines()
    for row in reading["rows"]:
        assert (
            row["text"]
            == physical[row["line"] - 2][row["column"] - 1 : row["end_column"] - 1]
        )
        assert displayed[row["reading_line"] - 1].endswith("| " + row["text"])
    assert max(map(len, displayed)) <= 80
    assert len(displayed) <= 80


def test_reading_encloses_source_backticks_with_a_longer_fence(tmp_path: Path) -> None:
    source = _source(tmp_path, b"```python\nExample.\n````\n")
    reading = _reading(source, tmp_path, end_line=3)
    lines = reading["rendered_text"].splitlines()
    assert "`````text" in lines
    assert lines.count("`````") == 1
    assert "".join(
        row["text"] + row["source_line_ending"] for row in reading["rows"]
    ) == ("```python\nExample.\n````\n")


def test_sentence_continuations_prefer_word_boundaries_without_losing_separators(
    tmp_path: Path,
) -> None:
    sentence = "Review every sentence and preserve every original character. "
    text = sentence * 4 + "Keep\tthis tab and both trailing spaces.  \r\n"
    source = _source(tmp_path, text.encode("utf-8"))
    reading = _reading(source, tmp_path)
    rows = reading["rows"]

    assert len(rows) > 1
    assert all(row["text"].endswith((" ", "\t")) for row in rows[:-1])
    assert "".join(row["text"] + row["source_line_ending"] for row in rows) == text
    assert reading["region"]["end_column"] == len(text[:-2]) + 1
    assert reading["sha256"] == source.sha256
    assert max(map(len, reading["rendered_text"].splitlines())) <= 80


@pytest.mark.parametrize("field", ["instructions", "questions"])
def test_wide_caller_text_is_refused_without_truncation(
    tmp_path: Path, field: str
) -> None:
    source = _source(tmp_path, b"Read this.")
    with pytest.raises(CorpusError, match="80 characters"):
        _reading(source, tmp_path, **{field: "x" * 81})


@pytest.mark.parametrize("field", ["instructions", "questions"])
def test_all_caller_text_counts_toward_line_budget(tmp_path: Path, field: str) -> None:
    source = _source(tmp_path, b"Read this.")
    with pytest.raises(CorpusError, match="80 lines"):
        _reading(source, tmp_path, **{field: "\n".join(["Read."] * 80)})


def test_large_source_is_refused_without_truncation(tmp_path: Path) -> None:
    source = _source(tmp_path, ("x" * 8000).encode())
    with pytest.raises(CorpusError, match="80 lines"):
        _reading(source, tmp_path)


@pytest.mark.parametrize(("start", "end"), [(0, 1), (2, 1), (1, 3), (True, 1)])
def test_invalid_full_line_regions_are_refused(
    tmp_path: Path, start: int, end: int
) -> None:
    source = _source(tmp_path, b"First.\nLast.")
    with pytest.raises(CorpusError, match="source line region"):
        _reading(source, tmp_path, start_line=start, end_line=end)


def test_empty_source_cannot_supply_a_line_region(tmp_path: Path) -> None:
    source = _source(tmp_path, b"")
    with pytest.raises(CorpusError, match="source line region"):
        _reading(source, tmp_path)


def test_non_utf8_source_is_refused(tmp_path: Path) -> None:
    source = _source(tmp_path, b"\xff")
    with pytest.raises(CorpusError, match="UTF-8"):
        _reading(source, tmp_path)


@pytest.mark.parametrize("rules", [[], ["G039", "G039"], ["G"], ["made-up"]])
def test_invalid_rule_declarations_are_refused(
    tmp_path: Path, rules: list[str]
) -> None:
    source = _source(tmp_path, b"Read this.")
    with pytest.raises(CorpusError, match="rule IDs"):
        _reading(source, tmp_path, rule_ids=rules)
