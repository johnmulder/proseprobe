"""Main linting orchestrator."""

import fnmatch
import os
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from proseprobe.config import Config, ConfigError
from proseprobe.parsers.prose import iter_inline_suppressions
from proseprobe.rules.base import Issue, Rule

__all__ = ["LintReadError", "LintResults", "Linter"]

# Registry mapping rule ``applies_to`` tags to file-type predicates.
# To support a new file type, append a (tag, checker) tuple here.
_FILE_TYPE_CHECKERS: list[tuple[str, Callable[[Path], bool]]] = [
    ("markdown", lambda p: p.name.lower().endswith((".md", ".mdx", ".markdown"))),
    ("python", lambda p: p.suffix == ".py"),
]


# ---------------------------------------------------------------------------
# File discovery (single responsibility: find files matching config patterns)
# ---------------------------------------------------------------------------


class LintReadError(OSError):
    """Raised when a file cannot be read for linting."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


@dataclass
class LintResults:
    """Lint issues plus scan metadata."""

    issues_by_file: dict[Path, list[Issue]]
    files_checked: int = 0


class FileDiscovery:
    """Resolve paths into files matching include/exclude patterns."""

    def __init__(
        self,
        include: list[str],
        exclude: list[str],
    ) -> None:
        self._include = include
        self._exclude = exclude

    def discover(self, paths: list[Path]) -> list[Path]:
        """Discover files to lint from paths.

        Args:
            paths: List of files or directories.

        Returns:
            List of files matching include/exclude patterns.
        """
        files: list[Path] = []
        explicit_files: set[Path] = set()
        roots: list[Path] = []
        for path in paths:
            if path.is_file():
                files.append(path)
                explicit_files.add(path)
                roots.append(path.parent)
            elif path.is_dir():
                roots.append(path)
                for pattern in self._include:
                    files.extend(path.rglob(pattern))

        # De-duplicate while preserving order
        files = list(dict.fromkeys(files))

        files = [file for file in files if not self._is_excluded(file, roots)]
        ignored = self._gitignored(
            [file for file in files if file not in explicit_files], roots
        )
        return [file for file in files if file not in ignored]

    def _is_excluded(self, file: Path, roots: list[Path]) -> bool:
        """Check if a file should be excluded."""
        rel_candidates: list[Path] = []
        for root in roots:
            try:
                rel_candidates.append(file.relative_to(root))
            except ValueError:
                continue

        for raw_pattern in self._exclude:
            pattern = raw_pattern.strip()
            if not pattern:
                continue

            anchored = pattern.startswith("/")
            if anchored:
                pattern = pattern.lstrip("/")

            # Treat directory patterns as recursive globs
            if pattern.endswith("/"):
                pattern = pattern + "**"

            candidates = rel_candidates if anchored else [*rel_candidates, file]
            if self._match_pattern_any(candidates, pattern):
                return True

        return False

    @staticmethod
    def _match_pattern_any(candidates: list[Path], pattern: str) -> bool:
        """Match a glob pattern against multiple candidates."""
        for candidate in candidates:
            if candidate.match(pattern):
                return True
            if not pattern.startswith("**/") and candidate.match(f"**/{pattern}"):
                return True
        return False

    @staticmethod
    def _gitignored(files: list[Path], roots: list[Path]) -> set[Path]:
        """Ask Git which discovered files are ignored."""
        ignored: set[Path] = set()
        for root in roots:
            candidates = [
                file for file in files if file == root or root in file.parents
            ]
            if not candidates:
                continue
            try:
                result = subprocess.run(  # noqa: S603 - invoke installed Git
                    [  # noqa: S607 - resolve Git through PATH
                        "git",
                        "-C",
                        str(root),
                        "check-ignore",
                        "--stdin",
                        "-z",
                        "--no-index",
                    ],
                    input="\0".join(str(file) for file in candidates) + "\0",
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except OSError:
                continue
            ignored.update(Path(path) for path in result.stdout.split("\0") if path)
        return ignored


# ---------------------------------------------------------------------------
# Linter (single responsibility: register rules and run them on files)
# ---------------------------------------------------------------------------


class Linter:
    """Orchestrates rule execution across discovered files."""

    def __init__(self, config: Config, valid_rule_ids: set[str] | None = None) -> None:
        """Initialize linter with configuration.

        Args:
            config: Linter configuration.
            valid_rule_ids: Complete rule registry for directive validation.
        """
        self.config = config
        self._rules: list[Rule] = []
        self._valid_rule_ids = {
            rule_id.upper() for rule_id in (valid_rule_ids or set())
        }
        self._discovery = FileDiscovery(config.include, config.exclude)

    def register_rule(self, rule: Rule) -> None:
        """Register a rule for linting.

        Args:
            rule: Rule instance to register.
        """
        self._rules.append(rule)
        self._valid_rule_ids.add(rule.id.upper())

    def discover_files(self, paths: list[Path]) -> list[Path]:
        """Discover files to lint from paths.

        Args:
            paths: List of files or directories.

        Returns:
            List of files matching include/exclude patterns.
        """
        return self._discovery.discover(paths)

    def check_file(self, path: Path) -> list[Issue]:
        """Read and check a single file for issues."""
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise LintReadError(path, str(exc)) from exc
        return self.check_content(content, path)

    def check_content(self, content: str, path: Path) -> list[Issue]:
        """Check in-memory content using a path for file-specific policy."""
        issues: list[Issue] = []

        for rule in self._rules:
            if self._rule_enabled(rule, path):
                issues.extend(rule.check(content, str(path)))

        return self._apply_inline_suppressions(issues, content, path)

    def _apply_inline_suppressions(
        self, issues: list[Issue], content: str, path: Path
    ) -> list[Issue]:
        """Validate line directives and remove their matching issues."""
        try:
            directives = iter_inline_suppressions(content, str(path))
        except ValueError as exc:
            raise ConfigError(path, str(exc)) from exc
        if not directives:
            return issues

        valid_tokens = self._valid_rule_ids | {
            rule_id[0] for rule_id in self._valid_rule_ids
        }
        ignored_by_line: dict[int, set[str]] = {}
        for directive_line, target_line, raw_tokens in directives:
            tokens = {token.strip().upper() for token in raw_tokens.split(",")}
            unknown = sorted(tokens - valid_tokens)
            if unknown:
                joined = ", ".join(unknown)
                raise ConfigError(
                    path,
                    f"line {directive_line}: unknown inline suppression token: {joined}",
                )
            ignored_by_line.setdefault(target_line, set()).update(tokens)

        return [
            issue
            for issue in issues
            if issue.rule_id not in ignored_by_line.get(issue.line, set())
            and issue.rule_id[0] not in ignored_by_line.get(issue.line, set())
        ]

    def check(self, paths: list[Path]) -> LintResults:
        """Check multiple paths for issues.

        Args:
            paths: Files or directories to check.

        Returns:
            Results containing issues by file and the number of files checked.
        """
        files = self.discover_files(paths)
        if not files:
            return LintResults({}, files_checked=0)

        worker_count = min(32, (os.cpu_count() or 1) + 4)

        file_results: list[tuple[Path, list[Issue]]]
        if len(files) > 1 and worker_count > 1:
            with ThreadPoolExecutor(max_workers=min(worker_count, len(files))) as pool:
                file_results = list(pool.map(self._check_file_with_path, files))
        else:
            file_results = [self._check_file_with_path(file) for file in files]

        file_results.sort(key=lambda item: str(item[0]))
        issues_by_file = {path: issues for path, issues in file_results if issues}
        return LintResults(issues_by_file, files_checked=len(files))

    def _check_file_with_path(self, path: Path) -> tuple[Path, list[Issue]]:
        """Return a file path paired with lint issues for executor mapping."""
        return (path, self.check_file(path))

    def _rule_enabled(self, rule: Rule, path: Path) -> bool:
        """Check if a rule is enabled for a file.

        Args:
            rule: Rule to check.
            path: File path.

        Returns:
            True if rule should run on file.
        """
        if not self._rule_applies_to_file(rule, path):
            return False

        prefix = rule.id[0]  # V, S, T, etc.
        if prefix not in self.config.select and rule.id not in self.config.select:
            return False

        # Check per-file ignores
        for per_file in self.config.per_file_ignores:
            pattern_matches = fnmatch.fnmatch(
                path.name, per_file.pattern
            ) or fnmatch.fnmatch(str(path), per_file.pattern)
            if pattern_matches and (
                rule.id in per_file.ignore or prefix in per_file.ignore
            ):
                return False

        # Check global ignore
        return rule.id not in self.config.ignore and prefix not in self.config.ignore

    def _rule_applies_to_file(self, rule: Rule, path: Path) -> bool:
        """Check if a rule applies to the file type."""
        applies = rule.applies_to
        if "any" in applies:
            return True
        return any(
            checker(path) for tag, checker in _FILE_TYPE_CHECKERS if tag in applies
        )
