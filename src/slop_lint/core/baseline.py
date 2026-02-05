"""Baseline support for tracking known issues.

A baseline file stores issue fingerprints so only new issues are reported,
enabling gradual adoption in large codebases.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from slop_lint.rules.base import Issue


@dataclass
class IssueFingerprint:
    """Unique identifier for an issue independent of line numbers."""

    rule_id: str
    message_hash: str  # Hash of message to handle message changes
    relative_path: str  # Path relative to baseline file
    context_hash: str  # Hash of surrounding content for stability

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "IssueFingerprint":
        """Create from dictionary."""
        return cls(
            rule_id=data["rule_id"],
            message_hash=data["message_hash"],
            relative_path=data["relative_path"],
            context_hash=data["context_hash"],
        )


class Baseline:
    """Manages a baseline of known issues."""

    def __init__(self, baseline_path: Path | None = None) -> None:
        """Initialize baseline.

        Args:
            baseline_path: Path to baseline file. Defaults to .slop-lint-baseline.json
        """
        self.baseline_path = baseline_path or Path(".slop-lint-baseline.json")
        self._fingerprints: set[str] = set()
        self._loaded = False

    def load(self) -> bool:
        """Load baseline from file.

        Returns:
            True if baseline was loaded, False if file doesn't exist.
        """
        if not self.baseline_path.exists():
            return False

        try:
            data = json.loads(self.baseline_path.read_text())
            self._fingerprints = set(data.get("fingerprints", []))
            self._loaded = True
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    def save(self) -> None:
        """Save baseline to file."""
        data = {
            "version": "1.0",
            "fingerprints": sorted(self._fingerprints),
        }
        self.baseline_path.write_text(json.dumps(data, indent=2) + "\n")

    def add_issue(
        self, issue: Issue, file_path: Path, content: str, workspace: Path | None = None
    ) -> None:
        """Add an issue to the baseline.

        Args:
            issue: Issue to add.
            file_path: Path to file containing issue.
            content: File content for context hashing.
            workspace: Workspace root for relative paths.
        """
        fingerprint = self._compute_fingerprint(issue, file_path, content, workspace)
        self._fingerprints.add(fingerprint)

    def is_new_issue(
        self, issue: Issue, file_path: Path, content: str, workspace: Path | None = None
    ) -> bool:
        """Check if an issue is new (not in baseline).

        Args:
            issue: Issue to check.
            file_path: Path to file containing issue.
            content: File content for context hashing.
            workspace: Workspace root for relative paths.

        Returns:
            True if issue is not in baseline.
        """
        fingerprint = self._compute_fingerprint(issue, file_path, content, workspace)
        return fingerprint not in self._fingerprints

    def _compute_fingerprint(
        self, issue: Issue, file_path: Path, content: str, workspace: Path | None = None
    ) -> str:
        """Compute a stable fingerprint for an issue.

        The fingerprint is stable across line number changes by using
        surrounding content context.
        """
        # Get relative path
        if workspace:
            try:
                rel_path = file_path.relative_to(workspace)
            except ValueError:
                rel_path = file_path
        else:
            rel_path = file_path

        # Hash the message (may contain specific words/positions)
        message_hash = hashlib.sha256(issue.message.encode()).hexdigest()[:16]

        # Get context: the line with the issue plus surrounding lines
        lines = content.split("\n")
        line_idx = issue.line - 1
        start = max(0, line_idx - 1)
        end = min(len(lines), line_idx + 2)
        context = "\n".join(lines[start:end])
        context_hash = hashlib.sha256(context.encode()).hexdigest()[:16]

        # Create fingerprint string
        fp = IssueFingerprint(
            rule_id=issue.rule_id,
            message_hash=message_hash,
            relative_path=str(rel_path),
            context_hash=context_hash,
        )

        # Return a hash of the full fingerprint for compact storage
        return hashlib.sha256(json.dumps(fp.to_dict()).encode()).hexdigest()[:32]

    @property
    def count(self) -> int:
        """Number of issues in baseline."""
        return len(self._fingerprints)

    @property
    def is_loaded(self) -> bool:
        """Whether baseline was loaded from file."""
        return self._loaded


def filter_new_issues(
    results: dict[Path, list[Issue]],
    baseline: Baseline,
    workspace: Path | None = None,
) -> dict[Path, list[Issue]]:
    """Filter results to only include new issues not in baseline.

    Args:
        results: Mapping of file paths to issues.
        baseline: Baseline to filter against.
        workspace: Workspace root for relative paths.

    Returns:
        Filtered results with only new issues.
    """
    filtered: dict[Path, list[Issue]] = {}

    for file_path, issues in results.items():
        try:
            content = file_path.read_text()
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
