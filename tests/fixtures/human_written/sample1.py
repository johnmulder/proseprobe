"""Simple data processing utilities."""

from typing import TypeVar

T = TypeVar("T")


def double_values(items: list[T]) -> list[T]:
    """Double each value in a list.

    Args:
        items: List of values to double.

    Returns:
        New list with doubled values.
    """
    return [item * 2 for item in items]  # type: ignore[operator]


def filter_none(items: list[T | None]) -> list[T]:
    """Remove None values from a list.

    Args:
        items: List that may contain None values.

    Returns:
        New list with None values removed.
    """
    return [item for item in items if item is not None]


class Counter:
    """Simple counter class."""

    def __init__(self, start: int = 0) -> None:
        """Create a counter.

        Args:
            start: Initial count value.
        """
        self._count = start

    def increment(self) -> int:
        """Add one to the counter.

        Returns:
            New count value.
        """
        self._count += 1
        return self._count

    @property
    def value(self) -> int:
        """Get current count."""
        return self._count
