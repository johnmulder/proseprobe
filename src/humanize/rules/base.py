"""Abstract base rule and common types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


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
