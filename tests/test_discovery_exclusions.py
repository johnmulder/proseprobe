"""Regression tests for recursive and anchored discovery exclusions."""

import subprocess
from pathlib import Path

import pytest

from proseprobe.core.linter import FileDiscovery


def _write_files(root: Path, names: list[str]) -> dict[str, Path]:
    files = {name: root / name for name in names}
    for path in files.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n", encoding="utf-8")
    return files


@pytest.mark.parametrize(
    "pattern", [".venv/**", ".venv/", "node_modules/**", "node_modules/"]
)
def test_directory_exclusions_cover_all_depths_without_git(
    tmp_path: Path, pattern: str
) -> None:
    directory = pattern.split("/", 1)[0]
    files = _write_files(
        tmp_path,
        [
            "keep.md",
            f"{directory}/direct.py",
            f"{directory}/lib/package/deep.py",
            f"nested/{directory}/lib/deep.md",
            f"nested/{directory}-other/keep.md",
        ],
    )

    found = FileDiscovery(["*.md", "*.py"], [pattern]).discover([tmp_path])

    assert set(found) == {
        files["keep.md"],
        files[f"nested/{directory}-other/keep.md"],
    }


@pytest.mark.parametrize("pattern", ["/docs/**", "/docs/"])
def test_anchored_directory_exclusion_keeps_nested_namesakes(
    tmp_path: Path, pattern: str
) -> None:
    files = _write_files(
        tmp_path,
        [
            "docs/drop.md",
            "docs/deep/drop.py",
            "nested/docs/keep.md",
            "nested/docs/deep/keep.py",
            "keep.md",
        ],
    )

    found = FileDiscovery(["*.md", "*.py"], [pattern]).discover([tmp_path])

    assert set(found) == {
        files["nested/docs/keep.md"],
        files["nested/docs/deep/keep.py"],
        files["keep.md"],
    }


@pytest.mark.parametrize("anchored", [False, True])
def test_globstar_matches_zero_and_multiple_components(
    tmp_path: Path, anchored: bool
) -> None:
    files = _write_files(
        tmp_path,
        [
            "docs/draft12.md",
            "docs/a/draft23.md",
            "docs/a/b/draft34.md",
            "docs/a/draftx.md",
            "nested/docs/draft45.md",
        ],
    )
    pattern = "/docs/**/draft[0-9]?.md" if anchored else "docs/**/draft[0-9]?.md"

    found = FileDiscovery(["*.md"], [pattern]).discover([tmp_path])

    expected = {files["docs/a/draftx.md"]}
    if anchored:
        expected.add(files["nested/docs/draft45.md"])
    assert set(found) == expected


def test_single_star_does_not_cross_directory_boundaries(tmp_path: Path) -> None:
    files = _write_files(
        tmp_path,
        ["docs/drop.md", "docs/nested/keep.md", "nested/docs/keep.md"],
    )

    found = FileDiscovery(["*.md"], ["/docs/*"]).discover([tmp_path])

    assert set(found) == {
        files["docs/nested/keep.md"],
        files["nested/docs/keep.md"],
    }


def test_anchored_filename_glob_only_matches_at_root(tmp_path: Path) -> None:
    files = _write_files(tmp_path, ["draft1.md", "draft12.md", "nested/draft1.md"])

    found = FileDiscovery(["*.md"], ["/draft?.md"]).discover([tmp_path])

    assert set(found) == {files["draft12.md"], files["nested/draft1.md"]}


@pytest.mark.parametrize("relative_roots", [False, True])
def test_exclusions_are_anchored_at_each_scan_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative_roots: bool
) -> None:
    roots = [tmp_path / "first", tmp_path / "second"]
    expected: set[Path] = set()
    for root in roots:
        files = _write_files(
            root, ["docs/drop.md", "docs/deep/drop.md", "nested/docs/keep.md"]
        )
        expected.add(files["nested/docs/keep.md"])
    monkeypatch.chdir(tmp_path)
    if relative_roots:
        roots = [root.relative_to(tmp_path) for root in roots]

    found = FileDiscovery(["*.md"], ["", " /docs/** ", "  "]).discover(roots)

    assert {path.resolve() for path in found} == expected
    assert len(found) == len(expected)


def test_overlapping_roots_apply_anchoring_without_duplicate_files(
    tmp_path: Path,
) -> None:
    files = _write_files(
        tmp_path,
        [
            "docs/drop.md",
            "nested/docs/drop.md",
            "nested/deeper/docs/keep.md",
            "nested/keep.md",
        ],
    )

    found = FileDiscovery(["*.md"], ["/docs/**"]).discover(
        [tmp_path, tmp_path / "nested"]
    )

    assert set(found) == {
        files["nested/deeper/docs/keep.md"],
        files["nested/keep.md"],
    }
    assert len(found) == 2


def test_explicit_files_bypass_include_and_gitignore_but_respect_exclusions(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("*.py\n", encoding="utf-8")
    files = _write_files(tmp_path, ["src/keep.py", ".venv/lib/package/drop.py"])

    found = FileDiscovery(["*.md"], [".venv/**"]).discover(list(files.values()))

    assert found == [files["src/keep.py"]]


@pytest.mark.parametrize("pattern", ["notes.md/", "notes.md/**"])
def test_directory_exclusion_keeps_same_named_regular_file(
    tmp_path: Path, pattern: str
) -> None:
    files = _write_files(tmp_path, ["notes.md"])
    discovery = FileDiscovery(["*.md"], [pattern])

    assert discovery.discover([tmp_path]) == [files["notes.md"]]
    assert discovery.discover([files["notes.md"]]) == [files["notes.md"]]


def test_recursive_exclusions_coexist_with_gitignore_negation(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("*.md\n!keep.md\n", encoding="utf-8")
    files = _write_files(
        tmp_path,
        ["keep.md", "ignored.md", "docs/deep/keep.md", "nested/docs/keep.md"],
    )

    found = FileDiscovery(["*.md"], ["/docs/**"]).discover([tmp_path])

    assert set(found) == {files["keep.md"], files["nested/docs/keep.md"]}
