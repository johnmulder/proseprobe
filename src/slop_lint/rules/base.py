"""Abstract base rule and common types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import ClassVar

__all__ = [
    "Confidence",
    "Issue",
    "Rule",
    "Severity",
    "severity_from_str",
    "severity_rank",
]


class Severity(Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    OFF = "off"


class Confidence(StrEnum):
    """How confident the rule is that a match is a real problem."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


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
    confidence: Confidence = Confidence.MEDIUM
    suggestion: str | None = None


class Rule(ABC):
    """Abstract base class for detection rules."""

    id: str
    name: str
    description: str
    severity: Severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"any"}  # "markdown", "python", "any"
    content_scope: str = "raw"  # "raw", "prose", "non_code"

    # Maps the last segment of a rule module path to a human-readable category.
    _MODULE_CATEGORIES: ClassVar[dict[str, str]] = {
        "vocab": "Vocabulary",
        "struct": "Structure",
    }

    @property
    def category(self) -> str:
        """Derive category name from the owning module."""
        mod_name = type(self).__module__.rsplit(".", 1)[-1]
        return self._MODULE_CATEGORIES.get(mod_name, mod_name.title())

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

    def iter_lines(self, content: str, filename: str) -> list[tuple[int, str]]:
        """Return line-numbered content based on the rule's scope."""
        from slop_lint.parsers.markdown import iter_non_code_lines, iter_prose_lines

        if self.content_scope == "prose":
            return iter_prose_lines(content, filename)
        if self.content_scope == "non_code":
            return iter_non_code_lines(content, filename)
        return list(enumerate(content.split("\n"), start=1))
