"""Main linting orchestrator."""

import fnmatch
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from slop_lint.config import Config
from slop_lint.rules.base import Issue, Rule

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


class LintResults(dict[Path, list[Issue]]):
    """Lint issues plus scan metadata, while preserving dict behavior."""

    def __init__(
        self,
        issues_by_file: dict[Path, list[Issue]] | None = None,
        *,
        files_checked: int = 0,
    ) -> None:
        super().__init__(issues_by_file or {})
        self.files_checked = files_checked

    @property
    def issues_by_file(self) -> dict[Path, list[Issue]]:
        """Return issues keyed by file path."""
        return dict(self)


class FileDiscovery:
    """Resolve paths into files matching include/exclude patterns."""

    def __init__(
        self,
        include: list[str],
        exclude: list[str],
    ) -> None:
        self._include = include
        self._exclude = exclude
        self._gitignore_patterns: dict[Path, list[_GitignorePattern]] = {}

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

        # Apply exclude patterns
        filtered: list[Path] = []
        for file in files:
            if self._is_excluded(file, roots):
                continue
            if file not in explicit_files and self._is_gitignored(file, roots):
                continue
            filtered.append(file)

        return filtered

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

    def _load_gitignore_patterns(self, directory: Path) -> list["_GitignorePattern"]:
        """Load parsed .gitignore patterns from a directory."""
        if directory in self._gitignore_patterns:
            return self._gitignore_patterns[directory]

        ignore_file = directory / ".gitignore"
        if not ignore_file.exists():
            self._gitignore_patterns[directory] = []
            return []

        parsed: list[_GitignorePattern] = []
        for raw_line in ignore_file.read_text(
            encoding="utf-8", errors="ignore"
        ).splitlines():
            pattern = raw_line.strip()
            if not pattern:
                continue

            if pattern.startswith("\\#"):
                pattern = pattern[1:]
            elif pattern.startswith("#"):
                continue

            negated = False
            if pattern.startswith("\\!"):
                pattern = pattern[1:]
            elif pattern.startswith("!"):
                negated = True
                pattern = pattern[1:]

            anchored = pattern.startswith("/")
            if anchored:
                pattern = pattern.lstrip("/")

            directory_only = pattern.endswith("/")
            if directory_only:
                pattern = pattern.rstrip("/")

            if not pattern:
                continue

            parsed.append(
                _GitignorePattern(
                    pattern=pattern,
                    negated=negated,
                    anchored=anchored,
                    directory_only=directory_only,
                    has_slash="/" in pattern,
                )
            )

        self._gitignore_patterns[directory] = parsed
        return parsed

    @staticmethod
    def _gitignore_pattern_matches(
        rel_path: Path,
        entry: "_GitignorePattern",
    ) -> bool:
        """Check whether a parsed .gitignore pattern matches a relative path."""
        path_str = rel_path.as_posix()

        if entry.directory_only:
            if entry.anchored:
                return path_str == entry.pattern or path_str.startswith(
                    f"{entry.pattern}/"
                )

            if entry.has_slash:
                return (
                    path_str == entry.pattern
                    or path_str.startswith(f"{entry.pattern}/")
                    or fnmatch.fnmatch(path_str, f"**/{entry.pattern}")
                    or fnmatch.fnmatch(path_str, f"**/{entry.pattern}/**")
                )

            return entry.pattern in rel_path.parts

        if entry.anchored:
            return fnmatch.fnmatch(path_str, entry.pattern)

        if entry.has_slash:
            return fnmatch.fnmatch(path_str, entry.pattern) or fnmatch.fnmatch(
                path_str, f"**/{entry.pattern}"
            )

        return (
            fnmatch.fnmatch(rel_path.name, entry.pattern)
            or fnmatch.fnmatch(path_str, entry.pattern)
            or fnmatch.fnmatch(path_str, f"**/{entry.pattern}")
        )

    @staticmethod
    def _iter_scope_directories(root: Path, file: Path) -> list[Path]:
        """Return root-to-leaf directories whose .gitignore can affect the file."""
        directories: list[Path] = []
        current = file.parent
        while True:
            directories.append(current)
            if current == root:
                break
            if root not in current.parents:
                return []
            current = current.parent
        directories.reverse()
        return directories

    def _is_gitignored(self, file: Path, roots: list[Path]) -> bool:
        """Check if a file is ignored by a root .gitignore."""
        for root in roots:
            try:
                file.relative_to(root)
            except ValueError:
                continue

            scope_dirs = self._iter_scope_directories(root, file)
            if not scope_dirs:
                continue

            ignored = False
            for scope_dir in scope_dirs:
                patterns = self._load_gitignore_patterns(scope_dir)
                if not patterns:
                    continue

                rel_path = file.relative_to(scope_dir)
                for entry in patterns:
                    if self._gitignore_pattern_matches(rel_path, entry):
                        ignored = not entry.negated

            if ignored:
                return True

        return False


@dataclass(frozen=True)
class _GitignorePattern:
    """Parsed .gitignore pattern metadata for matching behavior."""

    pattern: str
    negated: bool
    anchored: bool
    directory_only: bool
    has_slash: bool


# ---------------------------------------------------------------------------
# Linter (single responsibility: register rules and run them on files)
# ---------------------------------------------------------------------------


class Linter:
    """Orchestrates rule execution across discovered files."""

    def __init__(self, config: Config) -> None:
        """Initialize linter with configuration.

        Args:
            config: Linter configuration.
        """
        self.config = config
        self._rules: list[Rule] = []
        self._discovery = FileDiscovery(config.include, config.exclude)

    def register_rule(self, rule: Rule) -> None:
        """Register a rule for linting.

        Args:
            rule: Rule instance to register.
        """
        self._rules.append(rule)

    def discover_files(self, paths: list[Path]) -> list[Path]:
        """Discover files to lint from paths.

        Args:
            paths: List of files or directories.

        Returns:
            List of files matching include/exclude patterns.
        """
        return self._discovery.discover(paths)

    def check_file(self, path: Path) -> list[Issue]:
        """Check a single file for issues.

        Args:
            path: Path to file.

        Returns:
            List of issues found.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise LintReadError(path, str(exc)) from exc
        issues: list[Issue] = []

        for rule in self._rules:
            if self._rule_enabled(rule, path):
                issues.extend(rule.check(content, str(path)))

        return issues

    def check(self, paths: list[Path]) -> LintResults:
        """Check multiple paths for issues.

        Args:
            paths: Files or directories to check.

        Returns:
            Mapping of file paths to issues.
        """
        files = self.discover_files(paths)
        if not files:
            return LintResults(files_checked=0)

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
        # Check global select/ignore
        if rule.id in self.config.ignore:
            return False

        prefix = rule.id[0]  # V, S, T, etc.

        # Check per-file ignores
        for per_file in self.config.per_file_ignores:
            pattern_matches = fnmatch.fnmatch(
                path.name, per_file.pattern
            ) or fnmatch.fnmatch(str(path), per_file.pattern)
            if pattern_matches and (
                rule.id in per_file.ignore or prefix in per_file.ignore
            ):
                return False

        return prefix in self.config.select or rule.id in self.config.select

    def _rule_applies_to_file(self, rule: Rule, path: Path) -> bool:
        """Check if a rule applies to the file type."""
        applies = rule.applies_to
        if "any" in applies:
            return True
        return any(
            checker(path) for tag, checker in _FILE_TYPE_CHECKERS if tag in applies
        )
