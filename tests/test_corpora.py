"""Offline tests for evaluation source provenance and native dataset readers."""

import hashlib
import json
from pathlib import Path

import pytest
from benchmarks import corpora
from benchmarks.corpora import (
    CorpusError,
    load_sources,
    read_codesearchnet,
    read_m2,
    read_markdown,
    read_pairs,
    read_sample,
)


def _record(
    root: Path, identity: str = "example", **updates: object
) -> dict[str, object]:
    path = root / f"{identity}.md"
    content = b"---\ntitle: Example\n---\n# Exact Markdown\n\n{% data example %}\r\n"
    path.write_bytes(content)
    record: dict[str, object] = {
        "id": identity,
        "source_group": "github/example",
        "pair_group": identity,
        "url": "https://example.org/source.md",
        "revision": "a" * 40,
        "license": "CC-BY-4.0",
        "license_url": "https://example.org/LICENSE",
        "attribution": "Example authors",
        "sha256": hashlib.sha256(content).hexdigest(),
        "path": path.name,
        "locator": f"docs/{identity}.md",
        "format": "markdown",
        "split": "development",
        "review_status": "unreviewed",
    }
    record.update(updates)
    return record


def _manifest(root: Path, records: list[dict[str, object]]) -> Path:
    path = root / "sources.json"
    path.write_text(json.dumps({"version": 1, "samples": records}), encoding="utf-8")
    return path


def test_markdown_preserves_raw_text_and_source_identity(tmp_path: Path) -> None:
    record = _record(tmp_path)
    [source] = load_sources(_manifest(tmp_path, [record]), tmp_path)

    sample = read_markdown(source, tmp_path)

    assert sample.identity == "example"
    assert sample.source_group == "github/example"
    assert sample.split == "development"
    assert sample.original.encode() == (tmp_path / "example.md").read_bytes()
    assert sample.references == ()


@pytest.mark.parametrize(
    "field",
    ["url", "revision", "license", "license_url", "attribution", "sha256", "locator"],
)
def test_manifest_requires_provenance(tmp_path: Path, field: str) -> None:
    record = _record(tmp_path)
    del record[field]

    with pytest.raises(CorpusError, match=field):
        load_sources(_manifest(tmp_path, [record]), tmp_path)


@pytest.mark.parametrize("split", ["train", "", None])
def test_manifest_rejects_invalid_split(tmp_path: Path, split: object) -> None:
    record = _record(tmp_path, split=split)

    with pytest.raises(CorpusError, match="split"):
        load_sources(_manifest(tmp_path, [record]), tmp_path)


def test_manifest_rejects_duplicate_identity(tmp_path: Path) -> None:
    record = _record(tmp_path)

    with pytest.raises(CorpusError, match="duplicate"):
        load_sources(_manifest(tmp_path, [record, record]), tmp_path)


@pytest.mark.parametrize("path", ["../outside.md", "/tmp/outside.md"])
def test_manifest_rejects_path_escape(tmp_path: Path, path: str) -> None:
    record = _record(tmp_path, path=path)

    with pytest.raises(CorpusError, match="path"):
        load_sources(_manifest(tmp_path, [record]), tmp_path)


def test_manifest_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    root.mkdir()
    record = _record(root)
    (tmp_path / "outside.md").write_text("external", encoding="utf-8")
    (root / "link.md").symlink_to(tmp_path / "outside.md")
    record["path"] = "link.md"

    with pytest.raises(CorpusError, match="path"):
        load_sources(_manifest(root, [record]), root)


def test_manifest_rejects_corrupted_cached_sample(tmp_path: Path) -> None:
    record = _record(tmp_path)
    (tmp_path / "example.md").write_text("corrupted", encoding="utf-8")

    with pytest.raises(CorpusError, match="checksum"):
        load_sources(_manifest(tmp_path, [record]), tmp_path)


def test_markdown_rechecks_checksum_before_conversion(tmp_path: Path) -> None:
    [source] = load_sources(_manifest(tmp_path, [_record(tmp_path)]), tmp_path)
    (tmp_path / "example.md").write_text("corrupted", encoding="utf-8")

    with pytest.raises(CorpusError, match="checksum"):
        read_markdown(source, tmp_path)


