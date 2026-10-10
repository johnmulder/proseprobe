"""Explicit parameter-kind documentation examples."""


def ordinary(args):
    """:param *args: Input."""
    return args


def variadic(*args):
    """:param *args: Values."""
    return args
