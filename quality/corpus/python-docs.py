"""A robust module used to exercise documentation checks."""


def total(values: list[int]) -> int:
    """Return the sum of the supplied values."""
    # This function loops over records before returning the total
    # I hope this helps!
    # TODO: Implement
    # **Important**: replace the placeholder before release
    return sum(values)


def retry() -> None:
    """Retry a request after a transient timeout."""
    # Retry once because the service closes idle connections.
    # Callers can request a longer delay through configuration.
    # TODO: Retry on HTTP 503 after issue #42 defines the limit.
    pass
