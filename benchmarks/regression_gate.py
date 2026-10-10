"""Validate frozen reviewed mismatch records and compare exact regressions."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from benchmarks.evaluation_identity import rule_contract_snapshot
from benchmarks.quality_scoring import (
    ActualFinding,
    AnnotationError,
    Annotations,
    ExpectedFinding,
    QualityScore,
    _keys,
    _location,
    _mapping,
    _positive_int,
    _sha256,
    _text,
)
from proseprobe.config import Config
from proseprobe.core.linter import Linter
from proseprobe.rules.base import Rule


def policy_identity(config: Config, root: Path) -> dict[str, Any]:
    """Describe effective settings with root-relative configured filesystem paths."""

    def normalize(value: Any) -> Any:
        if isinstance(value, Path):
            path = value.resolve()
            return (
                {"root_relative": path.relative_to(root.resolve()).as_posix()}
                if path.is_relative_to(root.resolve())
                else {"absolute": str(path)}
            )
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        return value

    values = asdict(config)
    values.pop("source_path")
    if values.get("project_root") is not None:
        values["project_root"] = Path(values["project_root"])
    return normalize(values)


def _identity(row: dict[str, Any]) -> str:
    return json.dumps(
        {
            key: row[key]
            for key in (
                "kind",
                "path",
                "rule_id",
                "line",
                "column",
                "end_line",
                "end_column",
                "label_id",
            )
        },
        sort_keys=True,
    )


def mismatch_row(kind: str, finding: ActualFinding | ExpectedFinding) -> dict[str, Any]:
    """Keep source endpoints and stable expected identities without count allowances."""
    return {
        "kind": kind,
        "path": finding.path,
        "rule_id": finding.rule_id,
        "line": finding.line,
        "column": finding.column,
        "end_line": (finding.end_line or finding.line)
        if finding.end_column is not None
        else None,
        "end_column": finding.end_column,
        "label_id": finding.identity if isinstance(finding, ExpectedFinding) else "",
    }


def load_gate_record(
    path: Path,
    annotations: Annotations,
    manifest: Path,
    root: Path,
    mode: str,
    config: Config,
    rules: list[Rule],
) -> dict[str, Any]:
    """Reject stale source, annotation, declared-contract or policy bindings."""
    try:
        record = _mapping(json.loads(path.read_text(encoding="utf-8")), "gate")
    except (OSError, json.JSONDecodeError) as exc:
        raise AnnotationError(
            f"{path}: invalid or unreadable gate JSON: {exc}"
        ) from exc
    _keys(
        record,
        required={
            "version",
            "name",
            "mode",
            "policy",
            "annotation_contract",
            "corpus",
            "rule_contracts",
            "created_runtime",
            "mismatches",
        },
        context="gate",
    )
    if type(record["version"]) is not int or record["version"] != 1:
        raise AnnotationError("unsupported regression gate version")
    _text(record["name"], "gate.name")
    if record["mode"] != mode or record["policy"] != policy_identity(config, root):
        raise AnnotationError(
            "gate effective policy differs from the requested evaluation policy"
        )
    contract = _text(record["annotation_contract"], "gate.annotation_contract")
    if contract not in {"legacy-exhaustive-v1", "source-bound-v3"}:
        raise AnnotationError("unsupported gate annotation contract")
    corpus = _mapping(record["corpus"], "gate.corpus")
    _keys(corpus, required={"manifest_sha256", "files"}, context="gate.corpus")
    expected_hash = _sha256(corpus["manifest_sha256"], "gate.corpus.manifest_sha256")
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != expected_hash:
        raise AnnotationError("gate annotation snapshot SHA-256 differs")
    annotation_version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    if annotation_version != (1 if contract == "legacy-exhaustive-v1" else 3):
        raise AnnotationError(
            "gate annotation contract does not match the manifest version"
        )
    file_hashes = _mapping(corpus["files"], "gate.corpus.files")
    actual_hashes = {
        path.resolve().relative_to(root.resolve()).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in annotations.files
    }
    for relative, digest in file_hashes.items():
        _sha256(digest, f"gate.corpus.files.{relative}")
    if file_hashes != actual_hashes:
        raise AnnotationError(
            "gate source SHA-256 bindings differ from evaluated sources"
        )
    rule_ids = {rule.id for rule in rules}
    if record["rule_contracts"] != rule_contract_snapshot(rule_ids):
        raise AnnotationError(
            "gate declared rule contracts differ; review contract migration"
        )
    runtime = _mapping(record["created_runtime"], "gate.created_runtime")
    _keys(
        runtime,
        required={
            "package_version",
            "source_sha256",
            "source_files_count",
            "source_files",
            "identity_scope",
            "source_roots",
            "git",
        },
        context="gate.created_runtime",
    )
    _sha256(runtime["source_sha256"], "gate.created_runtime.source_sha256")
    _text(runtime["package_version"], "gate.created_runtime.package_version")
    _text(runtime["identity_scope"], "gate.created_runtime.identity_scope")
    source_count = _positive_int(
        runtime["source_files_count"], "gate.created_runtime.source_files_count"
    )
    source_files = runtime["source_files"]
    if (
        not isinstance(source_files, list)
        or len(source_files) != source_count
        or any(not isinstance(name, str) or not name.strip() for name in source_files)
        or len(set(source_files)) != source_count
    ):
        raise AnnotationError(
            "gate.created_runtime source file names/count are inconsistent"
        )
    source_roots = _mapping(
        runtime["source_roots"], "gate.created_runtime.source_roots"
    )
    _keys(
        source_roots,
        required={"package", "evaluator"},
        context="gate.created_runtime.source_roots",
    )
    for key, value in source_roots.items():
        _text(value, f"gate.created_runtime.source_roots.{key}")
    git = _mapping(runtime["git"], "gate.created_runtime.git")
    _keys(
        git,
        required={
            "head",
            "tracked_worktree_dirty",
            "staged_dirty",
            "untracked_python_files",
            "scope",
        },
        context="gate.created_runtime.git",
    )
    if any(
        git[key] is not None and type(git[key]) is not bool
        for key in ("tracked_worktree_dirty", "staged_dirty")
    ):
        raise AnnotationError(
            "gate.created_runtime Git dirty states must be booleans or null"
        )
    if git["head"] is not None:
        _text(git["head"], "gate.created_runtime.git.head")
    for key in ("scope", "untracked_python_files"):
        values = git[key]
        if values is None and key == "untracked_python_files":
            continue
        if (
            not isinstance(values, list)
            or any(not isinstance(value, str) or not value.strip() for value in values)
            or len(set(values)) != len(values)
        ):
            raise AnnotationError(
                f"gate.created_runtime.git.{key} must contain unique names"
            )
    if not isinstance(record["mismatches"], list):
        raise AnnotationError("gate.mismatches must be a list")
    seen = set()
    for index, value in enumerate(record["mismatches"]):
        context = f"gate.mismatches[{index}]"
        row = _mapping(value, context)
        _keys(
            row,
            required={
                "kind",
                "path",
                "rule_id",
                "line",
                "column",
                "end_line",
                "end_column",
                "label_id",
                "reason",
            },
            context=context,
        )
        kind = _text(row["kind"], f"{context}.kind")
        rule_id = _text(row["rule_id"], f"{context}.rule_id")
        relative = _text(row["path"], f"{context}.path")
        if kind not in {"fp", "fn"} or rule_id not in rule_ids:
            raise AnnotationError(f"{context}: unknown mismatch kind or rule")
        if relative not in actual_hashes:
            raise AnnotationError(f"{context}: source is not bound by the gate")
        _text(row["reason"], f"{context}.reason")
        label_id = _text(row["label_id"], f"{context}.label_id", allow_empty=True)
        if row["end_column"] is not None and row["end_line"] is None:
            raise AnnotationError(
                f"{context}: full source spans require explicit end_line"
            )
        if row["kind"] == "fp" and (label_id or row["end_column"] is None):
            raise AnnotationError(
                f"{context}: false positives require a full source span and no expected label"
            )
        lines = (root / row["path"]).read_bytes().decode("utf-8").splitlines()
        location = {"line": row["line"], "column": row["column"]} | {
            key: row[key] for key in ("end_line", "end_column") if row[key] is not None
        }
        _location(
            location,
            lines,
            context,
            column_required=True,
            allow_zero=row["rule_id"] == "M004",
        )
        if row["kind"] == "fn" and not any(
            mismatch_row("fn", item)
            == {key: row[key] for key in mismatch_row("fn", item)}
            for item in annotations.expected
        ):
            raise AnnotationError(
                f"{context}: false negative does not identify an expected label"
            )
        key = _identity(row)
        if key in seen:
            raise AnnotationError(f"{context}: duplicate mismatch identity")
        seen.add(key)
    return record


def require_complete_review(
    annotations: Annotations,
    root: Path,
    linter: Linter,
    rules: list[Rule],
    contract: str,
) -> None:
    """Refuse eligible unknown regions independently of emitted predictions."""
    if contract == "legacy-exhaustive-v1":
        if annotations.scopes is not None:
            raise AnnotationError(
                "legacy gate coverage requires the exhaustive version-one curated contract"
            )
        return
    if linter.config.local_links:
        raise AnnotationError(
            "strict source-bound evaluation cannot enable local_links: native target paths/bytes are not bound"
        )
    if annotations.source_binding != "sha256-utf8":
        raise AnnotationError(
            "independent gate coverage requires source-bound version-three annotations"
        )
    scopes = annotations.scopes or ()
    discovered = set(linter.discover_files(list(annotations.files)))
    verified = dict(annotations.verified_sources)
    gaps = []
    for path in annotations.files:
        if path not in discovered:
            continue
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        source_bytes = verified[relative] if relative in verified else path.read_bytes()
        lines = source_bytes.decode("utf-8").splitlines()
        end = (len(lines), len(lines[-1]) + 1) if lines else (1, 1)
        for rule in rules:
            if not linter._rule_enabled(rule, path):
                continue
            matching = [
                scope
                for scope in scopes
                if scope.path == relative and rule.id in scope.rules
            ]
            whole = any(
                scope.status == "reviewed" and scope.span is None for scope in matching
            )
            cursor = (1, 1)
            spans = sorted(
                (
                    scope.span
                    for scope in matching
                    if scope.status == "reviewed" and scope.span is not None
                ),
                key=lambda span: (span.line, span.column),
            )
            for span in spans:
                if (span.line, span.column) > cursor:
                    break
                cursor = max(cursor, (span.end_line, span.end_column))
            if any(scope.status != "reviewed" for scope in matching) or not (
                whole or (spans and cursor >= end)
            ):
                gaps.append(f"{relative}:{rule.id}")
    if gaps:
        raise AnnotationError(
            "strict gate requires complete eligible review coverage: "
            + ", ".join(sorted(gaps))
        )


def bind_gate_sources(
    annotations: Annotations, record: dict[str, Any], root: Path
) -> Annotations:
    """Use the frozen ledger's exact verified bytes for legacy regression scans."""
    if annotations.verified_sources:
        return annotations
    sources = tuple(
        (relative, (root / relative).read_bytes())
        for relative in sorted(record["corpus"]["files"])
    )
    if any(
        hashlib.sha256(raw).hexdigest() != record["corpus"]["files"][relative]
        for relative, raw in sources
    ):
        raise AnnotationError("gate source SHA-256 changed during input collection")
    return replace(
        annotations,
        source_identities={
            relative: {
                "source_id": f"regression-ledger:{relative}",
                "sha256": record["corpus"]["files"][relative],
            }
            for relative, _raw in sources
        },
        verified_sources=sources,
    )


def compare_gate(record: dict[str, Any], score: QualityScore) -> dict[str, Any]:
    """Allow exact reviewed mismatches while exposing new and resolved identities."""
    known = {_identity(row): row for row in record["mismatches"]}
    actual = [mismatch_row("fp", item.finding) for item in score.false_positives] + [
        mismatch_row("fn", item) for item in score.false_negatives
    ]
    counts: Counter[str] = Counter()
    new = []
    matched = 0
    for row in sorted(actual, key=_identity):
        key = _identity(row)
        counts[key] += 1
        if key in known and counts[key] == 1:
            matched += 1
        else:
            new.append(row)
    return {
        "passed": not new,
        "name": record["name"],
        "known_mismatches_count": matched,
        "new_mismatches": new,
        "resolved_mismatches": [known[key] for key in sorted(known) if not counts[key]],
        "source_binding": "frozen-regression-ledger",
        "effectiveness_claim": "curated regression only; no independent population claim",
    }
