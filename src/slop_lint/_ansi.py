"""Minimal ANSI styling helpers (replaces rich dependency).

Respects the NO_COLOR convention (https://no-color.org) and detects
whether stdout is a TTY.
"""

import os
import sys

__all__ = ["clear_screen", "style", "table"]

# ANSI SGR codes
_CODES: dict[str, str] = {
    "bold": "1",
    "dim": "2",
    "reset": "0",
    # Foreground colours
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
}


def _use_color() -> bool:
    """Return True if ANSI colour output should be used."""
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") is not None:
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def style(
    text: str,
    *,
    bold: bool = False,
    dim: bool = False,
    color: str | None = None,
) -> str:
    """Wrap *text* in ANSI SGR codes.

    Returns plain text when colour is disabled.
    """
    if not _use_color():
        return text

    parts: list[str] = []
    if bold:
        parts.append(_CODES["bold"])
    if dim:
        parts.append(_CODES["dim"])
    if color and color in _CODES:
        parts.append(_CODES[color])

    if not parts:
        return text

    prefix = "\033[" + ";".join(parts) + "m"
    suffix = "\033[" + _CODES["reset"] + "m"
    return f"{prefix}{text}{suffix}"


def table(
    headers: list[str],
    rows: list[list[str]],
    *,
    title: str | None = None,
) -> str:
    """Format *rows* as an aligned text table.

    Returns a multi-line string ready for ``print()``.
    """
    # Compute column widths
    all_rows = [headers, *rows]
    n_cols = len(headers)
    widths = [0] * n_cols
    for row in all_rows:
        for i, cell in enumerate(row[:n_cols]):
            widths[i] = max(widths[i], len(cell))

    # Build output
    lines: list[str] = []

    if title:
        lines.append(style(title, bold=True))
        lines.append("")

    # Header
    header_cells = [headers[i].ljust(widths[i]) for i in range(n_cols)]
    lines.append("  ".join(header_cells))
    lines.append("  ".join("-" * w for w in widths))

    # Data rows
    for row in rows:
        cells = [
            (row[i] if i < len(row) else "").ljust(widths[i]) for i in range(n_cols)
        ]
        lines.append("  ".join(cells))

    return "\n".join(lines)


def clear_screen() -> None:
    """Clear the terminal screen."""
    if _use_color():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    else:
        # Fallback: print some newlines
        print("\n" * 40)
