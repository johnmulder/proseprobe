"""Tests for explicitly enabled same-document fragment validation."""

from pathlib import Path

import pytest

from proseprobe.config import Config, ConfigError, load_config
from proseprobe.rules import markup
from proseprobe.rules.base import Confidence, Severity


def test_fragment_renderer_configuration_is_explicit(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[tool.proseprobe]\nmarkdown_anchor_style = "github"\n')
    config = load_config(path)
    assert config.markdown_anchor_style == "github"


@pytest.mark.parametrize("value", ['"unknown"', "true", "5"])
def test_invalid_fragment_renderer_is_a_configuration_error(
    tmp_path: Path, value: str
) -> None:
    path = tmp_path / "config.toml"
    path.write_text(f"[tool.proseprobe]\nmarkdown_anchor_style = {value}\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_fragment_rule_is_disabled_by_default() -> None:
    assert (
        markup.SameDocumentFragmentRule().check("[installation](#install)", "case.md")
        == []
    )


def test_disabled_renderer_is_not_an_active_rule() -> None:
    assert Config().markdown_anchor_style == "off"
    assert markup.SameDocumentFragmentRule().severity is Severity.OFF
    assert markup.SameDocumentFragmentRule("github").severity is Severity.INFO
    assert (
        markup.SameDocumentFragmentRule("github").default_confidence is Confidence.HIGH
    )


def test_unresolved_fragment_has_exact_destination_span() -> None:
    source = "[installation](#install)"
    [issue] = markup.SameDocumentFragmentRule("github").check(source, "case.md")
    assert issue.rule_id == "M011"
    assert (issue.line, issue.column, issue.end_column) == (1, 16, 24)
    assert source[issue.column - 1 : issue.end_column - 1] == "#install"


@pytest.mark.parametrize(
    "source",
    [
        "# Install\n[installation](#install)",
        "Install\n=======\n[installation](#install)",
        "# Install\n# Install\n[second](#install-1)",
        "# Install\n# Install\n# Install-1\n[collision](#install-1-1)",
        "# Café\n[unicode](#caf%C3%A9)",
        "# Use `code` and **bold**\n[formatting](#use-code-and-bold)",
        "# _Install_\n[formatting](#install)",
        '<a name="Install"></a>\n[custom](#Install)',
        '<div id="install"></div>\n[custom](#install)',
        '<a id="literal(parenthesis)"></a>\n[custom](<#literal(parenthesis)> "title")',
        '# Install\n[title](#install "Installation guide")',
        "> # Install\n> [quote](#install)",
        "[external](https://example.com/#missing)\n[cross](other.md#missing)\n[top](#)\n![image](#missing)",
        "```md\n[example](#missing)\n```\n`[example](#missing)`",
        '---\nlabel: "[example](#missing)"\n---',
        'import {Heading} from "./heading"\n[generated](#missing)',
        "{% include heading.md %}\n[generated](#missing)",
    ],
)
def test_supported_targets_and_excluded_contexts_are_clean(source: str) -> None:
    assert markup.SameDocumentFragmentRule("github").check(source, "case.md") == []


def test_reference_definition_is_reported_once_for_multiple_uses() -> None:
    source = "[one][target]\n[two][target]\n[target]: #install\n"
    [issue] = markup.SameDocumentFragmentRule("github").check(source, "case.md")
    assert issue.line == 3
    assert source.splitlines()[2][issue.column - 1 : issue.end_column - 1] == "#install"


def test_inline_anchor_example_does_not_create_a_target() -> None:
    source = '`<a id="install"></a>`\n[installation](#install)'
    [issue] = markup.SameDocumentFragmentRule("github").check(source, "case.md")
    assert issue.line == 2


@pytest.mark.parametrize(
    "source",
    [
        '<a id="Install"></a>\n[wrong case](#install)',
        '```html\n<a id="install"></a>\n```\n[missing](#install)',
        "---\nanchor: '<a id=\"install\"></a>'\n---\n[missing](#install)",
        r'\<a id="install"></a>' + "\n[missing](#install)",
        '<div name="install"></div>\n[missing](#install)',
    ],
)
def test_anchor_case_and_example_contexts_do_not_hide_missing_targets(
    source: str,
) -> None:
    [issue] = markup.SameDocumentFragmentRule("github").check(source, "case.md")
    assert issue.rule_id == "M011"


@pytest.mark.parametrize(
    "source",
    [
        '<a id="install"></a>\n# Install\n# Install\n[second](#install-1)',
        '<a id="a/b"></a>\n[encoded](#a%2Fb)',
        '<a id="a&amp;b"></a>\n[encoded](#a%26b)',
        "# Use `List<T>`\n[type](#use-listt)",
        "# <span>Install</span>\n[formatting](#install)",
        "# `__file__`\n[code](#__file__)",
        '# Use [API](https://example.com/a "Title")\n[formatting](#use-api)',
        "# Use [API][ref]\n[ref]: https://example.com\n[formatting](#use-api)",
        "<a id=\"literal(parenthesis)\"></a>\n[escaped](#literal\\(parenthesis\\) 'Title')",
        "# Install\n[title](#install (Installation guide))",
        "# Install\n[unused]: #missing",
        "![only image][ref]\n[ref]: #missing",
        "# Install\n[![image](#missing)](#install)",
        "Text <!-- [example](#missing) --> after comment.",
        "[example][ref] text <!-- [example][hidden] -->\n[ref]: https://example.com\n[hidden]: #missing",
        "[example][ref]\n[ref]: #missing invalid-title",
    ],
)
def test_fragment_boundaries_and_displayed_heading_text(source: str) -> None:
    assert markup.SameDocumentFragmentRule("github").check(source, "case.md") == []


@pytest.mark.parametrize(
    "link",
    [
        '[missing](<#literal(parenthesis)> "Title")',
        "[missing](#literal\\(parenthesis\\) 'Title')",
        '[missing](#literal(parenthesis) "Title")',
    ],
)
def test_complex_destination_spans_exclude_delimiters_and_titles(link: str) -> None:
    [issue] = markup.SameDocumentFragmentRule("github").check(link, "case.md")
    actual = link[issue.column - 1 : issue.end_column - 1]
    assert actual in {"#literal(parenthesis)", r"#literal\(parenthesis\)"}


def test_escaped_image_marker_keeps_an_active_reference_link() -> None:
    source = r"\![link][ref]" + "\n[ref]: #missing"
    [issue] = markup.SameDocumentFragmentRule("github").check(source, "case.md")
    assert issue.line == 2


@pytest.mark.parametrize(
    "source",
    [
        "# Install\n[reference][ref]\n[ref]: https://example.com/[example](#missing)",
        "# Install\n[reference][ref]\n[ref]: [example](#missing)",
    ],
)
def test_reference_destinations_do_not_contain_nested_inline_links(source: str) -> None:
    assert markup.SameDocumentFragmentRule("github").check(source, "case.md") == []


@pytest.mark.parametrize(
    "source",
    [
        "# Install\n[escaped](\\#install)",
        "# Install\n[entity](&#35;install)",
    ],
)
def test_fragment_hash_escapes_are_resolved_after_markdown_parsing(source: str) -> None:
    assert markup.SameDocumentFragmentRule("github").check(source, "case.md") == []


def test_dynamic_syntax_inside_code_does_not_disable_a_static_document() -> None:
    source = '```mdx\nimport {Heading} from "./heading"\n```\n[missing](#missing)'
    [issue] = markup.SameDocumentFragmentRule("github").check(source, "case.md")
    assert issue.line == 4


@pytest.mark.parametrize(
    "source",
    [
        "[unrelated](https://example.com \"<a id='install'>\")\n[missing](#install)",
        '![<span id="install">image</span>](image.png)\n[missing](#install)',
        '![<span id="install">image</span>][ref]\n[missing](#install)\n[ref]: image.png',
        "[unused]: https://example.com \"<a id='install'>\"\n[missing](#install)",
    ],
)
def test_link_titles_and_image_labels_do_not_create_html_targets(source: str) -> None:
    [issue] = markup.SameDocumentFragmentRule("github").check(source, "case.md")
    assert issue.line == 2
