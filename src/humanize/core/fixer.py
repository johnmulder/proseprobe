"""Auto-fix engine for fixable issues."""

from pathlib import Path

from humanize.rules.base import Issue, Rule


class Fixer:
    """Applies fixes to files."""

    def __init__(self, rules: list[Rule]) -> None:
        """Initialize fixer with rules.

        Args:
            rules: List of rules that may provide fixes.
        """
        self._rules = {rule.id: rule for rule in rules}

    def fix_file(self, path: Path, issues: list[Issue]) -> tuple[str, int]:
        """Apply fixes to a file.

        Args:
            path: Path to file.
            issues: Issues found in file.

        Returns:
            Tuple of (fixed content, number of fixes applied).
        """
        content = path.read_text(encoding="utf-8")
        fixes_applied = 0

        # Sort issues by position (reverse) to apply fixes from end to start
        # This prevents position shifts from affecting later fixes
        fixable = [i for i in issues if i.fixable]
        fixable.sort(key=lambda i: (i.line, i.column), reverse=True)

        for issue in fixable:
            rule = self._rules.get(issue.rule_id)
            if rule is None:
                continue

            new_content = rule.fix(content, issue)
            if new_content != content:
                content = new_content
                fixes_applied += 1

        return content, fixes_applied

    def fix_and_write(self, path: Path, issues: list[Issue]) -> int:
        """Apply fixes and write back to file.

        Args:
            path: Path to file.
            issues: Issues found in file.

        Returns:
            Number of fixes applied.
        """
        content, fixes_applied = self.fix_file(path, issues)

        if fixes_applied > 0:
            path.write_text(content, encoding="utf-8")

        return fixes_applied