def test_manifest_checks_native_download_artifacts(tmp_path: Path) -> None:
    record = _record(tmp_path)
    manifest = _manifest(tmp_path, [record])
    data = json.loads(manifest.read_text())
    (tmp_path / "archive.gz").write_bytes(b"corrupted")
    data["artifacts"] = [
        {
            "url": "https://example.org/archive.gz",
            "path": "archive.gz",
            "sha256": hashlib.sha256(b"original archive").hexdigest(),
        }
    ]
    manifest.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(CorpusError, match="artifact checksum"):
        load_sources(manifest, tmp_path)


@pytest.mark.parametrize(
    "group", ["source_group", "pair_group", "near_duplicate_group"]
)
def test_manifest_keeps_related_samples_in_one_split(
    tmp_path: Path, group: str
) -> None:
    first = _record(tmp_path, "first", source_group="one", pair_group="one")
    second = _record(
        tmp_path, "second", source_group="two", pair_group="two", split="holdout"
    )
    first[group] = second[group] = "shared"
    (tmp_path / "second.md").write_text("Different text", encoding="utf-8")
    second["sha256"] = hashlib.sha256(b"Different text").hexdigest()

    with pytest.raises(CorpusError, match="split"):
        load_sources(_manifest(tmp_path, [first, second]), tmp_path)


def test_manifest_detects_normalized_duplicate_across_splits(tmp_path: Path) -> None:
    first = _record(tmp_path, "first", source_group="one")
    second = _record(tmp_path, "second", source_group="two", split="holdout")
    text = (tmp_path / "first.md").read_text(encoding="utf-8")
    text = text.upper().replace(" ", "  ")
    (tmp_path / "second.md").write_text(text, encoding="utf-8")
    second["sha256"] = hashlib.sha256(text.encode()).hexdigest()

    with pytest.raises(CorpusError, match=r"duplicate.*split"):
        load_sources(_manifest(tmp_path, [first, second]), tmp_path)


def _code_record() -> dict[str, object]:
    return {
        "repo": "authors/example",
        "path": "client.py",
        "func_name": "read",
        "original_string": 'def read():\n    """Read a file."""\n    return None',
        "docstring": "Read a file.",
        "language": "python",
        "sha": "b" * 40,
        "url": "https://github.com/authors/example/blob/revision/client.py#L17-L19",
    }


def test_codesearchnet_preserves_function_docstring_and_metadata() -> None:
    record = _code_record()

    [sample] = read_codesearchnet(json.dumps(record))

    assert sample.original == record["original_string"]
    assert sample.docstring == "Read a file."
    assert sample.repository == "authors/example"
    assert sample.metadata == record
    assert sample.context == "function-only; surrounding module unavailable"


@pytest.mark.parametrize(
    "field", ["repo", "path", "original_string", "docstring", "sha", "url"]
)
def test_codesearchnet_rejects_missing_fields(field: str) -> None:
    record = _code_record()
    del record[field]

    with pytest.raises(CorpusError, match=field):
        read_codesearchnet(json.dumps(record))


@pytest.mark.parametrize(("dataset", "count"), [("jfleg", 4), ("asset", 10)])
def test_pairs_preserve_all_references_identity_and_split(
    dataset: str, count: int
) -> None:
    references = tuple((f"Revision {index}.",) for index in range(count))

    [pair] = read_pairs(("Original .",), references, dataset, "native:dev", "holdout")

    assert pair.identity == "native:dev:1"
    assert pair.pair_group == "native:dev:1"
    assert pair.original == "Original ."
    assert pair.references == tuple(f"Revision {index}." for index in range(count))
    assert pair.split == "holdout"


@pytest.mark.parametrize(("dataset", "count"), [("jfleg", 3), ("asset", 9)])
def test_pairs_reject_missing_references(dataset: str, count: int) -> None:
    with pytest.raises(CorpusError, match="references"):
        read_pairs(
            ("Original.",), (("Revised.",),) * count, dataset, "source", "holdout"
        )


def test_pairs_reject_misaligned_reference_files() -> None:
    with pytest.raises(CorpusError, match="aligned"):
        read_pairs(("One.", "Two."), (("One.",),) * 4, "jfleg", "source", "holdout")


def test_pair_bundle_checks_native_shape_and_checksum(tmp_path: Path) -> None:
    raw = json.dumps({"original": "Original.", "references": ["Revised."] * 4}).encode()
    record = _record(tmp_path, format="jfleg")
    (tmp_path / "example.md").write_bytes(raw)
    record["sha256"] = hashlib.sha256(raw).hexdigest()
    [source] = load_sources(_manifest(tmp_path, [record]), tmp_path)

    sample = read_sample(source, tmp_path)

    assert sample.original == "Original."
    assert sample.references == ("Revised.",) * 4
    (tmp_path / "example.md").write_text("changed", encoding="utf-8")
    with pytest.raises(CorpusError, match="checksum"):
        read_sample(source, tmp_path)


