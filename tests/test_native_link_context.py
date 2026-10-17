"""Synthetic offline Git proofs for declared native Markdown context."""

import hashlib
import json
import os
import subprocess
import zlib
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from benchmarks.native_link_context import (
    NativeContextError,
    NativeTarget,
    build_native_context,
    materialize_native_context,
    validate_native_context,
)


def _git(repository: Path, *arguments: str) -> bytes:
    result = subprocess.run(
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
    )
    return result.stdout


@pytest.fixture
def native_fixture(tmp_path: Path) -> dict[str, Any]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / "docs").mkdir()
    original = b"# Start\nRead the installation guide.\n"
    target = b"# Installation\nInstall the package.\n"
    (repository / "docs" / "start.md").write_bytes(original)
    (repository / "docs" / "guide.md").write_bytes(target)
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "Create synthetic context")
    revision = _git(repository, "rev-parse", "HEAD").decode().strip()
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "source.md").write_bytes(original)
    (cache / "target.md").write_bytes(target)
    record = {
        "id": "synthetic/docs:docs/start.md",
        "source_group": "synthetic/docs",
        "pair_group": "synthetic/docs:docs/start.md",
        "revision": revision,
        "locator": "docs/start.md",
        "path": "source.md",
        "sha256": hashlib.sha256(original).hexdigest(),
        "format": "markdown",
        "split": "development",
        "review_status": "unreviewed",
    }
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"version": 1, "samples": [record]}))
    return {
        "manifest": manifest,
        "cache": cache,
        "repository": repository,
        "revision": revision,
        "source_group": "synthetic/docs",
        "source_ids": [record["id"]],
        "targets": {"docs/guide.md": "target.md", "docs/absent.md": None},
    }


def _build(fixture: dict[str, Any]) -> dict[str, Any]:
    return build_native_context(
        fixture["manifest"],
        fixture["cache"],
        fixture["repository"],
        revision=fixture["revision"],
        source_group=fixture["source_group"],
        source_ids=fixture["source_ids"],
        targets=fixture["targets"],
    )


def _validate(bundle: dict[str, Any], fixture: dict[str, Any]) -> Any:
    return validate_native_context(
        bundle, fixture["manifest"], fixture["cache"], fixture["repository"]
    )


def _manifest_record(fixture: dict[str, Any], **changes: Any) -> None:
    manifest = fixture["manifest"]
    content = json.loads(manifest.read_text())
    content["samples"][0].update(changes)
    manifest.write_text(json.dumps(content))


def _forbid_cache_reads(monkeypatch: pytest.MonkeyPatch, cache: Path) -> None:
    import benchmarks.native_link_context as native_context

    read_bytes = Path.read_bytes
    original_open = os.open

    def checked_read(path: Path) -> bytes:
        if path.is_relative_to(cache):
            raise AssertionError("metadata rejection must precede cached byte access")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", checked_read)

    def checked_open(
        name: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if dir_fd is not None or Path(os.fsdecode(name)).is_relative_to(cache):
            raise AssertionError(
                "metadata rejection must precede cache descriptor access"
            )
        return original_open(name, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", checked_open)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, checked_open})

    def forbidden_confined_read(_root: Path, _name: str) -> bytes:
        raise AssertionError("metadata rejection must precede cached byte access")

    monkeypatch.setattr(native_context, "_read_cache_file", forbidden_confined_read)


def test_complete_offline_inventory_binds_declared_targets_and_native_paths(
    native_fixture: dict[str, Any],
) -> None:
    bundle = _build(native_fixture)
    context = _validate(bundle, native_fixture)

    assert bundle["target_scope"] == "explicitly-declared"
    assert bundle["targets"]["docs/absent.md"] == {"status": "absent"}
    assert len(context.sources) == 1
    assert len(context.targets) == 2
    with materialize_native_context(context) as root:
        assert root != native_fixture["repository"]
        assert (
            root / "docs/start.md"
        ).read_bytes() == b"# Start\nRead the installation guide.\n"
        assert (
            root / "docs/guide.md"
        ).read_bytes() == b"# Installation\nInstall the package.\n"
        assert not (root / "docs/absent.md").exists()
        assert not any(path.is_symlink() for path in root.rglob("*"))
    assert not root.exists()


@pytest.mark.parametrize("split", ["holdout", "invented"])
def test_selected_non_development_source_rejected_before_cached_bytes(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch, split: str
) -> None:
    _manifest_record(native_fixture, split=split)
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match="development"):
        _build(native_fixture)


def test_group_with_reserved_member_rejected_before_cached_bytes(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = native_fixture["manifest"]
    content = json.loads(manifest.read_text())
    reserved = {**content["samples"][0], "id": "reserved", "split": "holdout"}
    content["samples"].append(reserved)
    manifest.write_text(json.dumps(content))
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match="development"):
        _build(native_fixture)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("revision", "0" * 40, "revision"),
        ("source_group", "different/group", "group"),
        ("locator", "../escape.md", "path"),
        ("path", "../escape.md", "path"),
        ("format", "jfleg", "Markdown"),
    ],
)
def test_wrong_source_metadata_rejected_before_cached_bytes(
    native_fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
    match: str,
) -> None:
    _manifest_record(native_fixture, **{field: value})
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match=match):
        _build(native_fixture)


