"""Benchmark harness regression tests."""

from benchmarks.bench_rules import BenchmarkResult, print_results
from benchmarks.memory_probe import run_probe as run_memory_probe
from benchmarks.startup_probe import run_probe as run_startup_probe


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
    assert "PROSEPROBE BENCHMARK RESULTS" in output
    assert "HUMANIZE" not in output
    assert "Files/sec estimate" in output


def test_memory_probe_accepts_small_workspace(capsys) -> None:  # type: ignore[no-untyped-def]
    """Memory probe should pass for a tiny synthetic workspace."""
    assert run_memory_probe(file_count=2, limit_mb=100) == 0

    output = capsys.readouterr().out
    assert "Memory probe: 2 files" in output


def test_startup_probe_accepts_generous_limit(capsys) -> None:  # type: ignore[no-untyped-def]
    """Startup probe should pass with a generous latency limit."""
    assert run_startup_probe(limit_ms=10_000) == 0

    output = capsys.readouterr().out
    assert "Startup probe:" in output
