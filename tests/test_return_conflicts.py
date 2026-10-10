"""Regressions for explicit static return documentation contracts."""

from dataclasses import FrozenInstanceError

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
