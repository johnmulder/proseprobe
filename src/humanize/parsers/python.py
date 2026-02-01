"""Python parser for extracting docstrings and comments."""

import ast
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
            if isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                docstring = ast.get_docstring(node)
                if docstring:
                    # Find the line number of the docstring
                    if isinstance(node, ast.Module):
                        line = 1
                        node_type = "module"
                    else:
                        line = node.lineno + 1  # Docstring is after the def line
                        node_type = (
                            "class" if isinstance(node, ast.ClassDef) else "function"
                        )

                    # Estimate end line based on docstring length
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

        for line_num, line in enumerate(self._lines, start=1):
            stripped = line.strip()

            # Full-line comment
            if stripped.startswith("#"):
                comments.append(
                    Comment(
                        content=stripped[1:].strip(),
                        line=line_num,
                        column=line.index("#") + 1,
                        is_inline=False,
                    )
                )
            # Inline comment (simple heuristic)
            elif "#" in line:
                # Check if # is in a string - simple check
                comment_idx = line.find("#")
                before = line[:comment_idx]
                # Very basic check - not inside quotes
                if before.count('"') % 2 == 0 and before.count("'") % 2 == 0:
                    comments.append(
                        Comment(
                            content=line[comment_idx + 1 :].strip(),
                            line=line_num,
                            column=comment_idx + 1,
                            is_inline=True,
                        )
                    )

        return comments

    def get_string_literals(self) -> list[tuple[int, int, str]]:
        """Extract string literals (for catching AI patterns in strings).

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
