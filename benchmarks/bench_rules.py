#!/usr/bin/env python3
"""Benchmark suite for proseprobe performance testing.

Usage:
    python -m benchmarks.bench_rules     # Run benchmarks
    make benchmark                        # Via make

Tracks performance regressions in rule checking across content sizes.
"""

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from proseprobe import __version__
from proseprobe.config import Config, load_config
from proseprobe.core.policy import filter_by_confidence, prepare_scan
from proseprobe.parsers.markdown import clear_parser_cache as clear_markdown_cache
from proseprobe.parsers.prose import _source_lines
from proseprobe.parsers.python import clear_parser_cache as clear_python_cache
from proseprobe.profiles import PROFILES
from proseprobe.rules import get_all_rules
from proseprobe.rules.base import Rule


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    name: str
    content_size: int
    num_rules: int
    duration_ms: float
    issues_found: int
    throughput_kb_per_sec: float
    measurement: str = "direct-rule stress"
    cache_state: str = "warm"
    files_checked: int = 1
    iterations: int = 1
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    files_per_sec: float = 0.0
    workload_sha256: str = ""
    policy: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)


def clear_parser_caches() -> None:
    """Clear parser and source-line caches without clearing operating-system caches."""
    clear_markdown_cache()
    clear_python_cache()
    _source_lines.cache_clear()


def _workload_identity(documents: Mapping[Path, str]) -> tuple[int, str]:
    digest = hashlib.sha256()
    if not documents:
        return 0, digest.hexdigest()
    root = Path(os.path.commonpath([str(path.absolute().parent) for path in documents]))
    byte_count = 0
    for path in sorted(
        documents, key=lambda item: str(item.absolute().relative_to(root))
    ):
        content = documents[path].encode("utf-8")
        name = str(path.absolute().relative_to(root)).encode("utf-8")
        digest.update(
            name + b"\0" + str(len(content)).encode("ascii") + b"\0" + content
        )
        byte_count += len(content)
    return byte_count, digest.hexdigest()


def _environment() -> dict[str, Any]:
    return {
        "proseprobe": __version__,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
    }


def _policy_metadata(config: Config) -> dict[str, Any]:
    values = asdict(config)
    values.pop("source_path")
    return values


def _measure(
    name: str,
    documents: Mapping[Path, str],
    rules: list[Rule],
    scan: Callable[[], tuple[int, int]],
    iterations: int,
    measurement: str,
    cache_state: str,
    policy: dict[str, Any],
    *,
    warmup: bool = True,
) -> BenchmarkResult:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if warmup and cache_state not in {"warm", "cleared"}:
        raise ValueError("cache_state must be warm or cleared")
    if not warmup and cache_state != "new process":
        raise ValueError("cold CLI benchmarks require a new process")
    content_size, checksum = _workload_identity(documents)
    if warmup:
        clear_parser_caches()
        scan()
    times: list[float] = []
    issues_found = 0
    files_checked = 0
    for _ in range(iterations):
        if cache_state == "cleared":
            clear_parser_caches()
        start = time.perf_counter()
        files_checked, issues_found = scan()
        times.append(time.perf_counter() - start)
        if files_checked != len(documents):
            raise RuntimeError("selected workload changed during the benchmark")
    duration = statistics.median(times)
    return BenchmarkResult(
        name=name,
        content_size=content_size,
        num_rules=len(rules),
        duration_ms=duration * 1000,
        issues_found=issues_found,
        throughput_kb_per_sec=content_size / 1024 / duration if duration > 0 else 0,
        measurement=measurement,
        cache_state=cache_state,
        files_checked=files_checked,
        iterations=iterations,
        min_duration_ms=min(times) * 1000,
        max_duration_ms=max(times) * 1000,
        files_per_sec=files_checked / duration if duration > 0 else 0,
        workload_sha256=checksum,
        policy=policy,
        environment=_environment(),
    )


