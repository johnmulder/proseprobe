"""Benchmark harness regression tests."""

import json
import subprocess
from pathlib import Path

import pytest
from benchmarks import bench_rules
from benchmarks.bench_rules import BenchmarkResult, print_results
from benchmarks.memory_probe import run_probe as run_memory_probe
from benchmarks.startup_probe import run_probe as run_startup_probe

from proseprobe.config import Config, PerFileIgnore
from proseprobe.core.linter import Linter
from proseprobe.parsers import markdown, python
from proseprobe.rules.base import Issue
from proseprobe.rules.grammar import ExcessiveHedgingRule
from proseprobe.rules.vocab import AIVocabularyRule, WordyPhraseRule


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
    assert "files/s" in output


@pytest.mark.parametrize("filename", ["sample.md", "sample.py"])
@pytest.mark.parametrize("use_linter", [False, True])
def test_shared_prose_rules_reuse_parsers_in_direct_and_linter_calls(
    monkeypatch: pytest.MonkeyPatch, filename: str, use_linter: bool
) -> None:
    content = "The retry may possibly delve in order to recover."
    if filename.endswith(".py"):
        content = f'"""{content}"""'
    parser_class = (
        python.PythonParser if filename.endswith(".py") else markdown.MarkdownParser
    )
    original_init = parser_class.__init__
    constructions = 0

    def count_init(self: object, source: str) -> None:
        nonlocal constructions
        constructions += 1
        original_init(self, source)

    monkeypatch.setattr(parser_class, "__init__", count_init)
    rules = [AIVocabularyRule(), WordyPhraseRule(), ExcessiveHedgingRule()]
    linter = Linter(Config(select=["V001", "V009", "G002"]))
    for rule in rules:
        linter.register_rule(rule)

    def check() -> None:
        if use_linter:
            linter.check_content(content, Path(filename))
        else:
            for rule in rules:
                rule.check(content, filename)

    markdown.clear_parser_cache()
    python.clear_parser_cache()
    check()
    assert constructions == 1
    check()
    assert constructions == 1
    markdown.clear_parser_cache()
    python.clear_parser_cache()
    check()
    assert constructions == 2


def test_scan_benchmark_uses_policy_and_actual_utf8_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    documents = {
        Path("notes.md"): "Café operators delve in order to retry with a key.\n",
        Path("client.py"): '"""This delves into retries."""\n',
        Path("ignored.py"): '"""This delves into setup."""\n',
    }
    config = Config(
        select=["V001", "V009", "V015"],
        severity="warning",
        min_confidence="high",
        per_file_ignores=[PerFileIgnore(pattern="ignored.py", ignore=["V001"])],
    )
    monkeypatch.setattr(
        bench_rules.time, "perf_counter", iter([0.0, 0.2, 1.0, 1.4, 2.0, 2.3]).__next__
    )

    result = bench_rules.run_scan_benchmark("unicode", documents, config, iterations=3)

    assert result.measurement == "in-memory production scan"
    assert result.content_size == sum(
        len(text.encode("utf-8")) for text in documents.values()
    )
    assert result.files_checked == 3
    assert result.num_rules == 1
    assert result.issues_found == 2
    assert result.duration_ms == pytest.approx(300.0)
    assert result.min_duration_ms == pytest.approx(200.0)
    assert result.max_duration_ms == pytest.approx(400.0)
    assert result.throughput_kb_per_sec == pytest.approx(
        result.content_size / 1024 / 0.3
    )
    assert result.files_per_sec == pytest.approx(10.0)
    assert result.policy["min_confidence"] == "high"
    assert len(result.workload_sha256) == 64
    assert result.environment["python"]


@pytest.mark.parametrize("cache_state", ["warm", "cleared"])
def test_scan_benchmark_controls_parser_cache_state(
    monkeypatch: pytest.MonkeyPatch, cache_state: str
) -> None:
    original_init = markdown.MarkdownParser.__init__
    constructions = 0

    def count_init(self: markdown.MarkdownParser, source: str) -> None:
        nonlocal constructions
        constructions += 1
        original_init(self, source)

    monkeypatch.setattr(markdown.MarkdownParser, "__init__", count_init)

    result = bench_rules.run_scan_benchmark(
        "cache",
        {Path("notes.md"): "This delves into setup."},
        Config(select=["V001"]),
        iterations=2,
        cache_state=cache_state,
    )

    assert result.cache_state == cache_state
    assert constructions == (1 if cache_state == "warm" else 3)


