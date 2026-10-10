"""Offline identities for reviewed material and the implementation evaluating it."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import proseprobe
from proseprobe import __version__
from proseprobe.rules import get_rule_metadata


def diagnostic_sha256(finding: dict[str, Any]) -> str:
    """Bind a complete diagnostic regardless of JSON member order."""
    raw = json.dumps(
        finding, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def rule_contract_snapshot(rule_ids: set[str] | None = None) -> dict[str, Any]:
    """Capture canonical declared rule contracts separately from implementation."""
    contracts = {}
    for metadata in get_rule_metadata():
        if rule_ids is not None and metadata.id not in rule_ids:
            continue
        record = asdict(metadata)
        record["default_severity"] = metadata.default_severity.value
        record["default_confidence"] = metadata.default_confidence.value
        record["applies_to"] = list(metadata.applies_to)
        record["profiles"] = list(metadata.profiles)
        contracts[metadata.id] = record
    return {"version": 1, "rules": contracts}


def _git(root: Path, arguments: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],  # noqa: S607 - installed Git
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def _python_names(names: str | None) -> list[str] | None:
    if names is None:
        return None
    return sorted(
        name
        for name in names.split("\0")
        if name.endswith(".py") and "__pycache__" not in Path(name).parts
    )


def runtime_identity(
    package_root: Path | None = None, evaluator_root: Path | None = None
) -> dict[str, Any]:
    """Hash source names and bytes at actual module locations, independent of checkout path."""
    package_root = (package_root or Path(proseprobe.__file__).parent).resolve()
    evaluator_root = (evaluator_root or Path(__file__).parent).resolve()
    roots = {"package": package_root, "evaluator": evaluator_root}
    digest = hashlib.sha256()
    names = []
    for role, root in sorted(roots.items()):
        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(root)
            if "__pycache__" in relative.parts:
                continue
            name = f"{role}/{relative.as_posix()}"
            raw = path.read_bytes()
            digest.update(name.encode() + b"\0" + str(len(raw)).encode() + b"\0" + raw)
            names.append(name)
    git: dict[str, Any] = {
        "head": None,
        "tracked_worktree_dirty": None,
        "staged_dirty": None,
        "untracked_python_files": None,
        "scope": [],
    }
    checkout = _git(package_root, ["rev-parse", "--show-toplevel"])
    if checkout:
        root = Path(checkout.strip()).resolve()
        scope = sorted(
            {
                path.relative_to(root).as_posix()
                for path in roots.values()
                if path.is_relative_to(root)
            }
        )
        head = _git(root, ["rev-parse", "HEAD"])
        unstaged = _git(root, ["diff", "--name-only", "-z", "--", *scope])
        staged = _git(root, ["diff", "--cached", "--name-only", "-z", "--", *scope])
        untracked = _git(root, ["ls-files", "--others", "-z", "--", *scope])
        git = {
            "head": head.strip() if head else None,
            "tracked_worktree_dirty": bool(_python_names(unstaged))
            if unstaged is not None
            else None,
            "staged_dirty": bool(_python_names(staged)) if staged is not None else None,
            "untracked_python_files": _python_names(untracked),
            "scope": scope,
        }
    return {
        "package_version": __version__,
        "source_sha256": digest.hexdigest() if names else None,
        "source_files_count": len(names),
        "source_files": names,
        "identity_scope": "package and evaluator Python source names and exact bytes; caches, corpora and documents excluded",
        "source_roots": {role: str(root) for role, root in roots.items()},
        "git": git,
    }
