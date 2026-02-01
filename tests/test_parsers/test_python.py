"""Tests for Python parser."""

from humanize.parsers.python import PythonParser


class TestPythonParser:
    """Tests for Python source parser."""

    def test_parse_valid_python(self) -> None:
        content = '''
def hello():
    """Say hello."""
    print("Hello")
'''
        parser = PythonParser(content)
        assert parser.parse() is True

    def test_parse_invalid_python(self) -> None:
        content = "def broken("
        parser = PythonParser(content)
        assert parser.parse() is False

    def test_extract_docstrings(self) -> None:
        content = '''
"""Module docstring."""

def func():
    """Function docstring."""
    pass

class MyClass:
    """Class docstring."""
    pass
'''
        parser = PythonParser(content)
        parser.parse()
        docstrings = parser.get_docstrings()

        assert len(docstrings) == 3
        assert any("Module" in d.content for d in docstrings)
        assert any("Function" in d.content for d in docstrings)
        assert any("Class" in d.content for d in docstrings)

    def test_extract_comments(self) -> None:
        content = """
# This is a comment
x = 1  # Inline comment
# Another comment
"""
        parser = PythonParser(content)
        comments = parser.get_comments()

        assert len(comments) >= 2
        assert any(not c.is_inline for c in comments)
        assert any(c.is_inline for c in comments)
