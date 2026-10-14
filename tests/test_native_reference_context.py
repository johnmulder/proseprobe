"""Synthetic reference closure and source-bound local-link evaluation."""

import hashlib
import json
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from benchmarks.evaluation_identity import rule_contract_snapshot
from benchmarks.native_link_context import NativeContextError, build_native_context
from benchmarks.native_reference_context import (
    build_reference_context,
    validate_reference_context,
)
from benchmarks.rule_quality import main


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Synthetic Reviewer",
            "GIT_AUTHOR_EMAIL": "synthetic@example.test",
            "GIT_COMMITTER_NAME": "Synthetic Reviewer",
            "GIT_COMMITTER_EMAIL": "synthetic@example.test",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        },
    ).stdout


@pytest.fixture
def reference_fixture(tmp_path: Path) -> dict[str, Any]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / "docs").mkdir()
    source = (
        b"# Start\r\n"
        b"Read [install](guide.md#installation) and [missing](absent.md).\r\n"
        b"[repeat][guide]\r\n\r\n"
        b"[guide]: guide.md#absent\r\n"
    )
    target = b"# Installation\nInstall the package.\n"
    (repository / "docs/start.md").write_bytes(source)
    (repository / "docs/guide.md").write_bytes(target)
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "Create synthetic references")
    revision = _git(repository, "rev-parse", "HEAD").decode().strip()
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "source.md").write_bytes(source)
    (cache / "target.md").write_bytes(target)
    identity = "synthetic/docs:docs/start.md"
    source_manifest = tmp_path / "sources.json"
    source_manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "samples": [
                    {
                        "id": identity,
                        "source_group": "synthetic/docs",
                        "pair_group": identity,
                        "revision": revision,
                        "locator": "docs/start.md",
                        "path": "source.md",
                        "sha256": hashlib.sha256(source).hexdigest(),
                        "format": "markdown",
                        "split": "development",
                        "review_status": "unreviewed",
                    }
                ],
            }
        )
    )
    native = build_native_context(
        source_manifest,
        cache,
        repository,
        revision=revision,
        source_group="synthetic/docs",
        source_ids=[identity],
        targets={"docs/guide.md": "target.md", "docs/absent.md": None},
    )
    return {
        "repository": repository,
        "cache": cache,
        "source_manifest": source_manifest,
        "native": native,
        "source": source,
        "target": target,
        "identity": identity,
        "packet": tmp_path / "packet",
    }


def _build(fixture: dict[str, Any], *, renderer: str = "github") -> dict[str, Any]:
    return build_reference_context(
        fixture["native"],
        fixture["source_manifest"],
        fixture["cache"],
        fixture["repository"],
        renderer=renderer,
    )


def _validate(bundle: dict[str, Any], fixture: dict[str, Any]) -> Any:
    return validate_reference_context(
        bundle, fixture["source_manifest"], fixture["cache"], fixture["repository"]
    )


def _packet(fixture: dict[str, Any], bundle: dict[str, Any]) -> Path:
    packet = Path(fixture["packet"])
    (packet / "originals").mkdir(parents=True)
    (packet / "originals/0000.md").write_bytes(fixture["source"])
    binding = {
        "source_id": fixture["identity"],
        "sha256": hashlib.sha256(fixture["source"]).hexdigest(),
    }
    artifacts = {
        "index": {
            "version": 1,
            "files": {"originals/0000.md": binding},
            "context": {
                "originals/0000.md": {
                    "source_group": "synthetic/docs",
                    "pair_group": fixture["identity"],
                    "split": "development",
                    "format": "markdown",
                }
            },
        },
        "contracts": rule_contract_snapshot({"M012"}),
        "native": bundle,
    }
    references = {}
    for name, value in artifacts.items():
        artifact = packet / f"{name}.json"
        artifact.write_text(json.dumps(value))
        references[name] = {
            "path": artifact.name,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        }
    manifest = packet / "annotations.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 3,
                "review": {
                    "packet_index": references["index"],
                    "rule_contracts": references["contracts"],
                    "native_context": references["native"],
                    "protocol_revision": "synthetic-1",
                    "policy": {
                        "mode": "all-rules",
                        "profile": "default",
                        "severity": "info",
                        "min_confidence": "low",
                    },
                    "reviewers": ["synthetic-reviewer"],
                },
                "files": {
                    "originals/0000.md": binding
                    | {
                        "source_group": "synthetic/docs",
                        "reviewed_rules": ["M012"],
                        "expected": [
                            {"rule_id": "M012", "line": 2, "column": 53},
                            {"rule_id": "M012", "line": 5, "column": 10},
                        ],
                        "negative_cases": [],
                    }
                },
            }
        )
    )
    return manifest


