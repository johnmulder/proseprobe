"""Generate repetitive rule documentation from canonical metadata."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

from proseprobe.rules import get_rule_metadata

_CATEGORY_ORDER = ("V", "S", "T", "G", "C", "M")
_CATEGORY_DESCRIPTIONS = {
    "V": "Overused and clichéd words and phrases",
    "S": "Organizational patterns",
    "T": "Typographic issues",
    "G": "Grammatical patterns",
    "C": "Python docstring/comment issues",
    "M": "Markdown artifacts",
}
_MARKER_PATTERN = re.compile(r"<!-- rule-docs:[a-z-]+:(?:start|end) -->")


class MarkerError(ValueError):
    """Raised when generated-block markers are malformed."""


def render_category_table() -> str:
    """Render category counts from registered rule metadata."""
    metadata = get_rule_metadata()
    counts = Counter(item.id[0] for item in metadata)
    categories = {item.id[0]: item.category for item in metadata}
    rows = [
        "| Prefix | Category | Rules | Description |",
        "|--------|----------|-------|-------------|",
    ]
    rows.extend(
        f"| `{prefix}` | {categories[prefix]} | {counts[prefix]} | "
        f"{_CATEGORY_DESCRIPTIONS[prefix]} |"
        for prefix in _CATEGORY_ORDER
    )
    rows.append(f"| **Total** | | **{len(metadata)}** | |")
    return "\n".join(rows)


def render_rule_inventory() -> str:
    """Render a compact inventory of every registered rule."""
    rows = [
        "| ID | Name | Category | Severity | Confidence | Context | Configuration |",
        "|----|------|----------|----------|------------|---------|---------------|",
    ]
    ordered = sorted(
        get_rule_metadata(),
        key=lambda item: (_CATEGORY_ORDER.index(item.id[0]), item.id),
    )
    for item in ordered:
        context = f"{', '.join(item.applies_to)} / {item.content_scope}"
        config = f"`{item.config_key}`" if item.config_key else "—"
        rows.append(
            f"| `{item.id}` | {item.name} | {item.category} | "
            f"{item.default_severity.value} | {item.default_confidence.value} | "
            f"{context} | {config} |"
        )
    return "\n".join(rows)


def _replace_generated_block(text: str, marker: str, content: str) -> str:
    """Replace one generated block, rejecting malformed marker structure."""
    start_marker = f"<!-- rule-docs:{marker}:start -->"
    end_marker = f"<!-- rule-docs:{marker}:end -->"
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise MarkerError(f"expected exactly one {marker!r} marker pair")

    start = text.index(start_marker)
    end = text.index(end_marker)
    if start >= end:
        raise MarkerError(f"reversed {marker!r} markers")

    content_start = start + len(start_marker)
    if _MARKER_PATTERN.search(text[content_start:end]):
        raise MarkerError(f"nested marker inside {marker!r} block")

    return f"{text[:content_start]}\n\n{content.rstrip()}\n\n{text[end:]}"


_GENERATED_BLOCKS: dict[str, tuple[tuple[str, Callable[[], str]], ...]] = {
    "README.md": (("categories", render_category_table),),
    "SPEC.md": (("categories", render_category_table),),
    "docs/rules.md": (("inventory", render_rule_inventory),),
}


def synchronize_rule_docs(root: Path, *, write: bool) -> tuple[str, ...]:
    """Return stale paths and optionally replace their generated blocks."""
    changed: list[str] = []
    for relative_path, blocks in _GENERATED_BLOCKS.items():
        path = root / relative_path
        original = path.read_text(encoding="utf-8")
        generated = original
        for marker, renderer in blocks:
            generated = _replace_generated_block(generated, marker, renderer())
        if generated == original:
            continue
        changed.append(relative_path)
        if write:
            path.write_text(generated, encoding="utf-8", newline="\n")
    return tuple(changed)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: Sequence[str] | None = None) -> int:
    """Check or update generated rule documentation."""
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check", action="store_true", help="fail on stale docs")
    actions.add_argument("--write", action="store_true", help="update stale docs")
    args = parser.parse_args(argv)

    try:
        changed = synchronize_rule_docs(_project_root(), write=args.write)
    except (MarkerError, OSError) as exc:
        print(f"Rule documentation error: {exc}", file=sys.stderr)
        return 2

    if args.write:
        if changed:
            print(f"Updated rule documentation: {', '.join(changed)}")
        else:
            print("Rule documentation is current")
        return 0
    if changed:
        print(f"Stale rule documentation: {', '.join(changed)}", file=sys.stderr)
        return 1

    print("Rule documentation is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
