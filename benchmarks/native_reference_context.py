"""Prove supported native Markdown references before local-link evaluation.

The production static parser and resolver define reference eligibility. Images,
unused definitions, remote URLs, queries, absolute paths, non-Markdown targets,
and escaping paths retain that rule's exclusions. Generated source markup is
unsupported. No renderer expansion, remote fetch, or target recursion occurs.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from benchmarks.native_link_context import (
    NativeContextError,
    NativeSource,
    NativeTarget,
    VerifiedNativeContext,
    _source_metadata,
    _target_path,
    materialize_native_context,
    validate_native_context,
)
from benchmarks.quality_scoring import (
    AnnotationError,
    Annotations,
    _keys,
    _mapping,
    _review_header,
    _sha256,
    _text,
)
from proseprobe.rules.markup import LocalMarkdownLinkRule, SameDocumentFragmentRule

REFERENCE_SCOPE = "production-static-local-markdown-v1"


@dataclass(frozen=True)
class NativeReference:
    """One supported destination at its original source coordinates."""

    destination: str
    line: int
    column: int
    end_column: int
    native_path: str
    fragment: str


@dataclass(frozen=True)
class ExcludedDestination:
    """An extracted destination outside the production local-link contract."""

    destination: str
    line: int
    column: int
    end_column: int
    reason: str = "production-resolver-exclusion"


@dataclass(frozen=True)
class VerifiedReferenceContext:
    """Verified immutable native bytes and complete supported reference maps."""

    native: VerifiedNativeContext
    renderer: str
    references: tuple[tuple[str, tuple[NativeReference, ...]], ...]
    excluded: tuple[tuple[str, tuple[ExcludedDestination, ...]], ...]


def _renderer(value: Any) -> str:
    if not isinstance(value, str) or value not in {"off", "github"}:
        raise NativeContextError("unsupported native Markdown renderer")
    return str(value)


def native_markdown_text(raw: bytes) -> str:
    """Parse LF or CRLF source lines without changing their original byte binding."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise NativeContextError(
            "native source or target is not UTF-8 Markdown"
        ) from exc
    if "\r" in text.replace("\r\n", ""):
        raise NativeContextError("bare-CR native Markdown line endings are unsupported")
    return text.replace("\r\n", "\n")


def _enumerate(
    native: VerifiedNativeContext, renderer: str
) -> VerifiedReferenceContext:
    references = []
    excluded = []
    items: tuple[NativeSource | NativeTarget, ...] = (*native.sources, *native.targets)
    bound = {item.native_path: item.raw for item in items}
    with materialize_native_context(native) as root:
        root = root.resolve()
        resolver = LocalMarkdownLinkRule(True, str(root), renderer)
        for source in native.sources:
            document = SameDocumentFragmentRule._document(
                native_markdown_text(source.raw)
            )
            if document is None:
                raise NativeContextError("unsupported generated native source context")
            source_references = []
            source_excluded = []
            for destination, line, column, end_column in sorted(
                document[1], key=lambda item: (item[1], item[2], item[3], item[0])
            ):
                resolved = resolver._resolve_target(
                    root / source.native_path, destination
                )
                if resolved is None:
                    source_excluded.append(
                        ExcludedDestination(destination, line, column, end_column)
                    )
                    continue
                target, fragment = resolved
                name = target.relative_to(root).as_posix()
                if name not in bound:
                    raise NativeContextError(
                        f"required native target is not bound: {name}"
                    )
                raw = bound[name]
                if raw is not None:
                    content = native_markdown_text(raw)
                    if (
                        fragment
                        and renderer == "github"
                        and SameDocumentFragmentRule._document(content) is None
                    ):
                        raise NativeContextError(
                            f"unsupported generated native fragment target: {name}"
                        )
                source_references.append(
                    NativeReference(
                        destination, line, column, end_column, name, fragment
                    )
                )
            references.append((source.source_id, tuple(source_references)))
            excluded.append((source.source_id, tuple(source_excluded)))
    return VerifiedReferenceContext(
        native, renderer, tuple(references), tuple(excluded)
    )


def _reference_maps(
    context: VerifiedReferenceContext,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        {
            identity: [asdict(item) for item in rows]
            for identity, rows in context.references
        },
        {
            identity: [asdict(item) for item in rows]
            for identity, rows in context.excluded
        },
    )


def build_reference_context(
    native_bundle: Mapping[str, Any],
    manifest: Path,
    corpus_root: Path,
    repository: Path,
    *,
    renderer: str,
) -> dict[str, Any]:
    """Extend declared native evidence with complete supported reference maps."""
    renderer = _renderer(renderer)
    native = validate_native_context(native_bundle, manifest, corpus_root, repository)
    context = _enumerate(native, renderer)
    references, excluded = _reference_maps(context)
    return {
        "version": 2,
        "reference_scope": REFERENCE_SCOPE,
        "renderer": renderer,
        "native_context": dict(native_bundle),
        "references": references,
        "excluded_destinations": excluded,
    }


def validate_reference_context(
    bundle: Mapping[str, Any],
    manifest: Path,
    corpus_root: Path,
    repository: Path,
    *,
    metadata_guard: Callable[[], None] | None = None,
) -> VerifiedReferenceContext:
    """Recompute frozen reference closure from verified immutable native bytes."""
    _validate_reference_schema(bundle)
    renderer = _renderer(bundle["renderer"])
    native = validate_native_context(
        bundle["native_context"],
        manifest,
        corpus_root,
        repository,
        metadata_guard=metadata_guard,
    )
    context = _enumerate(native, renderer)
    references, excluded = _reference_maps(context)
    if json.dumps(bundle["references"], sort_keys=True) != json.dumps(
        references, sort_keys=True
    ) or json.dumps(bundle["excluded_destinations"], sort_keys=True) != json.dumps(
        excluded, sort_keys=True
    ):
        raise NativeContextError(
            "complete native reference map differs from frozen evidence"
        )
    return context


