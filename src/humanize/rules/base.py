"""Abstract base rule and common types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from humanize.parsers.markdown import iter_non_code_lines, iter_prose_lines


class Severity(Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    OFF = "off"


_SEVERITY_RANK = {
    Severity.ERROR: 3,
    Severity.WARNING: 2,
    Severity.INFO: 1,
    Severity.OFF: 0,
}


def severity_rank(severity: Severity) -> int:
    """Return numeric rank for severity comparisons."""
    return _SEVERITY_RANK.get(severity, 0)


def severity_from_str(value: str, default: Severity | None = None) -> Severity | None:
    """Convert string to Severity enum.

    Args:
        value: Severity string (error, warning, info, off).
        default: Default value if string is not recognized.

    Returns:
        Corresponding Severity enum value, or default if not found.
    """
    mapping = {
        "error": Severity.ERROR,
        "warning": Severity.WARNING,
        "info": Severity.INFO,
        "off": Severity.OFF,
    }
    return mapping.get(value.lower(), default)


@dataclass
class Issue:
    """A detected issue in content."""

    rule_id: str
    message: str
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    severity: Severity = Severity.WARNING
    fixable: bool = False
    suggestion: str | None = None


class Rule(ABC):
    """Abstract base class for detection rules."""

    id: str
    name: str
    description: str
    severity: Severity = Severity.WARNING
    fixable: bool = False
    applies_to: set[str] = {"any"}  # "markdown", "python", "any"
    content_scope: str = "raw"  # "raw", "prose", "non_code"

    @abstractmethod
    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content and return issues.

        Args:
            content: File content to check.
            filename: Name of the file being checked.

        Returns:
            List of issues found.
        """
        ...

    def fix(self, content: str, issue: Issue) -> str:
        """Apply fix for an issue.

        Override this method if the rule is fixable.

        Args:
            content: Current file content.
            issue: Issue to fix.

        Returns:
            Modified content with fix applied.
        """
        return content

    def iter_lines(self, content: str, filename: str) -> list[tuple[int, str]]:
        """Return line-numbered content based on the rule's scope."""
        if self.content_scope == "prose":
            return iter_prose_lines(content, filename)
        if self.content_scope == "non_code":
            return iter_non_code_lines(content, filename)
        return list(enumerate(content.split("\n"), start=1))