def generate_markdown_content(size_kb: int) -> str:
    """Generate Markdown content of approximate size."""
    # Representative prose patterns used to exercise rules
    block = """\
# Section Title

This comprehensive guide delves into the intricacies of the topic.
We will explore the multifaceted aspects of this important subject.

## Key Features

- **Feature One:** A crucial component of the system
- **Feature Two:** Showcasing the robust architecture
- **Feature Three:** Leveraging cutting-edge technology

The landscape of modern development is constantly evolving.
Not only does it require technical skills, but also creativity.

### Subsection

Here is some code:

```python
def example():
    '''An example function.'''
    return True
```

The following points are important:

1. First, we need to understand the basics
2. Second, we should consider the implications
3. Finally, we can implement the solution

"""
    # Repeat to reach target size
    repeats = max(1, (size_kb * 1024) // len(block))
    return block * repeats


def generate_python_content(size_kb: int) -> str:
    """Generate Python content of approximate size."""
    block = '''\
def example_function(param: str) -> None:
    """This function showcases the crucial functionality.

    It delves into the intricacies of the implementation,
    leveraging advanced techniques to achieve optimal results.

    Args:
        param: A comprehensive parameter description.

    Returns:
        None: This function fosters collaboration.
    """
    # This is a crucial step
    result = process_data(param)

    # Leverage the power of the framework
    return finalize(result)


class ExampleClass:
    """A multifaceted class demonstrating various patterns."""

    def __init__(self, value: int) -> None:
        """Initialize with a pivotal value."""
        self.value = value

    def process(self) -> str:
        """Showcase the processing capabilities."""
        return str(self.value)


'''
    repeats = max(1, (size_kb * 1024) // len(block))
    return block * repeats


def run_benchmark(
    name: str,
    content: str,
    filename: str,
    iterations: int = 5,
) -> BenchmarkResult:
    """Measure direct calls to all rules, preserving the historical stress workload."""
    rules = get_all_rules()

    def scan() -> tuple[int, int]:
        issues = [issue for rule in rules for issue in rule.check(content, filename)]
        return 1, len(issues)

    return _measure(
        name,
        {Path(filename): content},
        rules,
        scan,
        iterations,
        "direct-rule stress",
        "warm",
        {"mode": "all rules called directly without production filtering"},
    )


def _selected_rules(config: Config, rules: list[Rule]) -> list[Rule]:
    return [
        rule
        for rule in rules
        if (rule.id in config.select or rule.id[0] in config.select)
        and rule.id not in config.ignore
        and rule.id[0] not in config.ignore
    ]


def run_scan_benchmark(
    name: str,
    documents: Mapping[Path, str],
    config: Config | None = None,
    iterations: int = 5,
    cache_state: str = "warm",
) -> BenchmarkResult:
    """Measure in-memory checks and confidence filtering using production policy."""
    config, linter, rules = prepare_scan(config or Config())

    def scan() -> tuple[int, int]:
        issues = {
            path: findings
            for path, content in documents.items()
            if (findings := linter.check_content(content, path))
        }
        return len(documents), sum(
            len(findings)
            for findings in filter_by_confidence(issues, config.min_confidence).values()
        )

    return _measure(
        name,
        documents,
        _selected_rules(config, rules),
        scan,
        iterations,
        "in-memory production scan",
        cache_state,
        _policy_metadata(config),
    )


def run_workspace_benchmark(
    name: str,
    paths: list[Path],
    config: Config | None = None,
    iterations: int = 5,
    cache_state: str = "warm",
) -> BenchmarkResult:
    """Measure real discovery, file reading, extraction, rules, and filtering."""
    config, linter, rules = prepare_scan(config or Config())
    documents = {
        path: path.read_text(encoding="utf-8") for path in linter.discover_files(paths)
    }

    def scan() -> tuple[int, int]:
        results = linter.check(paths)
        return results.files_checked, sum(
            len(findings)
            for findings in filter_by_confidence(
                results.issues_by_file, config.min_confidence
            ).values()
        )

    return _measure(
        name,
        documents,
        _selected_rules(config, rules),
        scan,
        iterations,
        "directory discovery/read/production scan",
        cache_state,
        _policy_metadata(config),
    )


def run_cli_benchmark(
    name: str,
    paths: list[Path],
    config_path: Path,
    iterations: int = 5,
) -> BenchmarkResult:
    """Measure new CLI processes through captured JSON output with explicit config."""
    config_path = config_path.absolute()
    paths = [path.absolute() for path in paths]
    config, linter, rules = prepare_scan(load_config(config_path))
    documents = {
        path: path.read_text(encoding="utf-8") for path in linter.discover_files(paths)
    }
    command = [
        sys.executable,
        "-m",
        "proseprobe",
        "check",
        *(str(path) for path in paths),
        "--config",
        str(config_path),
        "--format",
        "json",
    ]

    def scan() -> tuple[int, int]:
        result = subprocess.run(
            command,
            cwd=config_path.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode not in {0, 1}:
            raise RuntimeError(
                f"CLI scan failed ({result.returncode}): {result.stderr}"
            )
        summary = json.loads(result.stdout)["summary"]
        return summary["files_checked"], summary["total_issues"]

    return _measure(
        name,
        documents,
        _selected_rules(config, rules),
        scan,
        iterations,
        "cold subprocess CLI with JSON serialization",
        "new process",
        _policy_metadata(config),
        warmup=False,
    )


def write_workspace(
    root: Path, small_files: int = 40, *, repeated: bool = False
) -> None:
    """Create a fixed offline mix with masked code, Unicode, and cache pressure."""
    (root / "small").mkdir(parents=True)
    (root / "ignored").mkdir()
    (root / ".gitignore").write_text("/ignored/\n", encoding="utf-8")
    (root / "ignored" / "ignored.md").write_text(
        "This delves into setup.\n", encoding="utf-8"
    )
    (root / "issues.md").write_text(
        "Café operators delve in order to retry.\n", encoding="utf-8"
    )
    (root / "clean.md").write_text("Read the café setup guide.\n", encoding="utf-8")
    code = "\n".join(f'value_{index} = "delve"' for index in range(200))
    (root / "code-heavy.md").write_text(
        f'# Code example\n\n```python title="example.py"\n{code}\n```\n',
        encoding="utf-8",
    )
    (root / "code-heavy.py").write_text(
        f'"""Read the stored values."""\n{code}\n', encoding="utf-8"
    )
    for index in range(small_files):
        suffix = ".py" if index % 2 else ".md"
        number = "" if repeated else f" {index}"
        text = f"Read café request{number} before retrying."
        if suffix == ".py":
            text = f'"""{text}"""'
        (root / "small" / f"file_{index:03}{suffix}").write_text(
            text + "\n", encoding="utf-8"
        )
    subprocess.run(
        ["git", "init", "-q", str(root)],  # noqa: S607 - resolve Git through PATH
        check=True,
        capture_output=True,
    )


def print_results(results: list[BenchmarkResult]) -> None:
    """Print benchmark results in a table."""
    print("\n" + "=" * 80)
    print("PROSEPROBE BENCHMARK RESULTS")
    print("=" * 80)
    print(
        f"{'Benchmark':<30} {'UTF-8 KiB':>10} {'Median ms':>12} {'Files':>6} {'Issues':>8} {'KiB/s':>12} {'files/s':>10}"
    )
    print("-" * 80)

    for r in results:
        size_str = f"{r.content_size / 1024:.1f}"
        time_str = f"{r.duration_ms:.2f}"
        throughput_str = f"{r.throughput_kb_per_sec:.1f}"
        print(
            f"{r.name:<30} {size_str:>10} {time_str:>12} {r.files_checked:>6} {r.issues_found:>8} {throughput_str:>12} {r.files_per_sec:>10.1f}"
        )
        print(
            f"  {r.measurement}; parser cache: {r.cache_state}; selected rules: {r.num_rules}"
        )
        print(
            f"  range {r.min_duration_ms:.2f}-{r.max_duration_ms:.2f} ms; {r.iterations} samples; SHA-256 {r.workload_sha256}"
        )

    print("=" * 80)

    if results:
        print(f"Environment: {json.dumps(results[0].environment, sort_keys=True)}")
    print(
        "Preparation is excluded; parser-cache clearing does not clear filesystem caches."
    )


def main() -> None:
    """Run all benchmarks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--mode", choices=["all", "stress", "scan"], default="all")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="technical-docs")
    parser.add_argument("--workspace", type=Path, nargs="+")
    args = parser.parse_args()
    if args.iterations <= 0:
        parser.error("iterations must be positive")
    results: list[BenchmarkResult] = []

    if args.mode in {"all", "stress"}:
        for size_kb in [1, 10, 50, 100]:
            results.append(
                run_benchmark(
                    f"markdown_{size_kb}kb",
                    generate_markdown_content(size_kb),
                    "benchmark.md",
                    args.iterations,
                )
            )
        for size_kb in [1, 10, 50]:
            results.append(
                run_benchmark(
                    f"python_{size_kb}kb",
                    generate_python_content(size_kb),
                    "benchmark.py",
                    args.iterations,
                )
            )
        results.append(run_benchmark("empty_file", "", "empty.md", args.iterations))
        results.append(
            run_benchmark("single_line", "Hello, world!", "single.md", args.iterations)
        )

    if args.mode in {"all", "scan"}:
        with tempfile.TemporaryDirectory(prefix="proseprobe-bench-") as temp_dir:
            root = Path(temp_dir)
            config_path = root / "benchmark.toml"
            config_path.write_text(f'profile = "{args.profile}"\n', encoding="utf-8")
            config = load_config(config_path)
            if args.workspace:
                workspaces = [("supplied-workspace", args.workspace)]
            else:
                distinct = root / "distinct"
                repeated = root / "repeated"
                write_workspace(distinct)
                write_workspace(repeated, repeated=True)
                workspaces = [
                    ("distinct-small", [distinct]),
                    ("repeated-small", [repeated]),
                    (
                        "reviewed-corpus",
                        [Path(__file__).resolve().parents[1] / "quality/corpus"],
                    ),
                ]
            for name, paths in workspaces:
                _, linter, _ = prepare_scan(config)
                documents = {
                    path: path.read_text(encoding="utf-8")
                    for path in linter.discover_files(paths)
                }
                for cache_state in ["warm", "cleared"]:
                    results.append(
                        run_scan_benchmark(
                            f"{name}/memory/{cache_state}",
                            documents,
                            config,
                            args.iterations,
                            cache_state,
                        )
                    )
                    results.append(
                        run_workspace_benchmark(
                            f"{name}/directory/{cache_state}",
                            paths,
                            config,
                            args.iterations,
                            cache_state,
                        )
                    )
                results.append(
                    run_cli_benchmark(
                        f"{name}/CLI", paths, config_path, args.iterations
                    )
                )

    if args.format == "json":
        print(
            json.dumps([asdict(result) for result in results], indent=2, sort_keys=True)
        )
    else:
        print_results(results)


if __name__ == "__main__":
    main()
