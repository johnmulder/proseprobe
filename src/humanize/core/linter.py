"""Main linting orchestrator."""

import fnmatch
from pathlib import Path

from humanize.config import Config
from humanize.parsers.markdown import is_markdown_file
from humanize.rules.base import Issue, Rule


class Linter:
    """Orchestrates file discovery and rule execution."""

    def __init__(self, config: Config) -> None:
        """Initialize linter with configuration.

        Args:
            config: Linter configuration.
        """
        self.config = config
        self._rules: list[Rule] = []

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
        files: list[Path] = []
        roots: list[Path] = []
        for path in paths:
            if path.is_file():
                files.append(path)
                roots.append(path.parent)
            elif path.is_dir():
                roots.append(path)
                for pattern in self.config.include:
                    files.extend(path.rglob(pattern))

        # De-duplicate while preserving order
        files = list(dict.fromkeys(files))

        # Apply exclude patterns
        filtered: list[Path] = []
        for file in files:
            if self._is_excluded(file, roots):
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

        for raw_pattern in self.config.exclude:
            pattern = raw_pattern.strip()
            if not pattern:
                continue

            anchored = pattern.startswith("/")
            if anchored:
                pattern = pattern.lstrip("/")

            # Treat directory patterns as recursive globs
            if pattern.endswith("/"):
                pattern = pattern + "**"

            candidates = rel_candidates if anchored else rel_candidates + [file]
            if self._match_pattern_any(candidates, pattern):
                return True

        return False

    def _match_pattern_any(self, candidates: list[Path], pattern: str) -> bool:
        """Match a glob pattern against multiple candidates."""
        for candidate in candidates:
            if candidate.match(pattern):
                return True
            if not pattern.startswith("**/") and candidate.match(f"**/{pattern}"):
                return True
        return False

    def check_file(self, path: Path) -> list[Issue]:
        """Check a single file for issues.

        Args:
            path: Path to file.

        Returns:
            List of issues found.
        """
        content = path.read_text(encoding="utf-8")
        issues: list[Issue] = []

        for rule in self._rules:
            if self._rule_enabled(rule, path):
                issues.extend(rule.check(content, str(path)))

        return issues

    def check(self, paths: list[Path]) -> dict[Path, list[Issue]]:
        """Check multiple paths for issues.

        Args:
            paths: Files or directories to check.

        Returns:
            Mapping of file paths to issues.
        """
        files = self.discover_files(paths)
        results: dict[Path, list[Issue]] = {}

        for file in files:
            issues = self.check_file(file)
            if issues:
                results[file] = issues

        return results

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
            pattern_matches = (
                fnmatch.fnmatch(path.name, per_file.pattern)
                or fnmatch.fnmatch(str(path), per_file.pattern)
            )
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
        if "markdown" in applies and is_markdown_file(path.name):
            return True
        return bool("python" in applies and path.suffix == ".py")
