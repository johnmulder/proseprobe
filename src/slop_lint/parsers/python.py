"""Python parser for extracting docstrings and comments."""

import ast
import io
import tokenize
from dataclasses import dataclass


@dataclass
class Docstring:
    """A docstring in Python code."""

    content: str
    line: int
    end_line: int
    node_type: str  # "module", "class", "function"


@dataclass
class Comment:
    """A comment in Python code."""

    content: str
    line: int
    column: int
    is_inline: bool


class PythonParser:
    """Parser for Python source files.

    Extracts docstrings and comments for rule checking.
    """

    def __init__(self, content: str) -> None:
        """Initialize parser with content.

        Args:
            content: Python source code.
        """
        self.content = content
        self._lines = content.split("\n")
        self._tree: ast.Module | None = None

    def parse(self) -> bool:
        """Parse the Python source.

        Returns:
            True if parsing succeeded, False otherwise.
        """
        try:
            self._tree = ast.parse(self.content)
            return True
        except SyntaxError:
            return False

    def get_docstrings(self) -> list[Docstring]:
        """Extract all docstrings from the source.

        Returns:
            List of docstrings with positions.
        """
        if self._tree is None:
            return []

        docstrings: list[Docstring] = []

        for node in ast.walk(self._tree):
            if not isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue

            if not getattr(node, "body", None):
                continue

            first = node.body[0]
            if not isinstance(first, ast.Expr):
                continue
            if not isinstance(first.value, ast.Constant):
                continue
            if not isinstance(first.value.value, str):
                continue

            docstring = first.value.value
            if isinstance(node, ast.Module):
                node_type = "module"
            else:
                node_type = "class" if isinstance(node, ast.ClassDef) else "function"

            line = getattr(first, "lineno", 1)
            end_line = getattr(first, "end_lineno", None)
            if end_line is None:
                end_line = line + docstring.count("\n")

            docstrings.append(
                Docstring(
                    content=docstring,
                    line=line,
                    end_line=end_line,
                    node_type=node_type,
                )
            )

        return docstrings

    def get_comments(self) -> list[Comment]:
        """Extract all comments from the source.

        Returns:
            List of comments with positions.
        """
        comments: list[Comment] = []

        try:
            tokens = tokenize.generate_tokens(io.StringIO(self.content).readline)
            for token in tokens:
                if token.type != tokenize.COMMENT:
                    continue

                line_num, col = token.start
                line_text = token.line or ""
                before = line_text[:col]
                is_inline = bool(before.strip())
                comment_text = token.string[1:].strip()
                comments.append(
                    Comment(
                        content=comment_text,
                        line=line_num,
                        column=col + 1,
                        is_inline=is_inline,
                    )
                )
        except (tokenize.TokenError, UnicodeDecodeError):
            return comments

        return comments

    def get_string_literals(self) -> list[tuple[int, int, str]]:
        """Extract string literals (for catching bad patterns in strings).

        Returns:
            List of (line, column, content) tuples.
        """
        if self._tree is None:
            return []

        strings: list[tuple[int, int, str]] = []

        for node in ast.walk(self._tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.append((node.lineno, node.col_offset + 1, node.value))

        return strings