def test_directory_benchmark_includes_discovery_reading_and_filtering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("/docs/ignored.md\n")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "notes.md").write_text("Café operators delve into setup.\n")
    (docs / "client.py").write_text('"""This delves into setup."""\n')
    (docs / "clean.md").write_text("Read the setup guide.\n")
    (docs / "ignored.md").write_text("This delves into setup.\n")
    monkeypatch.chdir(tmp_path)
    original_read = Linter.check_file
    reads: list[Path] = []

    def record_read(self: Linter, path: Path):  # type: ignore[no-untyped-def]
        reads.append(path)
        return original_read(self, path)

    monkeypatch.setattr(Linter, "check_file", record_read)
    config = Config(select=["V001"], min_confidence="high")
    result = bench_rules.run_workspace_benchmark(
        "directory", [Path("docs")], config, iterations=2
    )
    documents = {
        file: file.read_text(encoding="utf-8")
        for file in docs.iterdir()
        if file.name != "ignored.md"
    }
    memory = bench_rules.run_scan_benchmark("memory", documents, config, iterations=2)

    assert result.measurement == "directory discovery/read/production scan"
    assert set(reads) == {
        Path("docs/notes.md"),
        Path("docs/client.py"),
        Path("docs/clean.md"),
    }
    assert len(reads) == 9
    assert result.files_checked == memory.files_checked == 3
    assert result.issues_found == memory.issues_found == 2
    assert result.content_size == memory.content_size
    assert result.workload_sha256 == memory.workload_sha256


