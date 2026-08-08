"""Memory probe for proseprobe workspace scanning."""

from __future__ import annotations

import argparse
import tempfile
import tracemalloc
from pathlib import Path

from proseprobe.config import Config
from proseprobe.core.linter import Linter
from proseprobe.rules import get_all_rules


def _write_workspace(root: Path, file_count: int) -> None:
    """Create a synthetic workspace with Markdown and Python files."""
    for index in range(file_count):
        subdir = root / f"pkg_{index // 1000:02d}"
        subdir.mkdir(exist_ok=True)
        suffix = ".py" if index % 2 else ".md"
        path = subdir / f"file_{index:05d}{suffix}"
        if suffix == ".py":
            path.write_text('"""Small module docstring."""\n\n# regular comment\n')
        else:
            path.write_text("# Heading\n\nSmall project note.\n")


def run_probe(file_count: int, limit_mb: float) -> int:
    """Run a synthetic scan and return a process exit code."""
    with tempfile.TemporaryDirectory(prefix="proseprobe-memory-") as temp_dir:
        root = Path(temp_dir)
        _write_workspace(root, file_count)

        linter = Linter(Config())
        for rule in get_all_rules():
            linter.register_rule(rule)

        tracemalloc.start()
        results = linter.check([root])
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    print(
        f"Memory probe: {file_count} files, "
        f"{results.files_checked} checked, peak {peak_mb:.1f} MB"
    )
    if peak_mb > limit_mb:
        print(f"Memory probe exceeded {limit_mb:.1f} MB limit")
        return 1
    return 0


def main() -> int:
    """Run the memory probe from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=int, default=10_000)
    parser.add_argument("--limit-mb", type=float, default=100.0)
    args = parser.parse_args()
    return run_probe(args.files, args.limit_mb)


if __name__ == "__main__":
    raise SystemExit(main())