def test_pair_original_duplicates_cannot_hide_behind_different_references(
    tmp_path: Path,
) -> None:
    records = []
    for identity, split, revision in [
        ("one", "development", "First revision."),
        ("two", "holdout", "Another revision."),
    ]:
        record = _record(
            tmp_path, identity, source_group=identity, split=split, format="jfleg"
        )
        raw = json.dumps(
            {"original": "Same original.", "references": [revision] * 4}
        ).encode()
        (tmp_path / f"{identity}.md").write_bytes(raw)
        record["sha256"] = hashlib.sha256(raw).hexdigest()
        records.append(record)

    with pytest.raises(CorpusError, match=r"duplicate.*split"):
        load_sources(_manifest(tmp_path, records), tmp_path)


def test_m2_preserves_annotators_noops_and_token_character_spans() -> None:
    text = (
        "S I do n't like tea .\n"
        "A 3 4|||R:VERB|||love|||REQUIRED|||-NONE-|||0\n"
        "A 4 4|||M:ADJ|||green|||REQUIRED|||-NONE-|||0\n"
        "A 1 3|||U:VERB||||||REQUIRED|||-NONE-|||1\n"
        "A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||2\n"
    )

    [sentence] = read_m2(text)

    assert sentence.original == "I do n't like tea ."
    assert [edit.annotator for edit in sentence.edits] == ["0", "0", "1", "2"]
    assert sentence.edits[-1].is_noop
    assert sentence.source_span(sentence.edits[0]) == (9, 13)
    assert sentence.source_span(sentence.edits[1]) == (14, 14)
    assert sentence.source_span(sentence.edits[2]) == (2, 8)
    assert sentence.source_span(sentence.edits[-1]) is None
    assert sentence.original[2:8] == "do n't"
    assert sentence.tokenized is True


@pytest.mark.parametrize("span", ["-2 1", "3 1", "0 9"])
def test_m2_rejects_invalid_token_spans(span: str) -> None:
    with pytest.raises(CorpusError, match="span"):
        read_m2(f"S One sentence .\nA {span}|||R:OTHER|||x|||REQUIRED|||NONE|||0\n")


def test_cli_validates_without_displaying_text_and_exports_blind_originals(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = _manifest(tmp_path, [_record(tmp_path)])

    status = corpora.main(
        [
            str(manifest),
            "--cache",
            str(tmp_path),
            "--export-blind",
            "blind/originals.jsonl",
        ]
    )

    assert status == 0
    output = capsys.readouterr().out
    assert "Exact Markdown" not in output
    assert json.loads(output)["samples"] == 1
    [record] = [
        json.loads(line)
        for line in (tmp_path / "blind/originals.jsonl").read_text().splitlines()
    ]
    assert record["original"].encode() == (tmp_path / "example.md").read_bytes()
    assert "references" not in record
    assert "findings" not in record


def test_review_packet_is_source_bound_and_initially_unreviewed(tmp_path: Path) -> None:
    from benchmarks.quality_scoring import load_annotations

    from proseprobe.rules import get_all_rules

    manifest = _manifest(tmp_path, [_record(tmp_path)])
    assert (
        corpora.main(
            [
                str(manifest),
                "--cache",
                str(tmp_path),
                "--export-review-packet",
                "new-packet",
            ]
        )
        == 0
    )
    packet = tmp_path / "new-packet"
    annotations = load_annotations(
        packet / "annotations.unreviewed.json",
        packet,
        {rule.id for rule in get_all_rules()},
    )
    assert annotations.source_binding == "sha256-utf8"
    assert annotations.scopes == ()
    assert annotations.expected == annotations.negative_cases == ()
    assert annotations.review_provenance["reviewers"] == []
    [source] = annotations.files
    assert source.read_bytes() == (tmp_path / "example.md").read_bytes()
    index = json.loads((packet / "index.json").read_text())
    [context] = index["context"].values()
    assert context == {
        "source_group": "github/example",
        "pair_group": "example",
        "split": "development",
        "format": "markdown",
    }
    assert "references" not in json.dumps(index)
    assert "findings" not in json.dumps(index)
    with pytest.raises(SystemExit):
        corpora.main(
            [
                str(manifest),
                "--cache",
                str(tmp_path),
                "--export-review-packet",
                "new-packet",
            ]
        )
