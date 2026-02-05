"""Tests for Python parser."""

from slop_lint.parsers.python import Comment, Docstring, PythonParser


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

    def test_get_docstrings_without_parse(self) -> None:
        """Test get_docstrings returns empty list if not parsed."""
        parser = PythonParser("def foo(): pass")
        # Don't call parse()
        docstrings = parser.get_docstrings()
        assert docstrings == []

    def test_get_string_literals(self) -> None:
        """Test extracting string literals."""
        content = """
x = "hello world"
y = 'another string'
"""
        parser = PythonParser(content)
        parser.parse()
        strings = parser.get_string_literals()

        assert len(strings) >= 2
        assert any("hello world" in s[2] for s in strings)
        assert any("another string" in s[2] for s in strings)

    def test_get_string_literals_without_parse(self) -> None:
        """Test get_string_literals returns empty if not parsed."""
        parser = PythonParser('x = "test"')
        strings = parser.get_string_literals()
        assert strings == []

    def test_async_function_docstring(self) -> None:
        """Test extracting docstrings from async functions."""
        content = '''
async def async_func():
    """Async function docstring."""
    pass
'''
        parser = PythonParser(content)
        parser.parse()
        docstrings = parser.get_docstrings()

        assert len(docstrings) == 1
        assert "Async function" in docstrings[0].content
        assert docstrings[0].node_type == "function"

    def test_multiline_docstring(self) -> None:
        """Test extracting multiline docstrings."""
        content = '''
def func():
    """First line.

    Second paragraph.

    Third paragraph.
    """
    pass
'''
        parser = PythonParser(content)
        parser.parse()
        docstrings = parser.get_docstrings()

        assert len(docstrings) == 1
        assert docstrings[0].end_line > docstrings[0].line

    def test_comment_in_string_not_extracted(self) -> None:
        """Test that # inside strings is not extracted as comment."""
        content = """
url = "https://example.com#anchor"
"""
        parser = PythonParser(content)
        comments = parser.get_comments()

        # Should not extract # from inside the string
        assert not any("#anchor" in c.content for c in comments)

    def test_multiple_inline_comments(self) -> None:
        """Test extracting multiple inline comments."""
        content = """
a = 1  # first
b = 2  # second
c = 3  # third
"""
        parser = PythonParser(content)
        comments = parser.get_comments()

        inline = [c for c in comments if c.is_inline]
        assert len(inline) == 3


class TestDocstringDataclass:
    """Tests for Docstring dataclass."""

    def test_create_docstring(self) -> None:
        """Test creating a Docstring instance."""
        doc = Docstring(
            content="Test docstring",
            line=10,
            end_line=12,
            node_type="function",
        )

        assert doc.content == "Test docstring"
        assert doc.line == 10
        assert doc.end_line == 12
        assert doc.node_type == "function"


class TestCommentDataclass:
    """Tests for Comment dataclass."""

    def test_create_comment(self) -> None:
        """Test creating a Comment instance."""
        comment = Comment(
            content="This is a comment",
            line=5,
            column=10,
            is_inline=True,
        )

        assert comment.content == "This is a comment"
        assert comment.line == 5
        assert comment.column == 10
        assert comment.is_inline is True
