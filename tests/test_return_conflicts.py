"""Regressions for explicit static return documentation contracts."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from proseprobe.parsers.python import PythonParser


@pytest.mark.parametrize(
    ("source", "owner", "line", "column"),
    [
        ('def read() -> None:\n    """Read input."""\n', "read", 1, 15),
        ('def café() -> None:\n    """Read input."""\n', "café", 1, 15),
        ('async def read() -> None:\n    """Read input."""\n', "read", 1, 21),
        (
            'def outer():\n    def read() -> None:\n        """Read input."""\n',
            "read",
            2,
            19,
        ),
    ],
)
def test_return_annotation_metadata_keeps_owner_and_character_span(
    source: str, owner: str, line: int, column: int
) -> None:
    parser = PythonParser(source)
    assert parser.parse()
    [doc] = parser.get_docstrings()
    annotation = doc.return_annotation
    assert annotation is not None
    assert doc.owner_name == owner
    assert annotation.name == "None"
    assert annotation.span == (line, column, line, column + 4)
    assert source.splitlines()[line - 1][column - 1 : column + 3] == "None"
    with pytest.raises(FrozenInstanceError):
        annotation.name = "int"


@pytest.mark.parametrize(
    ("annotation", "body"),
    [
        ("", "return None"),
        (" -> int", "return 1"),
        (' -> "None"', "return None"),
        (" -> None | int", "return None"),
        (" -> None", "yield 1"),
    ],
)
def test_return_annotation_metadata_skips_unresolved_and_generator_contracts(
    annotation: str, body: str
) -> None:
    parser = PythonParser(
        f'def read(){annotation}:\n    """Read input."""\n    {body}\n'
    )
    assert parser.parse()
    [doc] = parser.get_docstrings()
    assert doc.return_annotation is None


def test_nested_generator_does_not_change_the_owning_return_annotation() -> None:
    parser = PythonParser('''\
def read() -> None:
    """Read input."""
    def items():
        yield 1
    return None
''')
    assert parser.parse()
    [doc] = parser.get_docstrings()
    assert doc.return_annotation is not None
    assert doc.return_annotation.name == "None"


@pytest.mark.parametrize("prefix", ["def", "async def"])
def test_explicit_return_documentation_conflict_has_a_physical_span(
    prefix: str,
) -> None:
    from proseprobe.rules.code import ExplicitReturnTypeConflictRule

    source = f'{prefix} café() -> None:\n    """:rtype: int"""\n    return None\n'
    [issue] = ExplicitReturnTypeConflictRule().check(source, "doc.py")
    assert (issue.rule_id, issue.line, issue.column, issue.end_column) == (
        "C010",
        2,
        16,
        19,
    )
    assert source.splitlines()[1][issue.column - 1 : issue.end_column - 1] == "int"
    assert issue.severity.value == "info"
    assert issue.confidence.value == "medium"
    assert "None" in issue.message
    assert "int" in issue.message
    assert issue.suggestion == "Check both explicit return declarations"


@pytest.mark.parametrize(
    "source",
    [
        'def read() -> None:\n    """:rtype: None"""\n',
        'def read():\n    """:rtype: int"""\n',
        'def read() -> int:\n    """:rtype: None"""\n',
        'def read() -> None:\n    """:rtype: str"""\n',
        'def read() -> None:\n    """:rtype: int | None"""\n',
        'def read() -> None:\n    """:rtype: Optional[int]"""\n',
        'def read() -> None:\n    """:rtype: integer"""\n',
        'def read() -> None:\n    """:rtype: \'int\'"""\n',
        'def read() -> None:\n    """:rtype: int\n    :rtype: int\n    """\n',
        'def read() -> None:\n    """:rtype: int\n    :rtype: None\n    """\n',
        'def read() -> None:\n    """Returns::\n\n        :rtype: int\n    """\n',
        'def read() -> None:\n    """.. code-block:: python\n\n        :rtype: int\n    """\n',
        'def read() -> None:\n    """```python\n    :rtype: int\n    ```\n    """\n',
        'def read() -> None:\n    """>>> example()\n    :rtype: int\n    """\n',
        'def read() -> None:\n    """Example = ":rtype: int"\n    """\n',
        'def read() -> None:\n    """:rtype: int\n        | None\n    """\n',
        'def read() -> None:\n    """Read input."""\n    example = ":rtype: int"\n',
        '@decorate\ndef read() -> None:\n    """:rtype: int"""\n',
        '@overload\ndef read() -> None:\n    """:rtype: int"""\n',
        'def read() -> None:\n    """:rtype: int"""\n    yield 1\n',
        'def read() -> None:\n    """:rtype: int"""\n  invalid\n',
        '""":rtype: int"""\ndef read() -> None:\n    """Read input."""\n',
        'class Reader:\n    """:rtype: int"""\n    def read(self) -> None:\n        """Read input."""\n',
    ],
)
def test_unresolved_literal_and_compatible_return_declarations_are_skipped(
    source: str,
) -> None:
    from proseprobe.rules.code import ExplicitReturnTypeConflictRule

    assert ExplicitReturnTypeConflictRule().check(source, "doc.py") == []


@pytest.mark.parametrize(
    "binding",
    [
        "int = str",
        "def int(): pass",
        "class int: pass",
        "from package import int",
        "from package import str as int",
        "from package import *",
        "def another(int): pass",
        "try: pass\nexcept Exception as int: pass",
        "match value:\n    case int: pass",
        "globals()['int'] = str",
        "exec('int = str')",
        "import builtins\nbuiltins.int = str",
        "import builtins as b\nb.__dict__['int'] = str",
    ],
)
def test_documented_builtin_must_have_an_unresolved_binding_guard(binding: str) -> None:
    from proseprobe.rules.code import ExplicitReturnTypeConflictRule

    source = binding + '\ndef read() -> None:\n    """:rtype: int"""\n'
    assert ExplicitReturnTypeConflictRule().check(source, "doc.py") == []


