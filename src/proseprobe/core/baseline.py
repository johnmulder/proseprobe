"""Versioned baseline support for tracking known issues."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from proseprobe.config import ConfigError
from proseprobe.rules.base import Issue

__all__ = [
    "Baseline",
    "BaselineComparison",
    "BaselineEntry",
    "filter_new_issues",
    "resolve_workspace",
]

_ENTRY_KEYS = frozenset({"context_hash", "match", "path", "rule_id"})
_MATCH_LIMIT = 80
_CONTEXT_RADIUS = 32


@dataclass(frozen=True, order=True)
class BaselineEntry:
    """Stable source identity for one known issue."""

    path: str
    rule_id: str
    match: str
    context_hash: str

    def to_dict(self) -> dict[str, str]:
        """Return the serialized entry in reviewable field order."""
        return {
            "path": self.path,
            "rule_id": self.rule_id,
            "match": self.match,
            "context_hash": self.context_hash,
        }

    @classmethod
    def from_dict(cls, value: Any, index: int) -> BaselineEntry:
        """Parse and strictly validate one serialized entry."""
        label = f"entries[{index}]"
        if not isinstance(value, dict) or set(value) != _ENTRY_KEYS:
            raise ValueError(
                f"{label} must contain exactly: {', '.join(sorted(_ENTRY_KEYS))}"
            )
        if not all(isinstance(value[key], str) for key in _ENTRY_KEYS):
            raise ValueError(f"{label} fields must be strings")

        path = value["path"]
        rule_id = value["rule_id"]
        match = value["match"]
        context_hash = value["context_hash"]
        if not path or Path(path).is_absolute():
            raise ValueError(f"{label}.path must be a non-empty relative path")
        if not re.fullmatch(r"[A-Z]\d{3}", rule_id):
            raise ValueError(f"{label}.rule_id must be an uppercase rule ID")
        if not match or len(match) > _MATCH_LIMIT:
            raise ValueError(
                f"{label}.match must contain 1 to {_MATCH_LIMIT} characters"
            )
        if not re.fullmatch(r"[0-9a-f]{16}", context_hash):
            raise ValueError(f"{label}.context_hash must be 16 lowercase hex digits")
        return cls(path, rule_id, match, context_hash)


@dataclass(frozen=True)
class BaselineComparison:
    """Current findings partitioned by their relationship to a baseline."""

    active: frozenset[BaselineEntry]
    stale: frozenset[BaselineEntry]
    new: frozenset[BaselineEntry]
    stale_legacy: int = 0

    @property
    def active_count(self) -> int:
        return len(self.active)

    @property
    def stale_count(self) -> int:
        return len(self.stale) + self.stale_legacy

    @property
    def new_count(self) -> int:
        return len(self.new)


class Baseline:
    """Manage known issue identities in baseline format 1 or 2."""

    def __init__(self, baseline_path: Path | None = None) -> None:
        self.baseline_path = baseline_path or Path(".proseprobe-baseline.json")
        self._entries: set[BaselineEntry] = set()
        self._legacy_fingerprints: set[str] = set()
        self._loaded = False
        self._format_version: int | None = None

    def load(self) -> bool:
        """Load a baseline, returning false only when the file does not exist."""
        if not self.baseline_path.exists():
            return False

        try:
            raw = self.baseline_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            self._load_data(data)
        except ConfigError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ConfigError(self.baseline_path, f"invalid baseline: {exc}") from exc

        self._loaded = True
        return True

    def _load_data(self, data: Any) -> None:
        if not isinstance(data, dict):
            raise ValueError("root must be an object")

        version = data.get("version")
        self._entries.clear()
        self._legacy_fingerprints.clear()
        if version == "1.0":
            if set(data) != {"version", "fingerprints"}:
                raise ValueError(
                    "version 1 must contain exactly version and fingerprints"
                )
            fingerprints = data["fingerprints"]
            if not isinstance(fingerprints, list) or not all(
                isinstance(item, str) for item in fingerprints
            ):
                raise ValueError("fingerprints must be a list of strings")
            self._legacy_fingerprints = set(fingerprints)
            self._format_version = 1
            return

        if version != 2:
            raise ValueError(f"unsupported baseline version: {version!r}")
        if set(data) != {"version", "entries"}:
            raise ValueError("version 2 must contain exactly version and entries")
        raw_entries = data["entries"]
        if not isinstance(raw_entries, list):
            raise ValueError("entries must be a list")
        entries = {
            BaselineEntry.from_dict(entry, index)
            for index, entry in enumerate(raw_entries)
        }
        if len(entries) != len(raw_entries):
            raise ValueError("entries must not contain duplicates")
        self._entries = entries
        self._format_version = 2

    def save(self) -> None:
        """Atomically save structured version 2 entries."""
        data = {
            "version": 2,
            "entries": [entry.to_dict() for entry in sorted(self._entries)],
        }
        serialized = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.baseline_path.parent,
                prefix=f".{self.baseline_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(serialized)
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, self.baseline_path)
        except OSError as exc:
            raise ConfigError(
                self.baseline_path, f"could not save baseline: {exc}"
            ) from exc
        finally:
            if temporary_path is not None:
                with suppress(OSError):
                    temporary_path.unlink(missing_ok=True)
        self._format_version = 2

    def add_issue(
        self, issue: Issue, file_path: Path, content: str, workspace: Path | None = None
    ) -> None:
        """Add one issue using structured source identity."""
        self._entries.add(self._build_entry(issue, file_path, content, workspace))
        self._format_version = 2

    def is_new_issue(
        self, issue: Issue, file_path: Path, content: str, workspace: Path | None = None
    ) -> bool:
        """Return whether an issue is absent from either loaded format."""
        entry = self._build_entry(issue, file_path, content, workspace)
        if entry in self._entries:
            return False
        legacy = self._compute_legacy_fingerprint(issue, file_path, content, workspace)
        return legacy not in self._legacy_fingerprints

    def compare(
        self,
        results: dict[Path, list[Issue]],
        workspace: Path | None = None,
    ) -> BaselineComparison:
        """Partition current issue identities into active, stale, and new sets."""
        current: set[BaselineEntry] = set()
        legacy_by_entry: dict[BaselineEntry, str] = {}
        for file_path, issues in results.items():
            content = file_path.read_text(encoding="utf-8")
            for issue in issues:
                entry = self._build_entry(issue, file_path, content, workspace)
                current.add(entry)
                legacy_by_entry[entry] = self._compute_legacy_fingerprint(
                    issue, file_path, content, workspace
                )

        if self._format_version == 1:
            active = {
                entry
                for entry, fingerprint in legacy_by_entry.items()
                if fingerprint in self._legacy_fingerprints
            }
            matched_legacy = {legacy_by_entry[entry] for entry in active}
            return BaselineComparison(
                active=frozenset(active),
                stale=frozenset(),
                new=frozenset(current - active),
                stale_legacy=len(self._legacy_fingerprints - matched_legacy),
            )

        return BaselineComparison(
            active=frozenset(current & self._entries),
            stale=frozenset(self._entries - current),
            new=frozenset(current - self._entries),
        )

    def replace_entries(
        self, entries: set[BaselineEntry] | frozenset[BaselineEntry]
    ) -> None:
        """Replace contents with structured entries for a maintenance write."""
        self._entries = set(entries)
        self._legacy_fingerprints.clear()
        self._format_version = 2

    def _build_entry(
        self, issue: Issue, file_path: Path, content: str, workspace: Path | None
    ) -> BaselineEntry:
        line = _issue_line(content, issue.line)
        start = min(max(issue.column - 1, 0), len(line))
        end = start
        if (
            issue.end_column is not None
            and issue.end_column - 1 > start
            and issue.end_line in {None, issue.line}
        ):
            end = min(issue.end_column - 1, len(line))
            raw_match = line[start:end]
        else:
            token = re.match(r"[\w]+(?:[-'][\w]+)*|[^\w\s]+", line[start:])
            if token:
                raw_match = token.group()
                end = start + len(raw_match)
            else:
                raw_match = line[start : start + _MATCH_LIMIT]
                end = start + len(raw_match)

        match = _normalize(raw_match)[:_MATCH_LIMIT] or "<empty>"
        context = _normalize(
            line[
                max(0, start - _CONTEXT_RADIUS) : min(len(line), end + _CONTEXT_RADIUS)
            ]
        )
        context_hash = hashlib.sha256(context.encode()).hexdigest()[:16]
        path = _relative_path(file_path, workspace)
        return BaselineEntry(path, issue.rule_id.upper(), match, context_hash)

    def _compute_legacy_fingerprint(
        self, issue: Issue, file_path: Path, content: str, workspace: Path | None = None
    ) -> str:
        """Compute the original version 1 message/three-line fingerprint."""
        if workspace:
            try:
                rel_path = file_path.relative_to(workspace)
            except ValueError:
                rel_path = file_path
        else:
            rel_path = file_path

        message_hash = hashlib.sha256(issue.message.encode()).hexdigest()[:16]
        lines = content.split("\n")
        line_idx = issue.line - 1
        context = "\n".join(lines[max(0, line_idx - 1) : min(len(lines), line_idx + 2)])
        context_hash = hashlib.sha256(context.encode()).hexdigest()[:16]
        fingerprint = {
            "rule_id": issue.rule_id,
            "message_hash": message_hash,
            "relative_path": str(rel_path),
            "context_hash": context_hash,
        }
        return hashlib.sha256(json.dumps(fingerprint).encode()).hexdigest()[:32]

    @property
    def count(self) -> int:
        return len(self._entries) + len(self._legacy_fingerprints)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def format_version(self) -> int | None:
        return self._format_version

    @property
    def entries(self) -> list[BaselineEntry]:
        return sorted(self._entries)


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def _issue_line(content: str, line_number: int) -> str:
    lines = content.splitlines()
    if 1 <= line_number <= len(lines):
        return lines[line_number - 1]
    return ""


def _relative_path(file_path: Path, workspace: Path | None) -> str:
    resolved_file = file_path.resolve()
    root = (workspace or Path.cwd()).resolve()
    try:
        return resolved_file.relative_to(root).as_posix()
    except ValueError as exc:
        raise ConfigError(
            Path("<workspace>"),
            f"{file_path} is outside baseline workspace {root}",
        ) from exc


def _git_root(path: Path) -> Path | None:
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def resolve_workspace(paths: list[Path]) -> Path:
    """Resolve a stable common workspace independent of input order."""
    if not paths:
        return Path.cwd().resolve()
    roots = [
        (path.resolve().parent if path.is_file() else path.resolve()) for path in paths
    ]
    git_roots = {_git_root(root) for root in roots}
    if len(git_roots) == 1 and None not in git_roots:
        return next(iter(git_roots))  # type: ignore[return-value]
    try:
        return Path(os.path.commonpath(roots))
    except ValueError as exc:
        raise ConfigError(
            Path("<workspace>"), "scan paths do not share a common filesystem root"
        ) from exc


def filter_new_issues(
    results: dict[Path, list[Issue]],
    baseline: Baseline,
    workspace: Path | None = None,
) -> dict[Path, list[Issue]]:
    """Filter results to only issues absent from the loaded baseline."""
    filtered: dict[Path, list[Issue]] = {}
    for file_path, issues in results.items():
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        new_issues = [
            issue
            for issue in issues
            if baseline.is_new_issue(issue, file_path, content, workspace)
        ]
        if new_issues:
            filtered[file_path] = new_issues
    return filtered
