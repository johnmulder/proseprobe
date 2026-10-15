import hashlib
import json
import re
import sys
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import pytest
from benchmarks.corpora import CorpusError, Source
from benchmarks.review_context import build_contextual_readings


def _source(tmp_path: Path, raw: bytes, *, format: str = "python") -> Source:
    path = "sample.py" if format == "python" else "sample.md"
    (tmp_path / path).write_bytes(raw)
    return Source(
        "authored:context",
        "authored",
        "authored:context-pair",
        path,
        hashlib.sha256(raw).hexdigest(),
        "development",
        format,
        {},
    )


def _bundle(source: Source, tmp_path: Path, **kwargs: object) -> dict:
    arguments = {
        "start_line": 1,
        "end_line": 1,
        "rule_ids": ["C009"],
        "instructions": "Read every linked source page.",
        "questions": "Describe supported issues, or say none or unresolved.",
        "reading_id": "sample",
        "link_directory": Path("/tmp/p32d5b"),
    }
    arguments.update(kwargs)
    return build_contextual_readings(source, tmp_path, **arguments)


def _region(text: str, start: int, end: int) -> dict[str, int]:
    return {
        "line": start,
        "column": 1,
        "end_line": end,
        "end_column": len(text.splitlines()[end - 1]) + 1,
    }


def _rows(bundle: dict, role: str) -> list[dict]:
    return [
        row
        for reading in bundle["readings"]
        if reading["role"].startswith(role)
        for row in reading["rows"]
    ]


def _reconstruct(rows: list[dict]) -> str:
    return "".join(row["text"] + row["source_line_ending"] for row in rows)


def _assert_pages(bundle: dict, source: Source, text: str) -> None:
    pages = bundle["readings"]
    physical = text.splitlines(keepends=True)
    assert pages
    for field in ("context_sha256", "bundle_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", bundle[field])
    for index, page in enumerate(pages, start=1):
        rendered = page["rendered_text"]
        displayed = rendered.splitlines()
        path = Path(page["path"])
        assert page["index"] == index
        assert page["total"] == len(pages)
        assert path.is_absolute()
        assert path.suffix == ".txt"
        assert str(path) in rendered
        if index > 1:
            assert pages[index - 2]["path"] in rendered
        if index < len(pages):
            assert pages[index]["path"] in rendered
        assert bundle["context_sha256"] in rendered
        assert all(rule in rendered for rule in bundle["context"]["rule_ids"])
        assert "Read every linked source page." in rendered
        assert "Describe supported issues, or say none or unresolved." in rendered
        assert len(displayed) <= 80
        assert max(map(len, displayed)) <= 80
        assert (
            page["rendered_sha256"]
            == hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        )
        for row in page["rows"]:
            body = physical[row["line"] - 1].rstrip("\r\n")
            assert row["source_id"] == source.identity
            assert row["sha256"] == source.sha256
            assert row["end_line"] == row["line"]
            assert row["text"] == body[row["column"] - 1 : row["end_column"] - 1]
            assert displayed[row["reading_line"] - 1].endswith("| " + row["text"])


