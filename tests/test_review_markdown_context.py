import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest
from benchmarks.corpora import CorpusError, Source
from benchmarks.native_link_context import (
    NativeSource,
    NativeTarget,
    VerifiedNativeContext,
)
from benchmarks.native_reference_context import (
    NativeReference,
    VerifiedReferenceContext,
)
from benchmarks.review_context import build_contextual_readings


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source(tmp_path: Path, raw: bytes) -> Source:
    (tmp_path / "source.md").write_bytes(raw)
    return Source(
        "synthetic/docs:docs/start.md",
        "synthetic/docs",
        "synthetic/docs:docs/start.md",
        "source.md",
        _sha(raw),
        "development",
        "markdown",
        {},
    )


def _build(source: Source, tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    arguments = {
        "start_line": 1,
        "end_line": 1,
        "rule_ids": ["M011"],
        "instructions": "Read the source and its complete structural context.",
        "questions": "Identify unresolved same-document fragments, or say none.",
        "reading_id": "md",
        "link_directory": Path("/tmp/p32d5b"),
        "markdown_anchor_style": "github",
    }
    arguments.update(kwargs)
    return build_contextual_readings(source, tmp_path, **arguments)


def _document(bundle: dict[str, Any], role: str, source_id: str) -> dict[str, Any]:
    matches = [
        document
        for document in bundle["context"]["markdown_documents"]
        if document["role"] == role and document["source_id"] == source_id
    ]
    assert len(matches) == 1
    return matches[0]


def _full_rows(bundle: dict[str, Any], role: str, source_id: str) -> list[dict]:
    return [
        row
        for reading in bundle["readings"]
        if reading["role"] == role
        for row in reading["rows"]
        if row["source_id"] == source_id
    ]


def _assert_exact_rows(
    bundle: dict[str, Any], role: str, source_id: str, raw: bytes
) -> None:
    rows = _full_rows(bundle, role, source_id)
    rebuilt = "".join(row["text"] + row["source_line_ending"] for row in rows)
    assert rebuilt.encode("utf-8") == raw
    physical = raw.decode("utf-8").splitlines()
    for row in rows:
        assert row["sha256"] == _sha(raw)
        assert row["end_line"] == row["line"]
        assert (
            row["text"]
            == physical[row["line"] - 1][row["column"] - 1 : row["end_column"] - 1]
        )


def _reference(raw: bytes, destination: str, path: str) -> NativeReference:
    for line, body in enumerate(raw.decode("utf-8").splitlines(), 1):
        if destination in body:
            column = body.index(destination) + 1
            return NativeReference(
                destination,
                line,
                column,
                column + len(destination),
                path,
                destination.partition("#")[2],
            )
    raise AssertionError("synthetic destination must occur in source")


def _trusted_native(
    source: Source,
    raw: bytes,
    targets: tuple[NativeTarget, ...],
    references: tuple[NativeReference, ...],
    *,
    renderer: str = "github",
    extra_sources: tuple[NativeSource, ...] = (),
) -> VerifiedReferenceContext:
    # The API accepts validator-produced immutable contexts. These synthetic
    # objects stand in for that trusted boundary; integration covers its proof.
    native = VerifiedNativeContext(
        "1" * 64,
        source.source_group,
        "2" * 40,
        "3" * 64,
        (NativeSource(source.identity, "docs/start.md", raw), *extra_sources),
        targets,
    )
    return VerifiedReferenceContext(
        native,
        renderer,
        ((source.identity, references),),
        ((source.identity, ()),),
    )


def test_markdown_inventory_uses_whole_source_and_original_heading_coordinates(
    tmp_path: Path,
) -> None:
    raw = b"# Before\nFocus body.\n## After\n"
    source = _source(tmp_path, raw)
    bundle = _build(source, tmp_path, start_line=2, end_line=2)
    document = _document(bundle, "source", source.identity)

    assert document["sha256"] == source.sha256
    assert document["status"] == "supported"
    assert [
        (item["title"], item["line"], item["column"], item["end_column"])
        for item in document["headings"]
    ] == [("Before", 1, 3, 9), ("After", 3, 4, 9)]
    assert document["anchors"] == ["after", "before"]
    _assert_exact_rows(bundle, "markdown-source", source.identity, raw)
    assert "reviewed_rules" not in bundle
    assert "expected" not in bundle


def test_markdown_inventory_preserves_order_and_production_duplicate_slugs(
    tmp_path: Path,
) -> None:
    raw = b"# Foo\n# Foo\n# Foo-1\n# Foo\n"
    source = _source(tmp_path, raw)
    document = _document(_build(source, tmp_path), "source", source.identity)

    assert [item["title"] for item in document["headings"]] == [
        "Foo",
        "Foo",
        "Foo-1",
        "Foo",
    ]
    assert [item["line"] for item in document["headings"]] == [1, 2, 3, 4]
    assert document["anchors"] == ["foo", "foo-1", "foo-1-1", "foo-2"]


def test_setext_and_blockquoted_headings_keep_exact_source_rows(
    tmp_path: Path,
) -> None:
    raw = b"Title\n=====\n> ## Quoted\n"
    source = _source(tmp_path, raw)
    bundle = _build(source, tmp_path)
    document = _document(bundle, "source", source.identity)

    assert [
        (item["title"], item["line"], item["column"], item["end_column"])
        for item in document["headings"]
    ] == [("Title", 1, 1, 6), ("Quoted", 3, 6, 12)]
    assert document["anchors"] == ["quoted", "title"]
    _assert_exact_rows(bundle, "markdown-source", source.identity, raw)


def test_explicit_anchor_inventory_uses_production_masks_and_complete_membership(
    tmp_path: Path,
) -> None:
    raw = (
        b"---\nkey: '<a id=\"front\"></a>'\n---\n"
        b"# Real\n\n"
        b'```html\n# Fenced\n<a id="fenced"></a>\n```\n'
        b'<!-- <a id="comment"></a> -->\n'
        b'`<a id="inline"></a>`\n'
        b'![<a id="image"></a>](asset.png)\n'
        b'[text](<a id="destination">)\n'
        b'\\<a id="escaped"></a> <a id="manual"></a>\n'
        b'<a name="legacy"></a>\n'
        b'<a id="manual"></a>\n'
    )
    source = _source(tmp_path, raw)
    bundle = _build(source, tmp_path)
    document = _document(bundle, "source", source.identity)

    assert [item["title"] for item in document["headings"]] == ["Real"]
    assert document["anchors"] == ["legacy", "manual", "real"]
    _assert_exact_rows(bundle, "markdown-source", source.identity, raw)


@pytest.mark.parametrize("generated", [b"{{ heading }}\n", b"{% include x %}\n"])
def test_generated_markdown_refuses_complete_static_inventory(
    tmp_path: Path, generated: bytes
) -> None:
    source = _source(tmp_path, b"# Static\n" + generated)
    with pytest.raises(CorpusError, match=r"generated|unsupported"):
        _build(source, tmp_path)


@pytest.mark.parametrize("rule", ["M011", "M012"])
@pytest.mark.parametrize("style", [None, "off"])
def test_fragment_readings_require_explicit_github_renderer(
    tmp_path: Path, rule: str, style: str | None
) -> None:
    source = _source(tmp_path, b"# Source\n")
    with pytest.raises(CorpusError, match=r"renderer|github|anchor"):
        _build(source, tmp_path, rule_ids=[rule], markdown_anchor_style=style)


def test_local_target_reading_requires_verified_native_context(tmp_path: Path) -> None:
    source = _source(tmp_path, b"[Target](guide.md#target)\n")
    with pytest.raises(CorpusError, match=r"native|context"):
        _build(source, tmp_path, rule_ids=["M012"])


def test_native_reading_uses_all_bound_target_bytes_and_pinned_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = b"[Target](guide.md#target)\n[Empty](empty.md)\n[Absent](absent.md)\n"
    target = b'# Target\n<a id="manual"></a>\n'
    source = _source(tmp_path, raw)
    references = (
        _reference(raw, "guide.md#target", "docs/guide.md"),
        _reference(raw, "empty.md", "docs/empty.md"),
        _reference(raw, "absent.md", "docs/absent.md"),
    )
    verified = _trusted_native(
        source,
        raw,
        (
            NativeTarget("docs/guide.md", target),
            NativeTarget("docs/empty.md", b""),
            NativeTarget("docs/absent.md", None),
        ),
        references,
    )
    real_read_bytes = Path.read_bytes
    real_read_text = Path.read_text

    def source_only_bytes(path: Path) -> bytes:
        assert path == tmp_path / source.path, "target bytes must remain immutable"
        return real_read_bytes(path)

    def no_target_text(path: Path, *args: Any, **kwargs: Any) -> str:
        assert path == tmp_path / source.path, "target text must not be reopened"
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", source_only_bytes)
    monkeypatch.setattr(Path, "read_text", no_target_text)
    bundle = _build(source, tmp_path, rule_ids=["M012"], native_context=verified)

    native = bundle["context"]["native"]
    assert native["manifest_sha256"] == verified.native.manifest_sha256
    assert native["revision"] == verified.native.revision
    assert native["inventory_sha256"] == verified.native.inventory_sha256
    targets = {item["native_path"]: item for item in native["targets"]}
    assert set(targets) == {"docs/guide.md", "docs/empty.md", "docs/absent.md"}
    assert targets["docs/guide.md"]["status"] == "present"
    assert targets["docs/guide.md"]["sha256"] == _sha(target)
    assert targets["docs/empty.md"]["status"] == "present"
    assert targets["docs/empty.md"]["sha256"] == _sha(b"")
    assert targets["docs/absent.md"]["status"] == "absent"
    assert "sha256" not in targets["docs/absent.md"]
    assert native["references"] == {
        source.identity: [asdict(reference) for reference in references]
    }
    assert _document(bundle, "target", "docs/guide.md")["anchors"] == [
        "manual",
        "target",
    ]
    assert _document(bundle, "target", "docs/empty.md")["headings"] == []
    assert not any(
        item["source_id"] == "docs/absent.md"
        for item in bundle["context"]["markdown_documents"]
    )
    _assert_exact_rows(bundle, "markdown-target", "docs/guide.md", target)


def test_native_targets_may_be_other_verified_sources(tmp_path: Path) -> None:
    raw = b"[Target](guide.md#target)\n"
    target = b"# Target\n"
    source = _source(tmp_path, raw)
    verified = _trusted_native(
        source,
        raw,
        (),
        (_reference(raw, "guide.md#target", "docs/guide.md"),),
        extra_sources=(NativeSource("other-source", "docs/guide.md", target),),
    )
    bundle = _build(source, tmp_path, rule_ids=["M012"], native_context=verified)
    assert _document(bundle, "target", "docs/guide.md")["sha256"] == _sha(target)
    _assert_exact_rows(bundle, "markdown-target", "docs/guide.md", target)


def test_native_reference_target_must_be_bound_even_outside_focus(
    tmp_path: Path,
) -> None:
    raw = b"Focus body.\n[Target](guide.md#target)\n"
    source = _source(tmp_path, raw)
    verified = _trusted_native(
        source,
        raw,
        (),
        (_reference(raw, "guide.md#target", "docs/guide.md"),),
    )
    with pytest.raises(CorpusError, match=r"target|bound"):
        _build(source, tmp_path, rule_ids=["M012"], native_context=verified)


@pytest.mark.parametrize("mismatch", ["identity", "group", "bytes", "renderer"])
def test_native_context_must_match_selected_source_and_renderer(
    tmp_path: Path, mismatch: str
) -> None:
    raw = b"# Source\n"
    source = _source(tmp_path, raw)
    verified = _trusted_native(source, raw, (), ())
    if mismatch == "identity":
        native_source = replace(verified.native.sources[0], source_id="other")
        verified = replace(
            verified, native=replace(verified.native, sources=(native_source,))
        )
    elif mismatch == "group":
        verified = replace(
            verified, native=replace(verified.native, source_group="other-group")
        )
    elif mismatch == "bytes":
        native_source = replace(verified.native.sources[0], raw=b"# Changed\n")
        verified = replace(
            verified, native=replace(verified.native, sources=(native_source,))
        )
    else:
        verified = replace(verified, renderer="off")
    with pytest.raises(
        CorpusError, match=r"source|identity|group|bytes|renderer|anchor"
    ):
        _build(source, tmp_path, rule_ids=["M012"], native_context=verified)


def test_conflicting_native_path_bytes_are_refused(tmp_path: Path) -> None:
    raw = b"[Target](guide.md#target)\n"
    source = _source(tmp_path, raw)
    verified = _trusted_native(
        source,
        raw,
        (NativeTarget("docs/guide.md", b"# Different\n"),),
        (_reference(raw, "guide.md#target", "docs/guide.md"),),
        extra_sources=(NativeSource("other-source", "docs/guide.md", b"# Target\n"),),
    )
    with pytest.raises(CorpusError, match=r"conflict|different|duplicate"):
        _build(source, tmp_path, rule_ids=["M012"], native_context=verified)


def test_generated_fragment_target_is_not_an_empty_inventory(tmp_path: Path) -> None:
    raw = b"[Target](guide.md#target)\n"
    source = _source(tmp_path, raw)
    verified = _trusted_native(
        source,
        raw,
        (NativeTarget("docs/guide.md", b"{{ generated_heading }}\n"),),
        (_reference(raw, "guide.md#target", "docs/guide.md"),),
    )
    with pytest.raises(CorpusError, match=r"generated|unsupported"):
        _build(source, tmp_path, rule_ids=["M012"], native_context=verified)


def test_unicode_crlf_markdown_rows_bind_exact_original_bytes(tmp_path: Path) -> None:
    raw = (
        "# Café 😀\r\n"
        "Read this source outside its focused line.\r\n"
        '<a id="mañana"></a>\r\n' + "Long " * 30 + "tail.\t \r\n"
    ).encode("utf-8")
    source = _source(tmp_path, raw)
    bundle = _build(source, tmp_path, start_line=2, end_line=2)
    document = _document(bundle, "source", source.identity)

    assert document["sha256"] == _sha(raw)
    assert document["anchors"] == ["café-", "mañana"]
    _assert_exact_rows(bundle, "markdown-source", source.identity, raw)


def test_large_markdown_inventory_paginates_without_losing_source_rows(
    tmp_path: Path,
) -> None:
    raw = "".join(f"## Heading {index:03d}\n" for index in range(240)).encode()
    source = _source(tmp_path, raw)
    bundle = _build(source, tmp_path)
    document = _document(bundle, "source", source.identity)

    assert len(document["headings"]) == 240
    assert [item["line"] for item in document["headings"]] == list(range(1, 241))
    assert document["anchors"] == [f"heading-{index:03d}" for index in range(240)]
    pages = [page for page in bundle["readings"] if page["role"] == "markdown-source"]
    assert len(pages) > 1
    for page in bundle["readings"]:
        lines = page["rendered_text"].splitlines()
        assert len(lines) <= 80
        assert max(map(len, lines), default=0) <= 80
        assert page["rendered_sha256"] == _sha(page["rendered_text"].encode())
        for row in page["rows"]:
            assert lines[row["reading_line"] - 1].endswith("| " + row["text"])
    _assert_exact_rows(bundle, "markdown-source", source.identity, raw)
    assert json.loads(json.dumps(bundle)) == bundle


def test_context_hash_is_deterministic_and_binds_hidden_markdown_context(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path, b"Focus body.\n# Before\n")
    first = _build(source, tmp_path)
    assert _build(source, tmp_path)["context_sha256"] == first["context_sha256"]
    changed = _source(tmp_path, b"Focus body.\n# After\n")
    second = _build(changed, tmp_path)
    assert second["context_sha256"] != first["context_sha256"]


@pytest.mark.parametrize("change", ["target-bytes", "absence", "inventory", "revision"])
def test_context_hash_binds_native_bytes_and_absence_proof(
    tmp_path: Path, change: str
) -> None:
    raw = b"[Target](guide.md)\n"
    source = _source(tmp_path, raw)
    verified = _trusted_native(
        source,
        raw,
        (NativeTarget("docs/guide.md", b"# Target\n"),),
        (_reference(raw, "guide.md", "docs/guide.md"),),
    )
    first = _build(source, tmp_path, rule_ids=["M012"], native_context=verified)
    if change == "target-bytes":
        native = replace(
            verified.native, targets=(NativeTarget("docs/guide.md", b"# Changed\n"),)
        )
    elif change == "absence":
        native = replace(
            verified.native, targets=(NativeTarget("docs/guide.md", None),)
        )
    elif change == "inventory":
        native = replace(verified.native, inventory_sha256="4" * 64)
    else:
        native = replace(verified.native, revision="5" * 40)
    second = _build(
        source,
        tmp_path,
        rule_ids=["M012"],
        native_context=replace(verified, native=native),
    )
    assert second["context_sha256"] != first["context_sha256"]


def test_long_backtick_heading_metadata_keeps_fences_within_page_bounds(
    tmp_path: Path,
) -> None:
    title = "Heading " + "`" * 160
    raw = f"# {title}\n".encode()
    source = _source(tmp_path, raw)
    bundle = _build(source, tmp_path)

    assert _document(bundle, "source", source.identity)["headings"][0]["title"] == title
    _assert_exact_rows(bundle, "markdown-source", source.identity, raw)
    for page in bundle["readings"]:
        lines = page["rendered_text"].splitlines()
        assert len(lines) <= 80
        assert max(map(len, lines)) <= 80
