"""Main linting orchestrator."""

import fnmatch
from pathlib import Path

from humanize.config import Config
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
        for path in paths:
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                for pattern in self.config.include:
                    files.extend(path.rglob(pattern))

        # Apply exclude patterns
        filtered: list[Path] = []
        for file in files:
            excluded = False
            for exclude_pattern in self.config.exclude:
                # Match against the file path string
                if fnmatch.fnmatch(str(file), f"*/{exclude_pattern}") or \
                   fnmatch.fnmatch(str(file), exclude_pattern) or \
                   any(fnmatch.fnmatch(part, exclude_pattern.rstrip("/*").rstrip("/**")) 
                       for part in file.parts):
                    excluded = True
                    break
            if not excluded:
                filtered.append(file)

        return filtered

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
        # Check global select/ignore
        if rule.id in self.config.ignore:
            return False

        prefix = rule.id[0]  # V, S, T, etc.

        # Check per-file ignores
        for per_file in self.config.per_file_ignores:
            if fnmatch.fnmatch(path.name, per_file.pattern) or \
               fnmatch.fnmatch(str(path), per_file.pattern):
                if rule.id in per_file.ignore or prefix in per_file.ignore:
                    return False

        return prefix in self.config.select or rule.id in self.config.select