@pytest.mark.parametrize(
    ("text", "start", "end", "owners"),
    [
        (
            "class Client:\n"
            "    @(\n"
            "        wrapper\n"
            "    )\n"
            "    async def send(\n"
            "        self,\n"
            "        café,\n"
            "        /,\n"
            "        *,\n"
            "        retry=True,\n"
            "    ) -> None:\n"
            '        """Review this docstring."""\n',
            12,
            12,
            [("Client", "class", 1, 1), ("send", "function", 2, 11)],
        ),
        (
            "def send(value):\n"
            '    """Outer documentation."""\n'
            "    def send(other):\n"
            '        """Review this docstring."""\n'
            "        return other\n"
            "    return value\n",
            4,
            4,
            [("send", "function", 1, 1), ("send", "function", 3, 3)],
        ),
        (
            "def make(factory=lambda x: x) -> lambda x: x: "
            '"""Review this docstring."""\n',
            1,
            1,
            [("make", "function", 1, 1)],
        ),
        (
            '@wrapper\ndef send(value):\n    """Review this docstring."""\n',
            1,
            1,
            [("send", "function", 1, 2)],
        ),
        (
            "def first(value):\n"
            '    """First documentation."""\n'
            "\n"
            "def second(value):\n"
            '    """Second documentation."""\n',
            2,
            5,
            [("first", "function", 1, 1), ("second", "function", 4, 4)],
        ),
    ],
    ids=[
        "async-class",
        "nested-repeat",
        "inline-lambda",
        "decorator-focus",
        "siblings",
    ],
)
def test_python_owner_selection_preserves_complete_lexical_headers(
    tmp_path: Path,
    text: str,
    start: int,
    end: int,
    owners: list[tuple[str, str, int, int]],
) -> None:
    raw = text.encode("utf-8")
    source = _source(tmp_path, raw)
    bundle = _bundle(source, tmp_path, start_line=start, end_line=end)
    context = bundle["context"]

    assert context["source_id"] == source.identity
    assert context["sha256"] == source.sha256
    assert context["split"] == source.split
    assert context["format"] == source.format
    assert context["region"] == _region(text, start, end)
    assert context["python_scope"] == "lexical-owners"
    assert [
        (owner["name"], owner["node_type"], owner["header_region"])
        for owner in context["python_owners"]
    ] == [
        (name, node_type, _region(text, first, last))
        for name, node_type, first, last in owners
    ]
    physical = text.splitlines(keepends=True)
    assert _reconstruct(_rows(bundle, "focus")) == "".join(physical[start - 1 : end])
    assert _reconstruct(_rows(bundle, "python-owner")) == "".join(
        "".join(physical[first - 1 : last]) for _, _, first, last in owners
    )
    assert (tmp_path / source.path).read_bytes() == raw
    assert json.loads(json.dumps(bundle)) == bundle
    assert "reviewed_rules" not in context
    assert "expected" not in context
    assert "has_dynamic_decorators" not in json.dumps(context)
    _assert_pages(bundle, source, text)


@pytest.mark.skipif(sys.version_info < (3, 12), reason="Python type parameter syntax")
def test_python_type_parameters_are_raw_header_context(tmp_path: Path) -> None:
    text = 'def send[T](value: T, /) -> T:\n    """Return the value."""\n'
    source = _source(tmp_path, text.encode())
    bundle = _bundle(source, tmp_path, start_line=2, end_line=2)

    assert bundle["context"]["python_owners"][0]["header_region"] == _region(text, 1, 1)
    assert (
        _reconstruct(_rows(bundle, "python-owner")) == text.splitlines(keepends=True)[0]
    )


def test_python_source_is_parsed_without_importing_or_executing_it(
    tmp_path: Path,
) -> None:
    text = (
        "from nonexistent_review_module import wrapper\n"
        'raise AssertionError("Reviewed source executed")\n'
        "@wrapper()\n"
        "def send(value):\n"
        '    """Review this docstring."""\n'
    )
    source = _source(tmp_path, text.encode())
    bundle = _bundle(source, tmp_path, start_line=5, end_line=5)

    assert _reconstruct(_rows(bundle, "python-owner")) == (
        "@wrapper()\ndef send(value):\n"
    )


@pytest.mark.parametrize(
    ("split", "format"),
    [("holdout", "python"), ("holdout", "markdown"), ("development", "codesearchnet")],
)
def test_context_source_metadata_is_gated_before_any_bytes_are_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, split: str, format: str
) -> None:
    source = replace(
        _source(tmp_path, b"Never open this."),
        split=split,
        format=format,
        path="absent.py",
    )

    def fail_read(_path: Path) -> bytes:
        raise AssertionError("Ineligible source bytes were opened")

    monkeypatch.setattr(Path, "read_bytes", fail_read)
    with pytest.raises(CorpusError, match=r"development|raw Markdown or Python"):
        _bundle(source, tmp_path)


def test_context_rejects_stale_source_bytes(tmp_path: Path) -> None:
    source = _source(tmp_path, b'def send():\n    """Original."""\n')
    (tmp_path / source.path).write_bytes(b'def send():\n    """Changed."""\n')

    with pytest.raises(CorpusError, match="checksum mismatch"):
        _bundle(source, tmp_path)


@pytest.mark.parametrize(
    "text",
    [
        "def broken(\n",
        'def send():\r    """Review this docstring."""\r',
        'def send():\n    """Review\u2028this docstring."""\n',
        'def send():\n    """Review\u0085this docstring."""\n',
        'def send():\n\f    """Review this docstring."""\n',
    ],
)
def test_unsupported_python_syntax_or_line_mapping_is_explicitly_rejected(
    tmp_path: Path, text: str
) -> None:
    source = _source(tmp_path, text.encode())

    with pytest.raises(
        CorpusError,
        match=r"Python|python|syntax|parse|unsupported|separator|newline|form",
    ):
        _bundle(source, tmp_path)