@pytest.mark.parametrize("revision", ["HEAD", "v1", "0" * 39, "A" * 40])
def test_revision_requires_exact_lowercase_commit_identity(
    native_fixture: dict[str, Any], revision: str
) -> None:
    native_fixture["revision"] = revision

    with pytest.raises(NativeContextError, match="revision"):
        _build(native_fixture)


def test_cached_source_must_match_frozen_sha256(native_fixture: dict[str, Any]) -> None:
    (native_fixture["cache"] / "source.md").write_bytes(b"Edited source\n")

    with pytest.raises(NativeContextError, match="SHA-256"):
        _build(native_fixture)


def test_source_bytes_must_match_pinned_native_blob(
    native_fixture: dict[str, Any],
) -> None:
    changed = b"Different native source\n"
    (native_fixture["cache"] / "source.md").write_bytes(changed)
    _manifest_record(native_fixture, sha256=hashlib.sha256(changed).hexdigest())

    with pytest.raises(NativeContextError, match="blob"):
        _build(native_fixture)


def test_present_upstream_target_cannot_be_declared_absent(
    native_fixture: dict[str, Any],
) -> None:
    native_fixture["targets"]["docs/guide.md"] = None

    with pytest.raises(NativeContextError, match=r"present|exists"):
        _build(native_fixture)


def test_missing_cache_target_is_not_verified_absence(
    native_fixture: dict[str, Any],
) -> None:
    (native_fixture["cache"] / "target.md").unlink()

    with pytest.raises(NativeContextError, match=r"unreadable|missing"):
        _build(native_fixture)


def test_cached_target_must_match_pinned_blob(native_fixture: dict[str, Any]) -> None:
    (native_fixture["cache"] / "target.md").write_bytes(b"# Stale target\n")

    with pytest.raises(NativeContextError, match="blob"):
        _build(native_fixture)


def test_validator_rejects_target_changed_since_bundle_freeze(
    native_fixture: dict[str, Any],
) -> None:
    bundle = _build(native_fixture)
    (native_fixture["cache"] / "target.md").write_bytes(b"# Stale target\n")

    with pytest.raises(NativeContextError, match="SHA-256"):
        _validate(bundle, native_fixture)


@pytest.mark.parametrize(
    "change",
    [
        "manifest-hash",
        "inventory-hash",
        "source-path",
        "source-blob",
        "target-hash",
        "unknown-key",
    ],
)
def test_validator_rejects_stale_or_altered_bundle(
    native_fixture: dict[str, Any], change: str
) -> None:
    bundle = deepcopy(_build(native_fixture))
    source = next(iter(bundle["sources"].values()))
    if change == "manifest-hash":
        bundle["manifest_sha256"] = "0" * 64
    elif change == "inventory-hash":
        bundle["inventory_sha256"] = "0" * 64
    elif change == "source-path":
        source["native_path"] = "docs/guide.md"
    elif change == "source-blob":
        source["blob_id"] = "0" * 40
    elif change == "target-hash":
        bundle["targets"]["docs/guide.md"]["sha256"] = "0" * 64
    else:
        bundle["extra"] = "unknown"

    with pytest.raises(NativeContextError):
        _validate(bundle, native_fixture)


@pytest.mark.parametrize(
    "path", ["../escape.md", "/escape.md", "a/../b.md", "a//b.md", "a\\b.md"]
)
def test_noncanonical_target_paths_rejected_before_cached_bytes(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    native_fixture["targets"] = {path: "target.md"}
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match="path"):
        _build(native_fixture)


@pytest.mark.parametrize("cache_path", ["../escape.md", "/escape.md", "a/../b.md"])
def test_cache_path_escape_rejected_before_cached_bytes(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch, cache_path: str
) -> None:
    native_fixture["targets"]["docs/guide.md"] = cache_path
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match="path"):
        _build(native_fixture)


