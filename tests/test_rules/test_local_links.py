"""Tests for explicit project-local Markdown file and fragment checks."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock, get_ident

import pytest

from proseprobe.config import Config
from proseprobe.core.linter import Linter
from proseprobe.rules import markup
from proseprobe.rules.base import Confidence, Issue, Rule, Severity


def project_rule(
    root: Path, *, renderer: str = "off", exclude: list[str] | None = None
) -> markup.LocalMarkdownLinkRule:
    return markup.LocalMarkdownLinkRule(True, str(root), renderer, exclude or [])


def test_missing_file_has_destination_span_and_advisory_metadata(
    tmp_path: Path,
) -> None:
    source = "[Install](setup.md#install)\n"

    [issue] = project_rule(tmp_path).check(source, str(tmp_path / "index.md"))

    assert issue.rule_id == "M012"
    assert issue.message == "No local Markdown file for 'setup.md#install'"
    assert source[issue.column - 1 : issue.end_column - 1] == "setup.md#install"
    assert issue.severity is Severity.INFO
    assert issue.confidence is Confidence.MEDIUM


def test_present_sibling_and_nested_parent_link_stay_inside_root(
    tmp_path: Path,
) -> None:
    (tmp_path / "setup.md").write_text("# Install\n")
    nested = tmp_path / "docs"
    nested.mkdir()
    rule = project_rule(tmp_path)

    assert rule.check("[Install](setup.md)", str(tmp_path / "index.md")) == []
    assert rule.check("[Install](../setup.md)", str(nested / "index.md")) == []


def test_relative_or_outside_virtual_filename_has_no_project_context(
    tmp_path: Path,
) -> None:
    rule = project_rule(tmp_path)

    assert rule.check("[Install](setup.md)", "virtual.md") == []
    assert rule.check("[Install](setup.md)", str(tmp_path.parent / "outside.md")) == []


@pytest.mark.parametrize(
    "destination",
    [
        "../outside.md",
        "/outside.md",
        "https://example.com/setup.md",
        "//example.com/setup.md",
        "mailto:writer@example.com",
        "setup.md?version=1",
        "setup.md?",
        "install",
        "setup.mdx",
        "a%2fsetup.md",
        "a%5csetup.md",
        "bad%GG.md",
        "bad%FF.md",
        "bad%00.md",
    ],
)
def test_unsupported_target_has_no_finding_or_content_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, destination: str
) -> None:
    def forbidden_read(_path: Path, *_args: object, **_kwargs: object) -> str:
        raise AssertionError("unsupported target must not be read")

    monkeypatch.setattr(Path, "read_text", forbidden_read)

    assert (
        project_rule(tmp_path, renderer="github").check(
            f"[Install]({destination})", str(tmp_path / "index.md")
        )
        == []
    )


def test_symlink_escape_has_no_content_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text("# Install\n")
    (tmp_path / "escape.md").symlink_to(outside)

    def forbidden_read(_path: Path, *_args: object, **_kwargs: object) -> str:
        raise AssertionError("outside-root target must not be read")

    monkeypatch.setattr(Path, "read_text", forbidden_read)

    assert (
        project_rule(tmp_path).check("[Install](escape.md)", str(tmp_path / "index.md"))
        == []
    )


def test_explicit_generated_target_selector_skips_target(tmp_path: Path) -> None:
    assert (
        project_rule(tmp_path, exclude=["generated/**"]).check(
            "[Install](generated/setup.md)", str(tmp_path / "index.md")
        )
        == []
    )


def test_balanced_titles_unicode_spaces_escapes_and_used_references(
    tmp_path: Path,
) -> None:
    source = (
        '[Guide](guide(2).md "Guide title")\n'
        "[Space](<résumé guide.md>)\n"
        "[Escaped](guide\\(3\\).md)\n"
        '[Reference][guide]\n[Repeated][guide]\n\n[guide]: absent.markdown "Reference"\n'
    )

    issues = project_rule(tmp_path).check(source, str(tmp_path / "index.md"))

    assert [issue.line for issue in issues] == [1, 2, 3, 7]
    lines = source.splitlines()
    assert [lines[i.line - 1][i.column - 1 : i.end_column - 1] for i in issues] == [
        "guide(2).md",
        "résumé guide.md",
        "guide\\(3\\).md",
        "absent.markdown",
    ]


def test_images_code_frontmatter_external_and_generated_source_are_skipped(
    tmp_path: Path,
) -> None:
    sources = [
        "![Install](missing.md)",
        "`[Install](missing.md)`",
        "```\n[Install](missing.md)\n```",
        "---\nlink: '[Install](missing.md)'\n---\n",
        "<!-- [Install](missing.md) -->",
        "{{ generated }}\n[Install](missing.md)",
        "{% include guide %}\n[Install](missing.md)",
    ]

    for source in sources:
        assert project_rule(tmp_path).check(source, str(tmp_path / "index.md")) == []


def test_fragments_require_explicit_github_renderer(tmp_path: Path) -> None:
    (tmp_path / "setup.md").write_text('# Install\n# Install\n<a id="Custom"></a>\n')
    source = "[One](setup.md#install) [Two](setup.md#install-1) [ID](setup.md#Custom) [Missing](setup.md#absent)"

    assert project_rule(tmp_path).check(source, str(tmp_path / "index.md")) == []
    [issue] = project_rule(tmp_path, renderer="github").check(
        source, str(tmp_path / "index.md")
    )
    assert issue.message == "No GitHub fragment target for 'setup.md#absent'"


def test_unreadable_utf8_and_dynamic_targets_are_advisory_not_missing(
    tmp_path: Path,
) -> None:
    (tmp_path / "bad.md").write_bytes(b"\xff")
    (tmp_path / "generated.md").write_text("{{ generated }}\n# Install\n")
    source = "[Bad](bad.md#install) [Generated](generated.md#install)"

    issues = project_rule(tmp_path, renderer="github").check(
        source, str(tmp_path / "index.md")
    )

    assert len(issues) == 2
    assert all(
        issue.message.startswith("Could not validate local target") for issue in issues
    )


def test_filesystem_context_is_independent_of_cwd_and_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    file = project / "index.md"
    file.write_text("[Missing](setup.md)\n")
    rule = project_rule(project)
    linter = Linter(
        Config(
            local_links=True,
            project_root=str(project),
            select=["M012"],
            exclude=["setup.md"],
        )
    )
    linter.register_rule(rule)
    monkeypatch.chdir(project)
    from_project = linter.check_file(Path("index.md"))
    monkeypatch.chdir(tmp_path)
    from_parent = linter.check_file(Path("project/index.md"))

    assert from_project == from_parent
    assert len(from_parent) == 1
    assert linter.check_content("[Missing](setup.md)", Path("virtual.md")) == []
    assert len(linter.check_content("[Missing](setup.md)", project / "virtual.md")) == 1


def test_target_cache_is_per_scan_and_targets_do_not_count_as_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "setup.md"
    target.write_text("# Install\n")
    source = tmp_path / "index.md"
    source.write_text("[One](setup.md#install) [Two](setup.md#install)\n")
    calls: list[Path] = []
    original_read = Path.read_text

    def record_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == target:
            calls.append(path)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", record_read)
    linter = Linter(
        Config(local_links=True, project_root=str(tmp_path), select=["M012"])
    )
    linter.register_rule(project_rule(tmp_path, renderer="github"))

    first = linter.check([source])
    assert first.files_checked == 1
    assert first.issues_by_file == {}
    assert calls == [target]
    target.write_text("# Other\n")
    second = linter.check([source])
    assert second.files_checked == 1
    assert len(second.issues_by_file[source]) == 2
    assert calls == [target, target]


def test_missing_target_is_cached_once_for_multiple_source_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "missing.md"
    sources = [tmp_path / "one.md", tmp_path / "two.md"]
    for source in sources:
        source.write_text("[Missing](missing.md)\n")
    calls: list[Path] = []
    original_read = Path.read_text

    def record_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == target:
            calls.append(path)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", record_read)
    monkeypatch.setattr("proseprobe.core.linter.os.cpu_count", lambda: 4)
    linter = Linter(
        Config(local_links=True, project_root=str(tmp_path), select=["M012"])
    )
    linter.register_rule(project_rule(tmp_path))

    results = linter.check(sources)

    assert results.files_checked == 2
    assert set(results.issues_by_file) == set(sources)
    assert calls == [target]


def test_concurrent_cache_miss_reads_target_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "setup.md"
    target.write_text("# Install\n")
    rule = project_rule(tmp_path, renderer="github")
    reading = Event()
    release_read = Event()
    second_attempt = Event()
    main_thread = get_ident()
    real_lock = Lock()
    worker_attempts = 0
    calls: list[Path] = []
    original_read = Path.read_text

    class ObservedLock:
        def __enter__(self) -> None:
            nonlocal worker_attempts
            if get_ident() != main_thread:
                worker_attempts += 1
                if worker_attempts == 2:
                    second_attempt.set()
            real_lock.acquire()

        def __exit__(self, *_error: object) -> None:
            real_lock.release()

    def controlled_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == target:
            calls.append(path)
            reading.set()
            if not release_read.wait(5):
                raise AssertionError("test did not release the target read")
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(rule, "_cache_lock", ObservedLock())
    monkeypatch.setattr(Path, "read_text", controlled_read)
    rule.begin_scan()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(
                rule.check, "[One](setup.md#install)", str(tmp_path / "one.md")
            )
            assert reading.wait(5)
            second = pool.submit(
                rule.check, "[Two](setup.md#install)", str(tmp_path / "two.md")
            )
            try:
                assert second_attempt.wait(5)
            finally:
                release_read.set()
            assert first.result() == second.result() == []
    finally:
        release_read.set()
        rule.end_scan()
    assert calls == [target]


def test_permission_failure_is_validation_advisory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "setup.md"
    target.write_text("# Install\n")
    original_read = Path.read_text

    def denied_target(path: Path, *args: object, **kwargs: object) -> str:
        if path == target:
            raise PermissionError("read denied")
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied_target)

    [issue] = project_rule(tmp_path).check(
        "[Install](setup.md)", str(tmp_path / "index.md")
    )

    assert issue.message == "Could not validate local target 'setup.md': read denied"


def test_existing_target_omitted_by_discovery_still_supplies_fragments(
    tmp_path: Path,
) -> None:
    (tmp_path / "setup.md").write_text("# Install\n")
    source = tmp_path / "index.md"
    source.write_text("[Install](setup.md#install)\n")
    linter = Linter(
        Config(
            local_links=True,
            project_root=str(tmp_path),
            exclude=["setup.md"],
            select=["M012"],
        )
    )
    linter.register_rule(project_rule(tmp_path, renderer="github"))

    results = linter.check([tmp_path])

    assert results.files_checked == 1
    assert results.issues_by_file == {}


def test_same_document_fragments_remain_owned_by_m011(tmp_path: Path) -> None:
    source = "# Install\n[Missing](#absent)\n"

    assert (
        project_rule(tmp_path, renderer="github").check(
            source, str(tmp_path / "index.md")
        )
        == []
    )
    assert [
        issue.rule_id
        for issue in markup.SameDocumentFragmentRule("github").check(source, "index.md")
    ] == ["M011"]


def test_project_context_preserves_other_rule_filename_and_report_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "index.md"
    source.write_text("[Missing](setup.md)\n")
    seen: list[str] = []

    class FilenameObserver(Rule):
        id = "M999"

        def check(self, _content: str, filename: str) -> list[Issue]:
            seen.append(filename)
            return []

    config = Config(
        local_links=True, project_root=str(tmp_path), select=["M012", "M999"]
    )
    linter = Linter(config)
    linter.register_rule(project_rule(tmp_path))
    linter.register_rule(FilenameObserver())
    monkeypatch.chdir(tmp_path)

    results = linter.check([Path("index.md")])

    assert seen == ["index.md"]
    assert list(results.issues_by_file) == [Path("index.md")]


def test_disabled_rule_cannot_be_enabled_by_severity_or_read_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rule = markup.LocalMarkdownLinkRule()
    rule.severity = Severity.ERROR

    def forbidden_read(_path: Path, *_args: object, **_kwargs: object) -> str:
        raise AssertionError("disabled local checking must not read a target")

    monkeypatch.setattr(Path, "read_text", forbidden_read)

    assert rule.check("[Missing](setup.md)", str(tmp_path / "index.md")) == []