def _arguments(fixture: dict[str, Any], manifest: Path) -> list[str]:
    return [
        "--manifest",
        str(manifest),
        "--root",
        str(fixture["packet"]),
        "--mode",
        "all-rules",
        "--require-bound",
        "--format",
        "json",
        "--native-repository",
        str(fixture["repository"]),
        "--source-manifest",
        str(fixture["source_manifest"]),
        "--native-cache-root",
        str(fixture["cache"]),
    ]


def _replace_native(
    fixture: dict[str, Any], *, source: bytes | None = None, target: bytes | None = None
) -> None:
    repository = fixture["repository"]
    cache = fixture["cache"]
    if source is not None:
        fixture["source"] = source
        (repository / "docs/start.md").write_bytes(source)
        (cache / "source.md").write_bytes(source)
    if target is not None:
        fixture["target"] = target
        (repository / "docs/guide.md").write_bytes(target)
        (cache / "target.md").write_bytes(target)
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "Update synthetic native bytes")
    revision = _git(repository, "rev-parse", "HEAD").decode().strip()
    manifest = fixture["source_manifest"]
    data = json.loads(manifest.read_text())
    data["samples"][0]["revision"] = revision
    data["samples"][0]["sha256"] = hashlib.sha256(fixture["source"]).hexdigest()
    manifest.write_text(json.dumps(data))
    fixture["native"] = build_native_context(
        manifest,
        cache,
        repository,
        revision=revision,
        source_group="synthetic/docs",
        source_ids=[fixture["identity"]],
        targets={"docs/guide.md": "target.md", "docs/absent.md": None},
    )


def test_complete_reference_context_preserves_native_destination_spans(
    reference_fixture: dict[str, Any],
) -> None:
    bundle = _build(reference_fixture)
    assert bundle["version"] == 2
    assert bundle["renderer"] == "github"
    refs = bundle["references"][reference_fixture["identity"]]
    assert [
        (ref["destination"], ref["line"], ref["column"], ref["end_column"])
        for ref in refs
    ] == [
        ("guide.md#installation", 2, 16, 37),
        ("absent.md", 2, 53, 62),
        ("guide.md#absent", 5, 10, 25),
    ]
    verified = _validate(bundle, reference_fixture)
    assert verified.renderer == "github"


@pytest.mark.parametrize("target", ["docs/guide.md", "docs/absent.md"])
def test_reference_preparation_refuses_omitted_required_target(
    reference_fixture: dict[str, Any],
    target: str,
) -> None:
    del reference_fixture["native"]["targets"][target]
    with pytest.raises(NativeContextError, match="required native target"):
        _build(reference_fixture)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("destination", "other.md"),
        ("line", 1),
        ("column", 1),
        ("end_column", 99),
        ("native_path", "docs/other.md"),
        ("fragment", "other"),
        ("line", 2.0),
        ("column", 16.0),
        ("end_column", 37.0),
    ],
)
def test_reference_validation_rejects_changed_source_map(
    reference_fixture: dict[str, Any],
    field: str,
    value: Any,
) -> None:
    bundle = _build(reference_fixture)
    bundle["references"][reference_fixture["identity"]][0][field] = value
    with pytest.raises(NativeContextError, match="reference map"):
        _validate(bundle, reference_fixture)


def test_reference_validation_rejects_incomplete_map(
    reference_fixture: dict[str, Any],
) -> None:
    bundle = _build(reference_fixture)
    bundle["references"][reference_fixture["identity"]].pop()
    with pytest.raises(NativeContextError, match="reference map"):
        _validate(bundle, reference_fixture)


@pytest.mark.parametrize("renderer", ["commonmark", "GitHub", "", None])
def test_reference_preparation_requires_supported_renderer(
    reference_fixture: dict[str, Any],
    renderer: Any,
) -> None:
    with pytest.raises(NativeContextError, match="renderer"):
        _build(reference_fixture, renderer=renderer)


