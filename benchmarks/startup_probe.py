"""Startup latency probe for slop-lint."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time


def run_probe(limit_ms: float) -> int:
    """Run the version command once and enforce a latency limit."""
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "slop_lint", "version"],
        check=False,
        capture_output=True,
        text=True,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"Startup probe: {elapsed_ms:.1f} ms")
    if result.returncode != 0:
        print(result.stderr)
        return result.returncode
    if elapsed_ms > limit_ms:
        print(f"Startup probe exceeded {limit_ms:.1f} ms limit")
        return 1
    return 0


def main() -> int:
    """Run the startup probe from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-ms", type=float, default=100.0)
    args = parser.parse_args()
    return run_probe(args.limit_ms)


if __name__ == "__main__":
    raise SystemExit(main())