def test_module_scope_has_an_explicit_empty_owner_inventory(tmp_path: Path) -> None:
    text = '"""Review this module documentation."""\n'
    source = _source(tmp_path, text.encode())
    bundle = _bundle(source, tmp_path)

    assert bundle["context"]["python_scope"] == "module"
    assert bundle["context"]["python_owners"] == []
    assert _rows(bundle, "python-owner") == []
    assert _reconstruct(_rows(bundle, "focus")) == text
    _assert_pages(bundle, source, text)


def test_long_physical_line_paginates_without_losing_unicode_or_crlf(
    tmp_path: Path,
) -> None:
    header = "def send(café, /, **options):\r\n"
    selected = '    """😀 café ' + "Review every word. " * 500 + '  """\r\n'
    text = header + selected
    source = _source(tmp_path, text.encode())
    bundle = _bundle(source, tmp_path, start_line=2, end_line=2)
    focus_pages = [
        page for page in bundle["readings"] if page["role"].startswith("focus")
    ]
    focus_rows = _rows(bundle, "focus")

    assert len(focus_pages) > 1
    assert _reconstruct(focus_rows) == selected
    assert _reconstruct(_rows(bundle, "python-owner")) == header
    assert focus_rows[0]["column"] == 1
    assert all(row["source_line_ending"] == "" for row in focus_rows[:-1])
    assert focus_rows[-1]["source_line_ending"] == "\r\n"
    assert all(
        before["end_column"] == after["column"]
        for before, after in pairwise(focus_rows)
    )
    _assert_pages(bundle, source, text)


def test_long_signature_header_is_paginated_in_full(tmp_path: Path) -> None:
    header = 'def send(value="' + "café " * 1800 + '"):\r\n'
    selected = '    """Review this docstring."""\r\n'
    text = header + selected
    source = _source(tmp_path, text.encode())
    bundle = _bundle(source, tmp_path, start_line=2, end_line=2)
    owner_pages = [
        page for page in bundle["readings"] if page["role"].startswith("python-owner")
    ]

    assert len(owner_pages) > 1
    assert _reconstruct(_rows(bundle, "python-owner")) == header
    assert _reconstruct(_rows(bundle, "focus")) == selected
    _assert_pages(bundle, source, text)


@pytest.mark.parametrize(
    "arguments",
    [
        {"questions": "x" * 81},
        {"instructions": "\n".join(["Read every source page."] * 80)},
        {"link_directory": Path("/tmp") / ("x" * 100)},
    ],
)
def test_unrenderable_mandatory_page_content_is_refused_without_omission(
    tmp_path: Path, arguments: dict
) -> None:
    source = _source(tmp_path, b'"""Module documentation."""\n')

    with pytest.raises(CorpusError, match=r"80|budget|fit|header|link"):
        _bundle(source, tmp_path, **arguments)


def test_links_and_hashes_are_deterministic_and_bind_the_rendered_bundle(
    tmp_path: Path,
) -> None:
    text = 'def send(value):\n    """Review this docstring."""\n'
    source = _source(tmp_path, text.encode())
    first = _bundle(source, tmp_path, start_line=2, end_line=2)
    second = _bundle(source, tmp_path, start_line=2, end_line=2)
    changed = _bundle(
        source,
        tmp_path,
        start_line=2,
        end_line=2,
        questions="Describe every issue and its source span.",
    )

    assert first == second
    assert first["bundle_sha256"] != changed["bundle_sha256"]
    assert [page["rendered_sha256"] for page in first["readings"]] != [
        page["rendered_sha256"] for page in changed["readings"]
    ]
    assert len({page["path"] for page in first["readings"]}) == len(first["readings"])
    _assert_pages(first, source, text)
    changed_source = _source(tmp_path, text.replace("value", "input").encode())
    changed_context = _bundle(changed_source, tmp_path, start_line=2, end_line=2)

    assert first["context_sha256"] != changed_context["context_sha256"]
    assert first["bundle_sha256"] != changed_context["bundle_sha256"]


def test_every_linked_page_repeats_canonical_rule_scope(tmp_path: Path) -> None:
    text = 'def send(value):\n    """Review this docstring."""\n'
    source = _source(tmp_path, text.encode())
    rules = ["C007", "C009", "C010"]
    bundle = _bundle(source, tmp_path, start_line=2, end_line=2, rule_ids=rules)

    assert len(bundle["readings"]) > 1
    for page in bundle["readings"]:
        assert all(rule in page["rendered_text"] for rule in rules)