def test_strict_evaluator_uses_native_tree_and_maps_findings_to_reviewed_paths(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle = _build(reference_fixture)
    manifest = _packet(reference_fixture, bundle)
    assert main(_arguments(reference_fixture, manifest)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["totals"]["true_positives"] == 2
    assert report["totals"]["false_positives"] == 0
    assert report["totals"]["false_negatives"] == 0
    assert {pair["actual"]["path"] for pair in report["matches"]} == {
        "originals/0000.md"
    }
    evidence = report["local_link_context"]
    assert evidence["target_binding"] == "verified-native-reference-closure"
    assert evidence["renderer"] == "github"
    assert evidence["inventory_sha256"] == bundle["native_context"]["inventory_sha256"]
    assert (
        evidence["artifact_sha256"]
        == hashlib.sha256((manifest.parent / "native.json").read_bytes()).hexdigest()
    )
    assert evidence["excluded_destinations_count"] == 0
    assert "proseprobe-native-" not in report["policy"]["project_root"]


def test_header_rejects_changed_native_context_artifact(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _packet(reference_fixture, _build(reference_fixture))
    (manifest.parent / "native.json").write_text("{}")
    assert main(_arguments(reference_fixture, manifest)) == 2
    assert "artifact SHA-256 differs" in capsys.readouterr().err


def test_native_header_requires_all_offline_validation_inputs(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _packet(reference_fixture, _build(reference_fixture))
    assert main(_arguments(reference_fixture, manifest)[:-2]) == 2
    assert "offline native context" in capsys.readouterr().err


def test_strict_evaluator_refuses_annotation_source_identity_mismatch(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _packet(reference_fixture, _build(reference_fixture))
    data = json.loads(manifest.read_text())
    data["files"]["originals/0000.md"]["source_id"] = "another-source"
    index = manifest.parent / "index.json"
    index_data = json.loads(index.read_text())
    index_data["files"]["originals/0000.md"]["source_id"] = "another-source"
    index.write_text(json.dumps(index_data))
    data["review"]["packet_index"]["sha256"] = hashlib.sha256(
        index.read_bytes()
    ).hexdigest()
    manifest.write_text(json.dumps(data))
    assert main(_arguments(reference_fixture, manifest)) == 2
    assert "native source identities" in capsys.readouterr().err


def test_renderer_off_does_not_score_fragments(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _packet(reference_fixture, _build(reference_fixture, renderer="off"))
    data = json.loads(manifest.read_text())
    data["files"]["originals/0000.md"]["expected"].pop()
    manifest.write_text(json.dumps(data))
    assert main(_arguments(reference_fixture, manifest)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["totals"]["true_positives"] == 1
    assert report["totals"]["false_positives"] == 0
    assert report["local_link_context"]["renderer"] == "off"


def test_preparatory_v1_bundle_cannot_authorize_strict_scoring(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _packet(reference_fixture, deepcopy(reference_fixture["native"]))
    assert main(_arguments(reference_fixture, manifest)) == 2
    assert "reference context" in capsys.readouterr().err


@pytest.mark.parametrize(
    "source",
    [
        b"# Start\n{% include guide %}\n[read](guide.md)\n",
        b"# Start\n{{ generated }}\n[read](guide.md)\n",
        b"<Component>\n[read](guide.md)\n</Component>\n",
    ],
)
def test_generated_source_context_is_explicitly_unsupported(
    reference_fixture: dict[str, Any],
    source: bytes,
) -> None:
    _replace_native(reference_fixture, source=source)
    with pytest.raises(NativeContextError, match="unsupported generated native source"):
        _build(reference_fixture)


@pytest.mark.parametrize(
    "target",
    [
        b"{% generated heading %}\n",
        b"{{ generated heading }}\n",
        b"<Component />\n",
    ],
)
def test_generated_fragment_target_is_explicitly_unsupported(
    reference_fixture: dict[str, Any],
    target: bytes,
) -> None:
    _replace_native(reference_fixture, target=target)
    with pytest.raises(
        NativeContextError, match="unsupported generated native fragment target"
    ):
        _build(reference_fixture)


@pytest.mark.parametrize("field", ["source", "target"])
@pytest.mark.parametrize(
    "raw", [b"# Heading\r[read](guide.md)\r", b"# Heading\n\xff\n"]
)
def test_unsupported_encoding_or_line_endings_fail_preparation(
    reference_fixture: dict[str, Any],
    field: str,
    raw: bytes,
) -> None:
    _replace_native(reference_fixture, **{field: raw})
    with pytest.raises(NativeContextError, match=r"UTF-8|bare-CR"):
        _build(reference_fixture)


def test_production_destination_exclusions_are_recorded_without_false_absence(
    reference_fixture: dict[str, Any],
) -> None:
    extra = (
        b"\n[remote](https://example.test/guide.md)\n"
        b"[query](guide.md?raw=1)\n[root](/docs/guide.md)\n"
        b"[text](guide.txt)\n[outside](../../secret.md)\n"
        b"[encoded](guide%2fpart.md)\n[same](#start)\n"
        b"![image](not-bound.md)\n[unused]: not-bound.md\n"
        b"`[code](not-bound.md)`\n"
        b"```md\n[code](not-bound.md)\n```\n"
    )
    _replace_native(reference_fixture, source=reference_fixture["source"] + extra)
    bundle = _build(reference_fixture)
    assert len(bundle["references"][reference_fixture["identity"]]) == 3
    excluded = bundle["excluded_destinations"][reference_fixture["identity"]]
    assert {item["destination"] for item in excluded} == {
        "https://example.test/guide.md",
        "guide.md?raw=1",
        "/docs/guide.md",
        "guide.txt",
        "../../secret.md",
        "guide%2fpart.md",
        "#start",
    }
    assert all(item["reason"] == "production-resolver-exclusion" for item in excluded)
    _validate(bundle, reference_fixture)


@pytest.mark.parametrize(
    "destination",
    [
        "./guide.md#installation",
        "../docs/guide.md#installation",
        "guide%2Emd#installati%6Fn",
        "<guide.md#installation>",
        'guide.md#installation "Install"',
    ],
)
def test_supported_destination_resolution_matches_production(
    reference_fixture: dict[str, Any],
    destination: str,
) -> None:
    _replace_native(
        reference_fixture, source=f"# Start\n[read]({destination})\n".encode()
    )
    bundle = _build(reference_fixture)
    reference = bundle["references"][reference_fixture["identity"]][0]
    assert reference["native_path"] == "docs/guide.md"
    assert reference["fragment"] == "installation"
    assert bundle["excluded_destinations"][reference_fixture["identity"]] == []


def test_validation_rejects_changed_exclusion_map(
    reference_fixture: dict[str, Any],
) -> None:
    bundle = _build(reference_fixture)
    bundle["excluded_destinations"][reference_fixture["identity"]] = [
        {"destination": "invented"}
    ]
    with pytest.raises(NativeContextError, match="reference map"):
        _validate(bundle, reference_fixture)


def test_evaluator_uses_snapshots_after_cache_and_worktree_mutation(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import benchmarks.rule_quality as evaluator

    manifest = _packet(reference_fixture, _build(reference_fixture))
    validate = validate_reference_context

    def mutate_after_validation(*args: Any, **kwargs: Any) -> Any:
        verified = validate(*args, **kwargs)
        (reference_fixture["cache"] / "source.md").write_bytes(
            b"Changed cache source\n"
        )
        (reference_fixture["cache"] / "target.md").write_bytes(b"# absent\n")
        (reference_fixture["repository"] / "docs/guide.md").write_bytes(b"# absent\n")
        return verified

    monkeypatch.setattr(
        evaluator, "validate_reference_context", mutate_after_validation
    )
    assert main(_arguments(reference_fixture, manifest)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["totals"]["true_positives"] == 2
    assert report["totals"]["false_positives"] == 0


def test_bound_text_report_identifies_proof_and_renderer(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _packet(reference_fixture, _build(reference_fixture))
    arguments = _arguments(reference_fixture, manifest)
    arguments[arguments.index("json")] = "text"
    assert main(arguments) == 0
    output = capsys.readouterr().out
    assert "verified native reference closure; renderer: github" in output
    assert "artifact SHA-256:" in output
    assert "inventory SHA-256:" in output
    assert "excluded destinations: 0" in output
    assert "target binding: unavailable" not in output


@pytest.mark.parametrize("argument", ["--project-root", "--gate"])
def test_bound_context_rejects_ambiguous_project_or_curated_gate(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    argument: str,
) -> None:
    manifest = _packet(reference_fixture, _build(reference_fixture))
    assert (
        main([*_arguments(reference_fixture, manifest), argument, str(manifest.parent)])
        == 2
    )
    assert "cannot combine" in capsys.readouterr().err


def test_unbound_offline_inputs_cannot_bypass_strict_guard(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _packet(reference_fixture, _build(reference_fixture))
    data = json.loads(manifest.read_text())
    del data["review"]["native_context"]
    manifest.write_text(json.dumps(data))
    assert main(_arguments(reference_fixture, manifest)) == 2
    assert "hash-bound review artifact" in capsys.readouterr().err


def test_empty_closure_retains_all_remote_destination_exclusions(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _replace_native(
        reference_fixture, source=b"# Start\n[remote](https://example.test/start.md)\n"
    )
    reference_fixture["native"]["targets"] = {}
    bundle = _build(reference_fixture)
    assert bundle["references"][reference_fixture["identity"]] == []
    assert bundle["native_context"]["targets"] == {}
    assert len(bundle["excluded_destinations"][reference_fixture["identity"]]) == 1
    manifest = _packet(reference_fixture, bundle)
    data = json.loads(manifest.read_text())
    data["files"]["originals/0000.md"]["expected"] = []
    manifest.write_text(json.dumps(data))
    assert main(_arguments(reference_fixture, manifest)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["local_link_context"]["references_count"] == 0
    assert report["local_link_context"]["excluded_destinations_count"] == 1
    assert report["rule_metrics"]["M012"]["precision"] is None
    assert report["rule_metrics"]["M012"]["recall"] is None


def test_omitted_exclusion_cannot_be_declared_complete(
    reference_fixture: dict[str, Any],
) -> None:
    _replace_native(
        reference_fixture, source=b"# Start\n[remote](https://example.test/start.md)\n"
    )
    bundle = _build(reference_fixture)
    bundle["excluded_destinations"][reference_fixture["identity"]] = []
    with pytest.raises(NativeContextError, match="reference map"):
        _validate(bundle, reference_fixture)


def test_renderer_change_requires_reference_map_revalidation(
    reference_fixture: dict[str, Any],
) -> None:
    _replace_native(reference_fixture, target=b"{% generated heading %}\n")
    bundle = _build(reference_fixture, renderer="off")
    bundle["renderer"] = "github"
    with pytest.raises(
        NativeContextError, match="unsupported generated native fragment target"
    ):
        _validate(bundle, reference_fixture)


@pytest.mark.parametrize(
    "artifact", ["native.json", "index.json", "contracts.json", "annotations.json"]
)
def test_late_review_artifact_or_header_mutation_prevents_report_publication(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    artifact: str,
) -> None:
    import benchmarks.rule_quality as evaluator

    manifest = _packet(reference_fixture, _build(reference_fixture))
    original_collect = evaluator.collect_findings

    def mutate_after_scan(*args: Any, **kwargs: Any) -> Any:
        findings = original_collect(*args, **kwargs)
        (manifest.parent / artifact).write_text("{}")
        return findings

    monkeypatch.setattr(evaluator, "collect_findings", mutate_after_scan)
    assert main(_arguments(reference_fixture, manifest)) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "SHA-256 differs" in output.err


def test_private_native_tree_is_removed_after_scan_failure(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import benchmarks.rule_quality as evaluator
    from benchmarks.native_link_context import materialize_native_context
    from benchmarks.quality_scoring import AnnotationError

    manifest = _packet(reference_fixture, _build(reference_fixture))
    created = []

    @contextmanager
    def observe_tree(context: Any) -> Iterator[Path]:
        with materialize_native_context(context) as root:
            created.append(root)
            yield root

    def fail_scan(*_args: Any, **_kwargs: Any) -> Any:
        raise AnnotationError("synthetic scan failure")

    monkeypatch.setattr(evaluator, "materialize_native_context", observe_tree)
    monkeypatch.setattr(evaluator, "collect_findings", fail_scan)
    assert main(_arguments(reference_fixture, manifest)) == 2
    assert "synthetic scan failure" in capsys.readouterr().err
    assert len(created) == 1
    assert not created[0].exists()


def test_source_link_can_use_another_verified_source_binding(
    reference_fixture: dict[str, Any],
) -> None:
    _replace_native(reference_fixture, source=b"# Start\n[self](start.md#start)\n")
    reference_fixture["native"]["targets"] = {}
    bundle = _build(reference_fixture)
    assert (
        bundle["references"][reference_fixture["identity"]][0]["native_path"]
        == "docs/start.md"
    )
    _validate(bundle, reference_fixture)


def _forbid_source_reads(
    fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    import benchmarks.native_link_context as native

    original_read = Path.read_bytes

    def read_metadata_only(path: Path) -> bytes:
        if path.is_relative_to(fixture["cache"]) or path.is_relative_to(
            fixture["packet"] / "originals"
        ):
            raise AssertionError(
                "native-bound metadata rejection must precede all source bytes"
            )
        return original_read(path)

    def forbidden_cache(*_args: Any, **_kwargs: Any) -> bytes:
        raise AssertionError(
            "native-bound metadata rejection must precede cached source bytes"
        )

    monkeypatch.setattr(Path, "read_bytes", read_metadata_only)
    monkeypatch.setattr(native, "_read_cache_file", forbidden_cache)


@pytest.mark.parametrize(
    "change",
    [
        "holdout-source",
        "source-id",
        "source-sha",
        "source-group",
        "index-id",
        "index-sha",
        "index-group",
        "index-holdout",
        "annotation-id",
        "annotation-sha",
        "annotation-group",
    ],
)
def test_native_bound_metadata_rejects_before_packet_and_cache_bytes(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    manifest = _packet(reference_fixture, _build(reference_fixture))
    annotations = json.loads(manifest.read_text())
    if change.startswith("source-") or change == "holdout-source":
        source_manifest = reference_fixture["source_manifest"]
        data = json.loads(source_manifest.read_text())
        field, value = {
            "holdout-source": ("split", "holdout"),
            "source-id": ("id", "other-source"),
            "source-sha": ("sha256", "0" * 64),
            "source-group": ("source_group", "other-group"),
        }[change]
        data["samples"][0][field] = value
        source_manifest.write_text(json.dumps(data))
    elif change.startswith("index-"):
        index_path = manifest.parent / "index.json"
        index = json.loads(index_path.read_text())
        if change == "index-id":
            index["files"]["originals/0000.md"]["source_id"] = "other-source"
        elif change == "index-sha":
            index["files"]["originals/0000.md"]["sha256"] = "0" * 64
        elif change == "index-group":
            index["context"]["originals/0000.md"]["source_group"] = "other-group"
        else:
            index["context"]["originals/0000.md"]["split"] = "holdout"
        index_path.write_text(json.dumps(index))
        annotations["review"]["packet_index"]["sha256"] = hashlib.sha256(
            index_path.read_bytes()
        ).hexdigest()
        manifest.write_text(json.dumps(annotations))
    else:
        field, value = {
            "annotation-id": ("source_id", "other-source"),
            "annotation-sha": ("sha256", "0" * 64),
            "annotation-group": ("source_group", "other-group"),
        }[change]
        annotations["files"]["originals/0000.md"][field] = value
        manifest.write_text(json.dumps(annotations))
    _forbid_source_reads(reference_fixture, monkeypatch)
    assert main(_arguments(reference_fixture, manifest)) == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "artifact",
    ["annotations.json", "index.json", "native.json", "contracts.json", "sources.json"],
)
def test_late_metadata_change_is_rejected_before_first_native_cache_byte(
    reference_fixture: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    artifact: str,
) -> None:
    import benchmarks.native_link_context as native

    manifest = _packet(reference_fixture, _build(reference_fixture))
    inventory = native._inventory

    def mutate_during_inventory(*args: Any, **kwargs: Any) -> Any:
        entries = inventory(*args, **kwargs)
        path = (
            reference_fixture["source_manifest"]
            if artifact == "sources.json"
            else manifest.parent / artifact
        )
        path.write_text("{}")
        return entries

    monkeypatch.setattr(native, "_inventory", mutate_during_inventory)
    _forbid_source_reads(reference_fixture, monkeypatch)
    assert main(_arguments(reference_fixture, manifest)) == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", ["invalid-json", "missing-file"])
def test_non_native_manifest_errors_preserve_path_specific_diagnostics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    manifest = tmp_path / "annotations.json"
    if kind == "invalid-json":
        manifest.write_text("{ invalid JSON")
    original_read = Path.read_bytes

    def manifest_read_only(path: Path) -> bytes:
        if path != manifest:
            raise AssertionError("invalid manifest must fail before source access")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", manifest_read_only)
    assert main(["--manifest", str(manifest), "--root", str(tmp_path)]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert (
        f"Rule quality error: {manifest}: invalid JSON or unreadable manifest:"
        in output.err
    )
