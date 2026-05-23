"""Benchmark harness regression tests."""

from benchmarks.bench_rules import BenchmarkResult, print_results


def test_benchmark_output_uses_project_name(capsys) -> None:  # type: ignore[no-untyped-def]
    """Benchmark output should use current project naming and summary fields."""
    result = BenchmarkResult(
        name="sample",
        content_size=1024,
        num_rules=59,
        duration_ms=10.0,
        issues_found=1,
        throughput_kb_per_sec=100.0,
    )

    print_results([result])

    output = capsys.readouterr().out
    assert "SLOP-LINT BENCHMARK RESULTS" in output
    assert "HUMANIZE" not in output
    assert "Files/sec estimate" in output