def test_cold_cli_benchmark_includes_json_serialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "notes.md").write_text("Café operators delve into setup.\n")
    config = tmp_path / "benchmark.toml"
    config.write_text('select = ["V001"]\nmin_confidence = "high"\n')
    commands: list[list[str]] = []
    original_run = subprocess.run

    def fake_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if "-m" not in command:
            return original_run(command, **kwargs)
        commands.append(command)
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=json.dumps(
                {
                    "summary": {"files_checked": 1, "total_issues": 1},
                    "files": [
                        {
                            "path": str(root / "notes.md"),
                            "issues": [
                                {
                                    "rule_id": "V001",
                                    "message": "Vocabulary",
                                    "line": 1,
                                    "column": 16,
                                    "end_line": None,
                                    "end_column": 21,
                                    "severity": "warning",
                                    "confidence": "high",
                                    "suggestion": None,
                                }
                            ],
                        }
                    ],
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(bench_rules.subprocess, "run", fake_run)
    monkeypatch.setattr(
        bench_rules.time, "perf_counter", iter([0.0, 0.1, 1.0, 1.2]).__next__
    )

    result = bench_rules.run_cli_benchmark("cold", [root], config, iterations=2)

    assert result.measurement == "cold subprocess CLI with JSON serialization"
    assert result.cache_state == "new process"
    assert result.duration_ms == pytest.approx(150.0)
    assert result.files_checked == 1
    assert result.issues_found == 1
    assert len(commands) == 2
    assert all(command[-2:] == ["--format", "json"] for command in commands)
    assert all(str(config) in command and str(root) in command for command in commands)


def test_direct_benchmark_labels_stress_and_counts_utf8_bytes() -> None:
    result = bench_rules.run_benchmark(
        "direct", "Café operators delve into setup.", "sample.md", iterations=1
    )

    assert result.measurement == "direct-rule stress"
    assert result.content_size == len("Café operators delve into setup.".encode())


def test_workspace_fixture_distinguishes_cache_pressure_and_repeated_content(
    tmp_path: Path,
) -> None:
    distinct = tmp_path / "distinct"
    repeated = tmp_path / "repeated"
    bench_rules.write_workspace(distinct, small_files=40)
    bench_rules.write_workspace(repeated, small_files=40, repeated=True)
    distinct_texts = {file.read_text() for file in (distinct / "small").iterdir()}
    repeated_texts = {file.read_text() for file in (repeated / "small").iterdir()}

    assert len(distinct_texts) == 40
    assert len(repeated_texts) == 2
    assert (distinct / "code-heavy.md").stat().st_size > 1024
    assert (distinct / "code-heavy.py").stat().st_size > 1024
    assert (distinct / ".gitignore").read_text() == "/ignored/\n"


def test_workload_checksum_does_not_depend_on_temporary_directory(
    tmp_path: Path,
) -> None:
    first = bench_rules.run_scan_benchmark(
        "first", {tmp_path / "a/notes.md": "Café."}, iterations=1
    )
    second = bench_rules.run_scan_benchmark(
        "second", {tmp_path / "b/notes.md": "Café."}, iterations=1
    )
    changed = bench_rules.run_scan_benchmark(
        "changed", {tmp_path / "b/notes.md": "Résumé."}, iterations=1
    )

    assert first.workload_sha256 == second.workload_sha256
    assert first.workload_sha256 != changed.workload_sha256


def test_benchmark_records_runtime_and_complete_diagnostic_identity(
    tmp_path: Path,
) -> None:
    result = bench_rules.run_scan_benchmark(
        "identity",
        {tmp_path / "doc.md": "delve\n"},
        Config(select=["V001"]),
        iterations=1,
    )
    assert len(result.runtime["source_sha256"]) == 64
    assert len(result.diagnostics_sha256) == 64
    assert result.schema_version == 1


@pytest.mark.parametrize(
    "change", ["suggestion", "endpoint", "message", "multiplicity"]
)
def test_diagnostic_identity_preserves_complete_observable_findings(
    tmp_path: Path, change: str
) -> None:
    from dataclasses import replace

    documents = {tmp_path / "doc.md": "delve\n"}
    issue = Issue("V001", "Original message", 1, 1, end_column=6, suggestion="inspect")
    original = bench_rules._diagnostic_identity(
        {tmp_path / "doc.md": [issue]}, documents
    )
    changed = {
        "suggestion": [replace(issue, suggestion="review")],
        "endpoint": [replace(issue, end_column=5)],
        "message": [replace(issue, message="Changed message")],
        "multiplicity": [issue, issue],
    }[change]
    assert (
        bench_rules._diagnostic_identity({tmp_path / "doc.md": changed}, documents)
        != original
    )


def test_diagnostic_identity_is_order_and_relocation_independent(
    tmp_path: Path,
) -> None:
    first = Issue("V001", "First", 1, 1, end_column=6)
    second = Issue("V009", "Second", 2, 1, end_column=5)
    a = tmp_path / "a/doc.md"
    b = tmp_path / "b/doc.md"
    assert bench_rules._diagnostic_identity(
        {a: [first, second]}, {a: "delve\n"}
    ) == bench_rules._diagnostic_identity({b: [second, first]}, {b: "delve\n"})


def test_diagnostic_hashing_stays_outside_timed_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []
    times = iter([0.0, 1.0])

    def clock() -> float:
        events.append("timer")
        return next(times)

    original = bench_rules._diagnostic_identity

    def identity(*args, **kwargs):
        events.append("digest")
        return original(*args, **kwargs)

    monkeypatch.setattr(bench_rules.time, "perf_counter", clock)
    monkeypatch.setattr(bench_rules, "_diagnostic_identity", identity)
    bench_rules.run_scan_benchmark(
        "timing", {Path("doc.md"): "delve\n"}, Config(select=["V001"]), iterations=1
    )
    assert events[-3:] == ["timer", "timer", "digest"]


@pytest.mark.parametrize("change", ["diagnostics", "workload", "newlines"])
def test_benchmark_refuses_changed_behavior_or_equal_size_workload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    source = docs / "doc.md"
    source.write_text("delve\n")
    original = Linter.check
    calls = 0

    def changing(self: Linter, paths: list[Path]):
        nonlocal calls
        calls += 1
        result = original(self, paths)
        if calls == 2:
            if change == "newlines":
                source.write_bytes(b"delve\r\n")
            elif change == "workload":
                source.write_text("plain\n")
            else:
                result.issues_by_file[source][0].message = "Different diagnosis"
        return result

    monkeypatch.setattr(Linter, "check", changing)
    with pytest.raises(RuntimeError, match="changed"):
        bench_rules.run_workspace_benchmark(
            "change", [docs], Config(select=["V001"]), iterations=2
        )


def test_cold_cli_probe_records_actual_child_modules(tmp_path: Path) -> None:
    source = tmp_path / "doc.md"
    source.write_text("delve\n")
    config = tmp_path / "benchmark.toml"
    config.write_text('select = ["V001"]\n')
    result = bench_rules.run_cli_benchmark("child", [source], config, iterations=1)
    assert result.child_runtime["source_sha256"] == result.runtime["source_sha256"]
    assert result.child_module_locations["cli"].endswith("cli.py")


@pytest.mark.parametrize("change", ["runtime", "policy"])
def test_cli_benchmark_rejects_different_child_identity_or_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    source = tmp_path / "doc.md"
    source.write_text("delve\n")
    config = tmp_path / "benchmark.toml"
    config.write_text('select = ["V001"]\n')
    original = bench_rules._probe_cli_identity

    def changed_probe(path: Path):
        probe = original(path)
        if change == "runtime":
            probe["runtime"]["source_sha256"] = "0" * 64
        else:
            probe["policy"]["min_confidence"] = "high"
        return probe

    monkeypatch.setattr(bench_rules, "_probe_cli_identity", changed_probe)
    with pytest.raises(RuntimeError, match=r"child CLI.*differs"):
        bench_rules.run_cli_benchmark("different-child", [source], config, iterations=1)


@pytest.mark.parametrize("iterations", [0, -1])
def test_benchmark_rejects_nonpositive_iterations(iterations: int) -> None:
    with pytest.raises(ValueError, match="iterations must be positive"):
        bench_rules.run_scan_benchmark("invalid", {}, iterations=iterations)


@pytest.mark.parametrize("cache_state", ["new process", "invalid"])
def test_in_memory_benchmark_rejects_misleading_cache_labels(cache_state: str) -> None:
    with pytest.raises(ValueError, match="cache_state must be warm or cleared"):
        bench_rules.run_scan_benchmark(
            "invalid", {}, iterations=1, cache_state=cache_state
        )


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