def test_return_fields_belong_to_their_owning_function() -> None:
    from proseprobe.rules.code import ExplicitReturnTypeConflictRule

    source = '''\
def outer() -> None:
    """:rtype: None"""
    def inner() -> None:
        """:rtype: int"""
        return None
    return None
'''
    [issue] = ExplicitReturnTypeConflictRule().check(source, "doc.py")
    assert issue.line == 4


def test_return_conflict_registration_and_experimental_policy() -> None:
    from proseprobe.config import Config
    from proseprobe.core.policy import prepare_scan
    from proseprobe.profiles import EXPERIMENTAL_RULES, PROFILES
    from proseprobe.rules import get_rule_metadata_by_id

    metadata = get_rule_metadata_by_id("C010")
    assert metadata is not None
    assert metadata.applies_to == ("python",)
    assert metadata.content_scope == "raw"
    assert metadata.profiles == ()
    assert "C010" in EXPERIMENTAL_RULES
    assert all("C010" not in profile.rules for profile in PROFILES.values())
    source = 'def read() -> None:\n    """:rtype: int"""\n'
    _, ordinary, _ = prepare_scan(Config())
    _, selected, _ = prepare_scan(Config(select=["C010"], severity="info"))
    assert not any(
        i.rule_id == "C010" for i in ordinary.check_content(source, Path("doc.py"))
    )
    [issue] = selected.check_content(source, Path("doc.py"))
    assert issue.rule_id == "C010"


@pytest.mark.parametrize("format_name", ["jsonl", "sarif"])
def test_return_conflict_cli_reporters_preserve_character_positions(
    format_name: str,
) -> None:
    import json

    from tests.test_cli import run_cli

    source = 'def café() -> None:\n    """:rtype: int"""\n'
    result = run_cli(
        "check",
        "-",
        "--filename",
        "doc.py",
        "--select",
        "C010",
        "--severity",
        "info",
        "--format",
        format_name,
        stdin=source,
    )
    assert result.exit_code == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    if format_name == "jsonl":
        assert payload["rule_id"] == "C010"
        assert (payload["line"], payload["column"], payload["end_column"]) == (
            2,
            16,
            19,
        )
    else:
        [finding] = payload["runs"][0]["results"]
        assert finding["ruleId"] == "C010"
        region = finding["locations"][0]["physicalLocation"]["region"]
        assert (region["startLine"], region["startColumn"], region["endColumn"]) == (
            2,
            16,
            19,
        )


def test_return_conflict_suppression_confidence_severity_and_baseline(
    tmp_path: Path,
) -> None:
    from proseprobe.config import Config
    from proseprobe.core.policy import prepare_scan
    from tests.test_cli import run_cli

    source = 'def read() -> None:\n    """:rtype: int"""\n'
    _, disabled, _ = prepare_scan(
        Config(select=["C010"], severity_overrides={"C010": "off"})
    )
    assert disabled.check_content(source, Path("doc.py")) == []
    _, selected, _ = prepare_scan(Config(select=["C010"], severity="info"))
    suppressed = source.replace('int"""', 'int"""  # proseprobe: ignore=C010')
    assert selected.check_content(suppressed, Path("doc.py")) == []
    high = run_cli(
        "check",
        "-",
        "--filename",
        "doc.py",
        "--select",
        "C010",
        "--severity",
        "info",
        "--min-confidence",
        "high",
        "--format",
        "jsonl",
        stdin=source,
    )
    assert high.exit_code == 0
    assert high.stdout == ""
    path = tmp_path / "doc.py"
    path.write_text(source)
    baseline = tmp_path / "accepted.json"
    generated = run_cli(
        "check",
        str(path),
        "--select",
        "C010",
        "--severity",
        "info",
        "--generate-baseline",
        "--baseline",
        str(baseline),
    )
    checked = run_cli(
        "check",
        str(path),
        "--select",
        "C010",
        "--severity",
        "info",
        "--baseline",
        str(baseline),
        "--format",
        "jsonl",
    )
    assert generated.exit_code == 0
    assert checked.exit_code == 0
    assert checked.stdout == ""
    explained = run_cli("explain", "C010")
    assert explained.exit_code == 0
    assert "Explicit Return Type Conflict" in explained.stdout


@pytest.mark.parametrize("wrapper", ["classmethod", "staticmethod"])
def test_return_conflict_skips_rebound_builtin_decorator_names(wrapper: str) -> None:
    from proseprobe.rules.code import ExplicitReturnTypeConflictRule

    source = (
        f"{wrapper} = transform_contract\n"
        f"class Reader:\n    @{wrapper}\n    def read() -> None:\n"
        '        """:rtype: int"""\n'
    )
    assert ExplicitReturnTypeConflictRule().check(source, "doc.py") == []


@pytest.mark.parametrize("wrapper", ["classmethod", "staticmethod"])
def test_return_conflict_retains_unshadowed_builtin_decorators(wrapper: str) -> None:
    from proseprobe.rules.code import ExplicitReturnTypeConflictRule

    source = (
        f"class Reader:\n    @{wrapper}\n    def read() -> None:\n"
        '        """:rtype: int"""\n'
    )
    [issue] = ExplicitReturnTypeConflictRule().check(source, "doc.py")
    assert issue.line == 4