def test_cache_symlink_rejected_before_cached_bytes(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = native_fixture["cache"]
    (cache / "target-link.md").symlink_to(cache / "target.md")
    native_fixture["targets"]["docs/guide.md"] = "target-link.md"
    _forbid_cache_reads(monkeypatch, cache)

    with pytest.raises(NativeContextError, match="symlink"):
        _build(native_fixture)


@pytest.mark.parametrize("kind", ["symlink", "submodule"])
def test_native_special_ancestry_cannot_prove_absence(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    repository = native_fixture["repository"]
    if kind == "symlink":
        (repository / "linked").symlink_to("docs")
        _git(repository, "add", "linked")
    else:
        _git(
            repository,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{native_fixture['revision']},linked",
        )
    _git(repository, "commit", "-qm", "Add special native entry")
    native_fixture["revision"] = _git(repository, "rev-parse", "HEAD").decode().strip()
    _manifest_record(native_fixture, revision=native_fixture["revision"])
    native_fixture["targets"] = {"linked/guide.md": None}
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match=r"symlink|submodule"):
        _build(native_fixture)


def test_missing_tree_object_prevents_complete_inventory(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = native_fixture["repository"]
    tree_id = _git(repository, "rev-parse", "HEAD:docs").decode().strip()
    (repository / ".git/objects" / tree_id[:2] / tree_id[2:]).unlink()
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match=r"Git|inventory|object"):
        _build(native_fixture)


def test_promisor_repository_is_rejected_without_fetching(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(native_fixture["repository"], "config", "remote.origin.promisor", "true")
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match=r"promisor|partial"):
        _build(native_fixture)


def test_replacement_objects_cannot_change_pinned_inventory(
    native_fixture: dict[str, Any],
) -> None:
    repository = native_fixture["repository"]
    pinned = native_fixture["revision"]
    (repository / "docs/guide.md").write_bytes(b"Replacement target\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "Create replacement commit")
    replacement = _git(repository, "rev-parse", "HEAD").decode().strip()
    _git(repository, "replace", pinned, replacement)

    assert _build(native_fixture)["revision"] == pinned


def test_verified_snapshot_does_not_follow_later_cache_mutation(
    native_fixture: dict[str, Any],
) -> None:
    context = _validate(_build(native_fixture), native_fixture)
    (native_fixture["cache"] / "target.md").write_bytes(b"Later edit\n")
    with materialize_native_context(context) as root:
        assert (
            root / "docs/guide.md"
        ).read_bytes() == b"# Installation\nInstall the package.\n"


@pytest.mark.parametrize(
    "native_path", ["../escape.md", "/escape.md", "a/../escape.md"]
)
def test_constructed_context_cannot_escape_private_materialization(
    native_fixture: dict[str, Any], native_path: str
) -> None:
    context = _validate(_build(native_fixture), native_fixture)
    altered = replace(
        context, sources=(replace(context.sources[0], native_path=native_path),)
    )

    with (
        pytest.raises(NativeContextError, match="path"),
        materialize_native_context(altered),
    ):
        pytest.fail("invalid lexical paths must be rejected before creating files")


def test_inventory_entry_omission_cannot_freeze_false_absence(
    native_fixture: dict[str, Any],
) -> None:
    bundle = _build(native_fixture)
    bundle["inventory"] = [
        row for row in bundle["inventory"] if row["path"] != "docs/guide.md"
    ]
    bundle["targets"]["docs/guide.md"] = {"status": "absent"}

    with pytest.raises(NativeContextError, match="inventory"):
        _validate(bundle, native_fixture)


def test_corrupt_tree_object_name_cannot_supply_pinned_proof(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = native_fixture["repository"]
    tree_id = _git(repository, "rev-parse", "HEAD^{tree}").decode().strip()
    raw = _git(repository, "cat-file", "tree", tree_id).replace(b"docs\0", b"else\0", 1)
    object_bytes = f"tree {len(raw)}\0".encode("ascii") + raw
    object_path = repository / ".git/objects" / tree_id[:2] / tree_id[2:]
    object_path.unlink()
    object_path.write_bytes(zlib.compress(object_bytes))
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match="object identity"):
        _build(native_fixture)


def test_git_object_reader_strips_inherited_repository_and_fetch_controls(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    original_run = subprocess.run
    calls = []

    def observed_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((args[0], kwargs))
        return original_run(*args, **kwargs)

    monkeypatch.setenv("GIT_DIR", str(native_fixture["cache"]))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "remote.origin.promisor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    monkeypatch.setattr(subprocess, "run", observed_run)

    _build(native_fixture)

    assert calls
    for arguments, options in calls:
        environment = options["env"]
        assert environment["GIT_NO_LAZY_FETCH"] == "1"
        assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
        assert "GIT_DIR" not in environment
        assert "GIT_CONFIG_COUNT" not in environment
        assert "--no-replace-objects" in arguments
        assert "protocol.allow=never" in arguments
        assert not options.get("shell", False)


def test_cache_symlink_replacement_before_open_does_not_follow_target(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import benchmarks.native_link_context as native_context

    original_path = native_context._cache_path
    target_path = native_fixture["cache"] / "target.md"
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside bytes must not be opened\n")
    calls = 0

    def replacing_path(root: Path, name: Any) -> Path:
        nonlocal calls
        resolved = original_path(root, name)
        if name == "target.md":
            calls += 1
            if calls == 2:
                target_path.unlink()
                target_path.symlink_to(outside)
        return resolved

    monkeypatch.setattr(native_context, "_cache_path", replacing_path)

    with pytest.raises(NativeContextError, match="unreadable confined"):
        _build(native_fixture)


@pytest.mark.parametrize("location", ["source", "target"])
def test_empty_cache_path_rejected_before_cached_bytes(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    if location == "source":
        _manifest_record(native_fixture, path=".")
    else:
        native_fixture["targets"]["docs/guide.md"] = "."
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match="path"):
        _build(native_fixture)


@pytest.mark.parametrize("group_field", ["pair_group", "near_duplicate_group"])
def test_related_reserved_group_rejected_before_cached_bytes(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch, group_field: str
) -> None:
    manifest = native_fixture["manifest"]
    content = json.loads(manifest.read_text())
    selected = content["samples"][0]
    selected[group_field] = "shared-group"
    reserved = {
        **selected,
        "id": "reserved-source",
        "source_group": "reserved/docs",
        "split": "holdout",
        "path": "reserved.md",
    }
    content["samples"].append(reserved)
    manifest.write_text(json.dumps(content))
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match="development"):
        _build(native_fixture)


def test_declared_target_cannot_read_known_holdout_cache_path(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = native_fixture["manifest"]
    content = json.loads(manifest.read_text())
    reserved = {
        **content["samples"][0],
        "id": "reserved-source",
        "source_group": "reserved/docs",
        "pair_group": "reserved-pair",
        "split": "holdout",
        "path": "reserved.md",
        "sha256": hashlib.sha256(b"different reserved source").hexdigest(),
    }
    content["samples"].append(reserved)
    manifest.write_text(json.dumps(content))
    native_fixture["targets"]["docs/guide.md"] = "reserved.md"
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match=r"holdout|reserved"):
        _build(native_fixture)


def test_constructed_absent_target_cannot_overlap_present_source(
    native_fixture: dict[str, Any],
) -> None:
    context = _validate(_build(native_fixture), native_fixture)
    contradictory = replace(context, targets=(NativeTarget("docs/start.md", None),))

    with (
        pytest.raises(NativeContextError, match="absent"),
        materialize_native_context(contradictory),
    ):
        pytest.fail("a present source cannot also supply verified absence")


def test_case_aliases_cannot_overwrite_present_bytes_or_supply_absence(
    native_fixture: dict[str, Any], tmp_path: Path
) -> None:
    probe = tmp_path / "CaseProbe"
    probe.write_bytes(b"probe")
    insensitive = (tmp_path / "caseprobe").exists()
    probe.unlink()
    if not insensitive:
        pytest.skip("this filesystem distinguishes case aliases")
    context = _validate(_build(native_fixture), native_fixture)
    present_alias = replace(
        context,
        targets=(*context.targets, NativeTarget("docs/START.md", b"different bytes\n")),
    )
    absent_alias = replace(
        context, targets=(*context.targets, NativeTarget("docs/START.md", None))
    )

    with (
        pytest.raises(NativeContextError, match="collision"),
        materialize_native_context(present_alias),
    ):
        pytest.fail("case aliases must not overwrite distinct native files")
    with (
        pytest.raises(NativeContextError, match="absent"),
        materialize_native_context(absent_alias),
    ):
        pytest.fail("case aliases cannot establish pinned target absence")


def test_selected_source_exact_holdout_sha_rejected_before_cached_bytes(
    native_fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = native_fixture["manifest"]
    content = json.loads(manifest.read_text())
    selected = content["samples"][0]
    content["samples"].append(
        {
            **selected,
            "id": "reserved-source",
            "source_group": "reserved/docs",
            "pair_group": "reserved-pair",
            "split": "holdout",
            "path": "reserved.md",
            "locator": "other/native.md",
        }
    )
    manifest.write_text(json.dumps(content))
    _forbid_cache_reads(monkeypatch, native_fixture["cache"])

    with pytest.raises(NativeContextError, match=r"SHA-256.*holdout"):
        _build(native_fixture)
