#!/usr/bin/env python3
"""Benchmark suite for humanize performance testing.

Usage:
    python -m benchmarks.bench_rules     # Run benchmarks
    make benchmark                        # Via make

Tracks performance regressions in rule checking across content sizes.
"""

import time
from dataclasses import dataclass
from pathlib import Path

from humanize.rules import get_all_rules
from humanize.rules.base import Issue, Rule


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    name: str
    content_size: int
    num_rules: int
    duration_ms: float
    issues_found: int
    throughput_kb_per_sec: float


def generate_markdown_content(size_kb: int) -> str:
    """Generate Markdown content of approximate size."""
    # Sample content with some AI patterns to exercise rules
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
    """Run a benchmark and return results."""
    rules = get_all_rules()
    
    def check_all_rules(content: str, filename: str) -> list[Issue]:
        """Run all rules on content."""
        issues: list[Issue] = []
        for rule in rules:
            issues.extend(rule.check(content, filename))
        return issues
    
    # Warm up
    check_all_rules(content, filename)
    
    # Timed runs
    times: list[float] = []
    issues_found = 0
    
    for _ in range(iterations):
        start = time.perf_counter()
        issues = check_all_rules(content, filename)
        end = time.perf_counter()
        times.append(end - start)
        issues_found = len(issues)
    
    avg_duration = sum(times) / len(times)
    content_kb = len(content) / 1024
    throughput = content_kb / avg_duration if avg_duration > 0 else 0
    
    return BenchmarkResult(
        name=name,
        content_size=len(content),
        num_rules=len(rules),
        duration_ms=avg_duration * 1000,
        issues_found=issues_found,
        throughput_kb_per_sec=throughput,
    )


def print_results(results: list[BenchmarkResult]) -> None:
    """Print benchmark results in a table."""
    print("\n" + "=" * 80)
    print("HUMANIZE BENCHMARK RESULTS")
    print("=" * 80)
    print(
        f"{'Benchmark':<30} {'Size':>10} {'Time':>12} {'Issues':>8} {'Throughput':>15}"
    )
    print("-" * 80)
    
    for r in results:
        size_str = f"{r.content_size / 1024:.1f} KB"
        time_str = f"{r.duration_ms:.2f} ms"
        throughput_str = f"{r.throughput_kb_per_sec:.1f} KB/s"
        print(
            f"{r.name:<30} {size_str:>10} {time_str:>12} {r.issues_found:>8} {throughput_str:>15}"
        )
    
    print("=" * 80)
    
    # Summary statistics
    total_time = sum(r.duration_ms for r in results)
    avg_throughput = sum(r.throughput_kb_per_sec for r in results) / len(results)
    print(f"\nTotal benchmark time: {total_time:.2f} ms")
    print(f"Average throughput: {avg_throughput:.1f} KB/s")
    print(f"Rules tested: {results[0].num_rules}")


def main() -> None:
    """Run all benchmarks."""
    results: list[BenchmarkResult] = []
    
    # Markdown benchmarks
    for size_kb in [1, 10, 50, 100]:
        content = generate_markdown_content(size_kb)
        result = run_benchmark(
            name=f"markdown_{size_kb}kb",
            content=content,
            filename="benchmark.md",
        )
        results.append(result)
    
    # Python benchmarks
    for size_kb in [1, 10, 50]:
        content = generate_python_content(size_kb)
        result = run_benchmark(
            name=f"python_{size_kb}kb",
            content=content,
            filename="benchmark.py",
        )
        results.append(result)
    
    # Empty content (baseline)
    result = run_benchmark(
        name="empty_file",
        content="",
        filename="empty.md",
    )
    results.append(result)
    
    # Single line
    result = run_benchmark(
        name="single_line",
        content="Hello, world!",
        filename="single.md",
    )
    results.append(result)
    
    print_results(results)


if __name__ == "__main__":
    main()
