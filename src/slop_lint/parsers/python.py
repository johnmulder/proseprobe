"""Python parser for extracting docstrings and comments."""

import ast
import io
import re
import tokenize
from dataclasses import dataclass
from functools import lru_cache

from slop_lint.parsers.prose import (
    InlineSuppression,
    ProseBlock,
    ProseSentence,
    _sentences_from_blocks,
    _validate_suppression_tokens,
)


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
        self._parsed = False
        self._tokens: list[tokenize.TokenInfo] | None = None
        self._docstrings: list[Docstring] | None = None
        self._comments: list[Comment] | None = None
        self._prose_blocks: list[ProseBlock] | None = None
        self._prose_sentences: list[ProseSentence] | None = None
        self._prose_lines: list[tuple[int, str]] | None = None
        self._inline_suppressions: list[InlineSuppression] | None = None

    def parse(self) -> bool:
        """Parse the Python source.

        Returns:
            True if parsing succeeded, False otherwise.
        """
        if self._parsed:
            return self._tree is not None
        self._parsed = True
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

        if self._docstrings is not None:
            return self._docstrings

        docstrings: list[Docstring] = []
        for node, value in self._docstring_nodes():
            docstring = value.value
            if not isinstance(docstring, str):  # pragma: no cover - narrowed above
                continue
            if isinstance(node, ast.Module):
                node_type = "module"
            else:
                node_type = "class" if isinstance(node, ast.ClassDef) else "function"

            line = value.lineno
            end_line = value.end_lineno
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

        self._docstrings = sorted(docstrings, key=lambda doc: doc.line)
        return self._docstrings

    def get_comments(self) -> list[Comment]:
        """Extract all comments from the source.

        Returns:
            List of comments with positions.
        """
        if self._comments is not None:
            return self._comments

        comments: list[Comment] = []
        for token in self._get_tokens():
            if token.type != tokenize.COMMENT:
                continue
            line_num, col = token.start
            before = (token.line or "")[:col]
            comments.append(
                Comment(
                    content=token.string[1:].strip(),
                    line=line_num,
                    column=col + 1,
                    is_inline=bool(before.strip()),
                )
            )

        self._comments = comments
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

    def get_inline_suppressions(self) -> list[InlineSuppression]:
        """Return directives found in real Python comment tokens."""
        if self._inline_suppressions is not None:
            return self._inline_suppressions

        directive_re = re.compile(
            r"#\s*slop-lint:\s*ignore\s*=\s*(.*?)\s*$", re.IGNORECASE
        )
        suppressions: list[InlineSuppression] = []
        for token in self._get_tokens():
            if (
                token.type != tokenize.COMMENT
                or "slop-lint:" not in token.string.lower()
            ):
                continue
            match = directive_re.search(token.string)
            if match is None:
                raise ValueError(f"line {token.start[0]}: malformed inline suppression")
            raw = _validate_suppression_tokens(match.group(1), token.start[0])
            suppressions.append((token.start[0], token.start[0], raw))

        self._inline_suppressions = suppressions
        return suppressions

    def get_prose_blocks(self) -> list[ProseBlock]:
        """Return source-mapped blocks for real docstrings and comments."""
        if self._prose_blocks is not None:
            return self._prose_blocks
        if not self._parsed:
            self.parse()

        blocks = self._docstring_prose_blocks()
        blocks.extend(self._comment_prose_blocks())
        blocks.sort(key=lambda block: block.start_line)
        self._prose_blocks = [
            ProseBlock(
                context=block.context,
                start_line=block.start_line,
                end_line=block.end_line,
                lines=block.lines,
                break_before=index > 0,
            )
            for index, block in enumerate(blocks)
        ]
        return self._prose_blocks

    def get_prose_lines(self) -> list[tuple[int, str]]:
        """Return Python prose while masking code and block boundaries."""
        if self._prose_lines is not None:
            return self._prose_lines
        masked = [list(" " * len(line)) for line in self._lines]
        for block in self.get_prose_blocks():
            for line_num, line in block.lines:
                for index, char in enumerate(line):
                    if char != " ":
                        masked[line_num - 1][index] = char
        self._prose_lines = [
            (line_num, "".join(chars)) for line_num, chars in enumerate(masked, start=1)
        ]
        return self._prose_lines

    def get_prose_sentences(self) -> list[ProseSentence]:
        """Return cached source-mapped prose sentences."""
        if self._prose_sentences is None:
            self._prose_sentences = _sentences_from_blocks(self.get_prose_blocks())
        return self._prose_sentences

    def _docstring_nodes(
        self,
    ) -> list[
        tuple[
            ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
            ast.Constant,
        ]
    ]:
        if self._tree is None:
            return []

        nodes: list[
            tuple[
                ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
                ast.Constant,
            ]
        ] = []
        for node in ast.walk(self._tree):
            if not isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ) or not getattr(node, "body", None):
                continue
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                nodes.append((node, first.value))
        return sorted(nodes, key=lambda item: item[1].lineno)

    def _get_tokens(self) -> list[tokenize.TokenInfo]:
        if self._tokens is not None:
            return self._tokens

        tokens: list[tokenize.TokenInfo] = []
        try:
            for token in tokenize.generate_tokens(io.StringIO(self.content).readline):
                tokens.append(token)
        except (tokenize.TokenError, UnicodeDecodeError):
            pass
        self._tokens = tokens
        return tokens

    def _docstring_prose_blocks(self) -> list[ProseBlock]:
        blocks: list[ProseBlock] = []
        string_tokens = [
            token for token in self._get_tokens() if token.type == tokenize.STRING
        ]
        for _owner, node in self._docstring_nodes():
            end_line = node.end_lineno or node.lineno
            end_column = node.end_col_offset or len(self._lines[end_line - 1])
            tokens = [
                token
                for token in string_tokens
                if token.start >= (node.lineno, node.col_offset)
                and token.end <= (end_line, end_column)
            ]
            if not tokens:
                continue
            start_line = tokens[0].start[0]
            final_line = tokens[-1].end[0]
            chars = {
                line_num: list(" " * len(self._lines[line_num - 1]))
                for line_num in range(start_line, final_line + 1)
            }
            for token in tokens:
                self._copy_string_token(chars, token)
            blocks.append(
                ProseBlock(
                    "body",
                    start_line,
                    final_line,
                    tuple((line_num, "".join(chars[line_num])) for line_num in chars),
                )
            )
        return blocks

    def _copy_string_token(
        self,
        chars: dict[int, list[str]],
        token: tokenize.TokenInfo,
    ) -> None:
        for line_num in range(token.start[0], token.end[0] + 1):
            source = self._lines[line_num - 1]
            start = token.start[1] if line_num == token.start[0] else 0
            end = token.end[1] if line_num == token.end[0] else len(source)
            chars[line_num][start:end] = source[start:end]

        delimiter = re.match(r"(?i:[rubf]*)(\"\"\"|'''|\"|')", token.string)
        if delimiter is None:  # pragma: no cover - tokenize guarantees quotes
            return
        opening_length = len(delimiter.group(0))
        quote_length = len(delimiter.group(1))
        start_chars = chars[token.start[0]]
        for index in range(token.start[1], token.start[1] + opening_length):
            start_chars[index] = " "
        end_chars = chars[token.end[0]]
        for index in range(token.end[1] - quote_length, token.end[1]):
            end_chars[index] = " "

    def _comment_prose_blocks(self) -> list[ProseBlock]:
        tokens = [
            token
            for token in self._get_tokens()
            if token.type == tokenize.COMMENT and not self._is_metadata_comment(token)
        ]
        blocks: list[ProseBlock] = []
        full_line_group: list[tokenize.TokenInfo] = []

        def flush() -> None:
            if not full_line_group:
                return
            blocks.append(self._comment_block(full_line_group))
            full_line_group.clear()

        for token in tokens:
            is_inline = bool((token.line or "")[: token.start[1]].strip())
            if is_inline:
                flush()
                blocks.append(self._comment_block([token]))
            elif full_line_group and token.start[0] != full_line_group[-1].start[0] + 1:
                flush()
                full_line_group.append(token)
            else:
                full_line_group.append(token)
        flush()
        return blocks

    def _comment_block(self, tokens: list[tokenize.TokenInfo]) -> ProseBlock:
        lines: list[tuple[int, str]] = []
        for token in tokens:
            line_num, column = token.start
            chars = list(" " * len(self._lines[line_num - 1]))
            chars[column + 1 : token.end[1]] = self._lines[line_num - 1][
                column + 1 : token.end[1]
            ]
            lines.append((line_num, "".join(chars)))
        return ProseBlock("body", lines[0][0], lines[-1][0], tuple(lines))

    @staticmethod
    def _is_metadata_comment(token: tokenize.TokenInfo) -> bool:
        if token.start[0] == 1 and token.string.startswith("#!"):
            return True
        return token.start[0] <= 2 and bool(
            re.search(r"coding\s*[:=]\s*[-\w.]+", token.string)
        )


@lru_cache(maxsize=32)
def _get_cached_parser(content: str) -> PythonParser:
    """Return one parsed Python parser per recent content value."""
    parser = PythonParser(content)
    parser.parse()
    return parser


def clear_parser_cache() -> None:
    """Clear the Python parser cache for deterministic tests."""
    _get_cached_parser.cache_clear()
