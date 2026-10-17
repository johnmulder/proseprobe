"""Bind declared development targets to an offline pinned Git tree.

This preparation stage does not enumerate Markdown links or enable evaluation.
Its verified bytes can be materialized separately from a native working tree.
Exact cross-split hashes can be rejected from metadata. Normalized duplicate
evidence remains unavailable because reserved sources are not read here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any

from benchmarks.corpora import CorpusError


class NativeContextError(CorpusError):
    """An offline context lacks a supported development binding."""


@dataclass(frozen=True)
class NativeSource:
    """Verified original bytes at their pinned native path."""

    source_id: str
    native_path: str
    raw: bytes


@dataclass(frozen=True)
class NativeTarget:
    """A declared native target with verified bytes or pinned absence."""

    native_path: str
    raw: bytes | None


@dataclass(frozen=True)
class VerifiedNativeContext:
    """Immutable verified bytes for an explicitly declared target set."""

    manifest_sha256: str
    source_group: str
    revision: str
    inventory_sha256: str
    sources: tuple[NativeSource, ...]
    targets: tuple[NativeTarget, ...]


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NativeContextError(f"invalid {label}")
    return value


def _hash(value: Any, length: int, label: str) -> str:
    text = _text(value, label)
    if re.fullmatch(f"[0-9a-f]{{{length}}}", text) is None:
        raise NativeContextError(f"invalid {label}")
    return text


def _keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise NativeContextError(f"invalid {label} fields")
    return value


def _canonical_path(value: Any) -> str:
    name = _text(value, "path")
    path = PurePosixPath(name)
    if (
        not path.parts
        or path.is_absolute()
        or path.as_posix() != name
        or any(part in {".", "..", ".git"} for part in path.parts)
        or "\\" in name
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
    ):
        raise NativeContextError(f"noncanonical or escaping path: {name!r}")
    return name


def _target_path(value: Any) -> str:
    name = _canonical_path(value)
    if PurePosixPath(name).suffix.lower() not in {".md", ".markdown"}:
        raise NativeContextError("declared target requires a Markdown path")
    return name


def _cache_path(root: Path, name: Any) -> Path:
    name = _canonical_path(name)
    path = root
    for component in PurePosixPath(name).parts:
        path /= component
        if path.is_symlink():
            raise NativeContextError(f"cache path contains a symlink: {name}")
    try:
        if not path.resolve().is_relative_to(root):
            raise NativeContextError(f"cache path escapes its root: {name}")
    except (OSError, RuntimeError) as exc:
        raise NativeContextError(f"invalid cache path: {name}") from exc
    return path


def _cache_root(root: Path) -> Path:
    if root.is_symlink() or not root.is_dir():
        raise NativeContextError("cache root requires a directory without a symlink")
    return root.resolve()


def _read_cache_file(root: Path, name: str) -> bytes:
    _cache_path(root, name)
    if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        raise NativeContextError(
            "confined cache reads are unsupported on this platform"
        )
    descriptors = []
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptors.append(os.open(root, directory_flags))
        parts = PurePosixPath(name).parts
        for component in parts[:-1]:
            descriptors.append(
                os.open(component, directory_flags, dir_fd=descriptors[-1])
            )
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=descriptors[-1],
        )
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise NativeContextError(f"cache path is not a regular file: {name}")
            return stream.read()
    except OSError as exc:
        raise NativeContextError(f"unreadable confined cache path: {name}") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _git_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment.update(
        GIT_NO_LAZY_FETCH="1",
        GIT_NO_REPLACE_OBJECTS="1",
        GIT_TERMINAL_PROMPT="0",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
    )
    return environment


def _git(repository: Path, arguments: list[str], *, missing_ok: bool = False) -> bytes:
    try:
        result = subprocess.run(
            [  # noqa: S607 - installed offline object reader
                "git",
                "--no-replace-objects",
                "-c",
                "protocol.allow=never",
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(repository),
                *arguments,
            ],
            env=_git_environment(),
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise NativeContextError("offline Git object reader is unavailable") from exc
    if result.returncode == 0 or (missing_ok and result.returncode == 1):
        return result.stdout
    raise NativeContextError(
        f"offline Git object/inventory operation failed: {arguments[0]}"
    )


def _git_object_id(kind: str, raw: bytes) -> str:
    header = f"{kind} {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw, usedforsecurity=False).hexdigest()


def _object(repository: Path, kind: str, identity: str) -> bytes:
    raw = _git(repository, ["cat-file", kind, identity])
    if _git_object_id(kind, raw) != identity:
        raise NativeContextError(f"Git {kind} object identity differs: {identity}")
    return raw


def _inventory(repository: Path, revision: str) -> list[dict[str, str]]:
    promisor = _git(
        repository,
        [
            "config",
            "--get-regexp",
            r"^(extensions\.partialclone|remote\..*\.promisor)$",
        ],
        missing_ok=True,
    )
    if promisor:
        raise NativeContextError("partial or promisor repositories are unsupported")
    commit = _object(repository, "commit", revision)
    tree_match = re.match(rb"tree ([0-9a-f]{40})\n", commit)
    if tree_match is None:
        raise NativeContextError("pinned Git commit has no supported root tree")
    root_tree = tree_match[1].decode("ascii")
    _object(repository, "tree", root_tree)
    raw = _git(repository, ["ls-tree", "-r", "-t", "-z", "--full-tree", revision])
    if raw and not raw.endswith(b"\0"):
        raise NativeContextError("incomplete Git inventory output")
    entries = []
    seen_paths: set[str] = set()
    verified_trees = {root_tree}
    for row in raw.split(b"\0")[:-1]:
        try:
            metadata, native = row.split(b"\t", 1)
            mode, kind, identity = metadata.decode("ascii").split(" ")
            name = _canonical_path(native.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise NativeContextError("unsupported Git inventory entry") from exc
        expected_kind = {
            "040000": "tree",
            "100644": "blob",
            "100755": "blob",
            "120000": "blob",
            "160000": "commit",
        }.get(mode)
        if kind != expected_kind or name in seen_paths:
            raise NativeContextError("invalid or duplicate Git inventory entry")
        _hash(identity, 40, "Git inventory object identity")
        seen_paths.add(name)
        if kind == "tree" and identity not in verified_trees:
            _object(repository, "tree", identity)
            verified_trees.add(identity)
        entries.append({"path": name, "mode": mode, "object_id": identity})
    return sorted(entries, key=lambda item: item["path"])


def _inventory_hash(entries: list[dict[str, str]]) -> str:
    raw = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _native_blob(inventory: dict[str, dict[str, str]], name: str) -> str | None:
    parts = PurePosixPath(name).parts
    for length in range(1, len(parts) + 1):
        ancestor = inventory.get("/".join(parts[:length]))
        if ancestor is None:
            continue
        if ancestor["mode"] in {"120000", "160000"}:
            raise NativeContextError(
                "native symlink or submodule ancestry is unsupported"
            )
        if length < len(parts) and ancestor["mode"] != "040000":
            raise NativeContextError("native path has a non-directory ancestor")
    entry = inventory.get(name)
    if entry is None:
        return None
    if entry["mode"] not in {"100644", "100755"}:
        raise NativeContextError("native target is not a regular file")
    return entry["object_id"]


def _source_metadata(
    manifest: Path, source_group: str, revision: str, source_ids: Sequence[str]
) -> tuple[str, dict[str, dict[str, str]], set[str]]:
    _hash(revision, 40, "revision")
    _text(source_group, "source group")
    if (
        isinstance(source_ids, str)
        or not source_ids
        or any(not isinstance(identity, str) or not identity for identity in source_ids)
        or len(set(source_ids)) != len(source_ids)
    ):
        raise NativeContextError("source IDs require a nonempty unique selection")
    try:
        raw = manifest.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise NativeContextError("invalid source manifest metadata") from exc
    if (
        not isinstance(data, dict)
        or type(data.get("version")) is not int
        or data["version"] != 1
    ):
        raise NativeContextError("unsupported source manifest metadata version")
    rows = data.get("samples")
    if not isinstance(rows, list) or not rows:
        raise NativeContextError("source manifest metadata requires samples")
    records = {}
    group_found = False
    for row in rows:
        if not isinstance(row, dict):
            raise NativeContextError("invalid source manifest metadata record")
        identity = _text(row.get("id"), "source identity")
        if identity in records:
            raise NativeContextError("duplicate source identity in metadata")
        records[identity] = row
        if row.get("source_group") == source_group:
            group_found = True
            if row.get("split") != "development":
                raise NativeContextError("source group is not wholly development")
    if not group_found:
        raise NativeContextError("source group is absent from manifest metadata")
    selected = {}
    related_groups: set[tuple[str, str]] = set()
    for identity in source_ids:
        row = records.get(identity)
        if row is None:
            raise NativeContextError(
                f"source identity is absent from metadata: {identity}"
            )
        if row.get("split") != "development":
            raise NativeContextError("selected source is not development")
        if row.get("source_group") != source_group:
            raise NativeContextError("selected source group differs")
        if row.get("revision") != revision:
            raise NativeContextError("selected source revision differs")
        if row.get("format") != "markdown":
            raise NativeContextError("selected source requires native Markdown format")
        if row.get("review_status") != "unreviewed":
            raise NativeContextError(
                "source acquisition metadata must remain unreviewed"
            )
        for field in ("pair_group", "near_duplicate_group"):
            if row.get(field) is not None:
                related_groups.add((field, _text(row[field], field)))
        selected[identity] = {
            "native_path": _target_path(row.get("locator")),
            "cache_path": _canonical_path(row.get("path")),
            "sha256": _hash(row.get("sha256"), 64, "source SHA-256"),
        }
    reserved_paths = set()
    selected_hashes = {source["sha256"] for source in selected.values()}
    for row in records.values():
        if row.get("split") != "development" and any(
            row.get(field) == group for field, group in related_groups
        ):
            raise NativeContextError("related source group is not wholly development")
        if row.get("split") == "holdout":
            if (
                _hash(row.get("sha256"), 64, "holdout source SHA-256")
                in selected_hashes
            ):
                raise NativeContextError(
                    "selected source SHA-256 matches holdout metadata"
                )
            reserved_paths.add(_canonical_path(row.get("path")))
    return hashlib.sha256(raw).hexdigest(), selected, reserved_paths


def _source_bindings(
    selected: dict[str, dict[str, str]], inventory: dict[str, dict[str, str]]
) -> dict[str, dict[str, str]]:
    bindings = {}
    seen_native: set[str] = set()
    for identity, source in sorted(selected.items()):
        name = source["native_path"]
        blob_id = _native_blob(inventory, name)
        if blob_id is None or name in seen_native:
            raise NativeContextError(
                "native source is missing or duplicated in pinned inventory"
            )
        seen_native.add(name)
        bindings[identity] = {**source, "blob_id": blob_id}
    return bindings


def _target_bindings(
    declared: Mapping[str, Any], inventory: dict[str, dict[str, str]], *, frozen: bool
) -> dict[str, dict[str, str]]:
    if not isinstance(declared, Mapping):
        raise NativeContextError("declared targets must be a mapping")
    bindings = {}
    for name_value, value in sorted(declared.items()):
        name = _target_path(name_value)
        blob_id = _native_blob(inventory, name)
        if frozen:
            if not isinstance(value, dict):
                raise NativeContextError("invalid target binding")
            if value.get("status") == "absent":
                _keys(value, {"status"}, "absent target")
                cache_name = None
            else:
                _keys(
                    value,
                    {"status", "cache_path", "sha256", "blob_id"},
                    "present target",
                )
                if value["status"] != "present":
                    raise NativeContextError("invalid target binding status")
                cache_name = _canonical_path(value["cache_path"])
        else:
            cache_name = _canonical_path(value) if value is not None else None
        if blob_id is None:
            if cache_name is not None:
                raise NativeContextError(
                    "declared target is absent from pinned inventory"
                )
            bindings[name] = {"status": "absent"}
        elif cache_name is None:
            raise NativeContextError("present native target requires cached bytes")
        else:
            binding = {
                "status": "present",
                "cache_path": cache_name,
                "blob_id": blob_id,
            }
            if frozen:
                if value["blob_id"] != blob_id:
                    raise NativeContextError(
                        "target blob differs from pinned inventory"
                    )
                binding["sha256"] = _hash(value["sha256"], 64, "target SHA-256")
            bindings[name] = binding
    return bindings


def _verify_bytes(
    root: Path,
    sources: dict[str, dict[str, str]],
    targets: dict[str, dict[str, str]],
    reserved_paths: set[str],
    metadata_guard: Callable[[], None] | None = None,
) -> tuple[tuple[NativeSource, ...], tuple[NativeTarget, ...]]:
    for binding in [*sources.values(), *targets.values()]:
        if "cache_path" in binding:
            if binding["cache_path"] in reserved_paths:
                raise NativeContextError("cache path names reserved holdout material")
            _cache_path(root, binding["cache_path"])
    source_bytes = []
    for identity, binding in sources.items():
        if metadata_guard is not None:
            metadata_guard()
        raw = _read_cache_file(root, binding["cache_path"])
        if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
            raise NativeContextError("source SHA-256 differs from frozen metadata")
        if _git_object_id("blob", raw) != binding["blob_id"]:
            raise NativeContextError("source bytes differ from pinned native blob")
        source_bytes.append(NativeSource(identity, binding["native_path"], raw))
    target_bytes = []
    for name, binding in targets.items():
        if binding["status"] == "absent":
            target_bytes.append(NativeTarget(name, None))
            continue
        if metadata_guard is not None:
            metadata_guard()
        raw = _read_cache_file(root, binding["cache_path"])
        digest = hashlib.sha256(raw).hexdigest()
        if "sha256" in binding and digest != binding["sha256"]:
            raise NativeContextError("target SHA-256 differs from frozen binding")
        if _git_object_id("blob", raw) != binding["blob_id"]:
            raise NativeContextError("target bytes differ from pinned native blob")
        binding["sha256"] = digest
        target_bytes.append(NativeTarget(name, raw))
    return tuple(source_bytes), tuple(target_bytes)


def build_native_context(
    manifest: Path,
    corpus_root: Path,
    repository: Path,
    *,
    revision: str,
    source_group: str,
    source_ids: Sequence[str],
    targets: Mapping[str, str | None],
) -> dict[str, Any]:
    """Build bindings for declared targets after development metadata checks."""
    manifest_hash, selected, reserved_paths = _source_metadata(
        manifest, source_group, revision, source_ids
    )
    root = _cache_root(corpus_root)
    entries = _inventory(repository, revision)
    inventory = {entry["path"]: entry for entry in entries}
    sources = _source_bindings(selected, inventory)
    target_bindings = _target_bindings(targets, inventory, frozen=False)
    _verify_bytes(root, sources, target_bindings, reserved_paths)
    return {
        "version": 1,
        "target_scope": "explicitly-declared",
        "manifest_sha256": manifest_hash,
        "source_group": source_group,
        "revision": revision,
        "inventory": entries,
        "inventory_sha256": _inventory_hash(entries),
        "sources": sources,
        "targets": target_bindings,
    }


def validate_native_context(
    bundle: Mapping[str, Any],
    manifest: Path,
    corpus_root: Path,
    repository: Path,
    *,
    metadata_guard: Callable[[], None] | None = None,
) -> VerifiedNativeContext:
    """Reprove frozen metadata, complete trees and declared target bytes."""
    data = _keys(
        bundle,
        {
            "version",
            "target_scope",
            "manifest_sha256",
            "source_group",
            "revision",
            "inventory",
            "inventory_sha256",
            "sources",
            "targets",
        },
        "native context bundle",
    )
    if (
        type(data["version"]) is not int
        or data["version"] != 1
        or data["target_scope"] != "explicitly-declared"
    ):
        raise NativeContextError("unsupported native context bundle version or scope")
    source_group = _text(data["source_group"], "source group")
    revision = _hash(data["revision"], 40, "revision")
    if not isinstance(data["sources"], dict):
        raise NativeContextError("invalid source bindings")
    manifest_hash, selected, reserved_paths = _source_metadata(
        manifest, source_group, revision, tuple(data["sources"])
    )
    if manifest_hash != _hash(data["manifest_sha256"], 64, "manifest SHA-256"):
        raise NativeContextError("source manifest SHA-256 differs from frozen binding")
    entries = _inventory(repository, revision)
    inventory_hash = _inventory_hash(entries)
    if data["inventory"] != entries or data["inventory_sha256"] != inventory_hash:
        raise NativeContextError(
            "complete pinned inventory differs from frozen binding"
        )
    inventory = {entry["path"]: entry for entry in entries}
    sources = _source_bindings(selected, inventory)
    if data["sources"] != sources:
        raise NativeContextError(
            "native source paths, SHA-256 or blobs differ from metadata"
        )
    targets = _target_bindings(data["targets"], inventory, frozen=True)
    source_bytes, target_bytes = _verify_bytes(
        _cache_root(corpus_root), sources, targets, reserved_paths, metadata_guard
    )
    return VerifiedNativeContext(
        manifest_hash,
        source_group,
        revision,
        inventory_hash,
        source_bytes,
        target_bytes,
    )


@contextmanager
def materialize_native_context(context: VerifiedNativeContext) -> Iterator[Path]:
    """Create and remove a private tree from immutable verified bytes."""
    files: dict[str, bytes] = {}
    absent = []
    items: tuple[NativeSource | NativeTarget, ...] = (
        *context.sources,
        *context.targets,
    )
    for item in items:
        name = _target_path(item.native_path)
        if item.raw is None:
            absent.append(name)
            continue
        if name in files and files[name] != item.raw:
            raise NativeContextError("conflicting verified native bytes")
        files[name] = item.raw
    with TemporaryDirectory(prefix="proseprobe-native-") as directory:
        root = Path(directory)
        for name, raw in sorted(files.items()):
            path = root / name
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as stream:
                    stream.write(raw)
            except OSError as exc:
                raise NativeContextError("private native namespace collision") from exc
        if any((root / name).exists() for name in absent):
            raise NativeContextError("declared absent target exists in private tree")
        yield root
