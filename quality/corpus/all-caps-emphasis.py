"""Reviewed Python prose for T013."""

# Callers MUST NOT DELETE cached state during recovery.

DISPLAY = "You MUST NOT DELETE cached state during recovery."
MAX_RETRY_COUNT = 3

# The client uses the HTTP GET API for status checks.


def retry() -> None:
    """Operators SHOULD NEVER IGNORE THIS warning during checksum repair."""