def _validate_reference_schema(bundle: Mapping[str, Any]) -> None:
    if (
        not isinstance(bundle, dict)
        or set(bundle)
        != {
            "version",
            "reference_scope",
            "renderer",
            "native_context",
            "references",
            "excluded_destinations",
        }
        or type(bundle.get("version")) is not int
        or bundle["version"] != 2
        or bundle["reference_scope"] != REFERENCE_SCOPE
    ):
        raise NativeContextError("unsupported complete native reference context")
    _renderer(bundle["renderer"])


def preflight_native_review(
    manifest_path: Path, source_manifest: Path | None
) -> tuple[str, dict[str, Any]] | None:
    """Check native review development metadata before any packet or cache source."""
    try:
        raw = manifest_path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return None
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("review"), dict)
        or "native_context" not in data["review"]
    ):
        return None
    if source_manifest is None:
        raise AnnotationError(
            "bound review requires all offline native context validation inputs"
        )
    _keys(
        data, required={"version", "review", "files"}, context="native review manifest"
    )
    if type(data["version"]) is not int or data["version"] != 3:
        raise AnnotationError("native review requires version-three annotations")
    _header, index, bundle = _review_header(data["review"], manifest_path.parent)
    assert bundle is not None
    _validate_reference_schema(bundle)
    native = _mapping(bundle["native_context"], "native context metadata")
    source_bindings = _mapping(native.get("sources"), "native source bindings")
    manifest_hash, selected, reserved_paths = _source_metadata(
        source_manifest,
        _text(native.get("source_group"), "native source group"),
        _text(native.get("revision"), "native revision"),
        tuple(source_bindings),
    )
    if native.get("manifest_sha256") != manifest_hash:
        raise NativeContextError(
            "source manifest SHA-256 differs from frozen native binding"
        )
    for identity, source in selected.items():
        binding = _mapping(source_bindings[identity], "native source metadata")
        if (
            any(binding.get(key) != value for key, value in source.items())
            or binding.get("cache_path") in reserved_paths
        ):
            raise NativeContextError(
                "native source metadata differs from development acquisition"
            )
    files = _mapping(data["files"], "native reviewed files")
    if not files or set(files) != set(index["files"]):
        raise AnnotationError("reviewed and indexed native source paths differ")
    identities = set()
    for relative, value in files.items():
        _target_path(relative)
        entry = _mapping(value, "native reviewed file")
        identity = _text(entry.get("source_id"), "native reviewed source ID")
        checksum = _sha256(entry.get("sha256"), "native reviewed source SHA-256")
        binding = {"source_id": identity, "sha256": checksum}
        if index["files"].get(relative) != binding:
            raise AnnotationError(
                "reviewed source binding differs from frozen packet index"
            )
        if identity in identities or identity not in selected:
            raise AnnotationError("reviewed and native source identities differ")
        identities.add(identity)
        context = index.get("context", {}).get(relative)
        if (
            not isinstance(context, dict)
            or context.get("split") != "development"
            or context.get("format") != "markdown"
        ):
            raise AnnotationError("native packet context must be development Markdown")
        if checksum != selected[identity]["sha256"]:
            raise AnnotationError("reviewed and native source SHA-256 bindings differ")
        if (
            entry.get("source_group") != native["source_group"]
            or context.get("source_group") != native["source_group"]
        ):
            raise AnnotationError("reviewed and native source groups differ")
    if identities != selected.keys():
        raise AnnotationError("reviewed and native source identities differ")
    return hashlib.sha256(raw).hexdigest(), bundle


def annotation_native_sources(
    annotations: Annotations, context: VerifiedReferenceContext
) -> dict[str, tuple[str, bytes]]:
    """Bind reviewed packet paths to exact native source identities and bytes."""
    if annotations.source_binding != "sha256-utf8":
        raise AnnotationError(
            "native evaluation requires source-bound version-three annotations"
        )
    native_sources = {source.source_id: source for source in context.native.sources}
    annotation_ids = {
        item["source_id"] for item in annotations.source_identities.values()
    }
    if annotation_ids != native_sources.keys():
        raise AnnotationError("reviewed and native source identities differ")
    result = {}
    for relative, binding in annotations.source_identities.items():
        source = native_sources[binding["source_id"]]
        if hashlib.sha256(source.raw).hexdigest() != binding["sha256"]:
            raise AnnotationError("reviewed and native source SHA-256 bindings differ")
        if annotations.source_groups.get(relative) != context.native.source_group:
            raise AnnotationError("reviewed and native source groups differ")
        result[relative] = (source.native_path, source.raw)
    return result


def reference_context_evidence(
    context: VerifiedReferenceContext, artifact_sha256: str
) -> dict[str, Any]:
    """Describe the verified renderer, inventory, closure and resolver exclusions."""
    return {
        "root": None,
        "enabled": True,
        "target_binding": "verified-native-reference-closure",
        "reason": None,
        "reference_scope": REFERENCE_SCOPE,
        "renderer": context.renderer,
        "artifact_sha256": artifact_sha256,
        "source_manifest_sha256": context.native.manifest_sha256,
        "source_group": context.native.source_group,
        "revision": context.native.revision,
        "inventory_sha256": context.native.inventory_sha256,
        "sources_count": len(context.native.sources),
        "targets_count": len(context.native.targets),
        "references_count": sum(len(rows) for _, rows in context.references),
        "excluded_destinations_count": sum(len(rows) for _, rows in context.excluded),
        "excluded_destinations": {
            identity: [asdict(item) for item in rows]
            for identity, rows in context.excluded
        },
    }
