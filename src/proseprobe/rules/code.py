"""Code-specific detection rules (C001-C008)."""

import ast
import re
from typing import ClassVar

from proseprobe.data.code_patterns import (
    AI_PLACEHOLDER_CODE_PATTERNS,
    AI_PLACEHOLDER_COMMENT_PATTERNS,
    AI_PLACEHOLDER_INLINE_PATTERNS,
    COLLABORATIVE_COMMENT_PATTERNS,
    VERBOSE_COMMENT_PATTERNS,
)
from proseprobe.data.vocabulary import AI_VOCABULARY, DOCSTRING_AI_VOCABULARY
from proseprobe.parsers.python import Docstring, _get_cached_parser
from proseprobe.rules.base import Confidence, Issue, Rule, Severity

_IDENTIFIER_WORD = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|[A-Z]+|\d+")
_SIGNATURE_CONNECTIVES = frozenset(
    {"a", "an", "and", "by", "for", "from", "of", "the", "to", "with"}
)


class DocstringVocabularyRule(Rule):
    """C001: Detect Python-specific vocabulary in docstrings."""

    id = "C001"
    name = "Docstring-Only Vocabulary"
    description = "Detects Python docstring terms not covered by V001"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"python"}

    def __init__(
        self,
        allowed: set[str] | None = None,
        additional: set[str] | None = None,
    ) -> None:
        super().__init__()
        self._allowed = {w.lower() for w in (allowed or set())}
        general_words = AI_VOCABULARY | {
            word.lower() for word in (additional or set()) if isinstance(word, str)
        }
        self._ai_words = [
            item
            for item in DOCSTRING_AI_VOCABULARY
            if item[1].lower() not in general_words
        ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for overused vocabulary in docstrings."""
        issues: list[Issue] = []

        parser = _get_cached_parser(content)
        if not parser.parse():
            return issues

        for block in parser.get_docstring_prose_blocks():
            for pattern, word, replacement in self._ai_words:
                if word.lower() in self._allowed:
                    continue
                found: tuple[int, re.Match[str]] | None = None
                for line_num, line in block.lines:
                    if match := re.search(pattern, line, re.IGNORECASE):
                        found = (line_num, match)
                        break
                if found is None:
                    continue
                line_num, match = found
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Overused word in docstring: '{word}'",
                        line=line_num,
                        column=match.start() + 1,
                        end_column=match.end() + 1,
                        severity=self.severity,
                        suggestion=replacement,
                    )
                )

        return issues


class VerboseCommentsRule(Rule):
    """C002: Detect over-explained code comments."""

    id = "C002"
    name = "Verbose Comments"
    description = "Detects comments with excessive verbosity patterns"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"python"}

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for verbose comments."""
        issues: list[Issue] = []

        parser = _get_cached_parser(content)
        comments = parser.get_comments()

        lines = content.split("\n")
        for comment in comments:
            source_comment = lines[comment.line - 1][comment.column - 1 :]
            for pattern, reason in VERBOSE_COMMENT_PATTERNS:
                match = re.search(pattern, source_comment, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Verbose comment: {reason}",
                            line=comment.line,
                            column=comment.column + match.start(),
                            end_column=comment.column + match.end(),
                            severity=self.severity,
                        )
                    )
                    break  # Only one issue per line

        return issues


class CollaborativeCommentsRule(Rule):
    """C003: Detect chat phrases in code comments."""

    id = "C003"
    name = "Collaborative Comments"
    description = "Detects 'I hope this helps' in # comments"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"python"}

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for collaborative comments."""
        issues: list[Issue] = []
        parser = _get_cached_parser(content)
        comments = parser.get_comments()

        lines = content.split("\n")
        for comment in comments:
            source_comment = lines[comment.line - 1][comment.column - 1 :]
            for pattern, phrase in COLLABORATIVE_COMMENT_PATTERNS:
                match = re.search(pattern, source_comment, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Chat phrase in comment: '{phrase}'",
                            line=comment.line,
                            column=comment.column + match.start(),
                            end_column=comment.column + match.end(),
                            severity=self.severity,
                        )
                    )
                    break

        return issues


class AIPlaceholdersRule(Rule):
    """C004: Detect formulaic placeholders."""

    id = "C004"
    name = "Formulaic Placeholders"
    description = "Detects context-free markers, generic TODOs, and boilerplate"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"python"}

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for formulaic placeholders."""
        issues: list[Issue] = []

        lines = content.split("\n")
        parser = _get_cached_parser(content)
        comments = parser.get_comments()

        # Comment-only placeholders
        for comment in comments:
            source_comment = lines[comment.line - 1][comment.column - 1 :]
            matched_comment = False
            for pattern, kind in AI_PLACEHOLDER_COMMENT_PATTERNS:
                match = re.search(pattern, source_comment, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Formulaic placeholder: {kind}",
                            line=comment.line,
                            column=comment.column + match.start(),
                            end_column=comment.column + match.end(),
                            severity=self.severity,
                        )
                    )
                    matched_comment = True
                    break

            # Inline code + comment placeholders
            if matched_comment:
                continue
            line_text = lines[comment.line - 1]
            before = line_text[: comment.column - 1]
            source_comment = line_text[comment.column - 1 :]
            for code_pattern, todo_pattern, kind in AI_PLACEHOLDER_INLINE_PATTERNS:
                todo_match = re.search(todo_pattern, source_comment, re.IGNORECASE)
                if re.search(code_pattern, before) and todo_match is not None:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Formulaic placeholder: {kind}",
                            line=comment.line,
                            column=comment.column + todo_match.start(),
                            end_column=comment.column + todo_match.end(),
                            severity=self.severity,
                        )
                    )
                    break

        # Code-only placeholders
        for line_num, line in enumerate(lines, start=1):
            for pattern, kind in AI_PLACEHOLDER_CODE_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Formulaic placeholder: {kind}",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
                    break

        return issues


class CommentRestatesCodeRule(Rule):
    """C006: Detect exact comments that restate the next statement."""

    id = "C006"
    name = "Comment Restates Code"
    description = "Detects exact comments that restate the next Python statement"
    severity = Severity.INFO
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"python"}

    @staticmethod
    def _name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    @staticmethod
    def _words(text: str) -> tuple[str, ...]:
        return tuple(
            match.group().casefold() for match in _IDENTIFIER_WORD.finditer(text)
        )

    @classmethod
    def _expected_comments(cls, statement: ast.stmt) -> set[tuple[str, ...]]:
        name: str | None = None
        verbs: tuple[str, ...] = ()
        if isinstance(statement, ast.Return) and statement.value is not None:
            name = cls._name(statement.value)
            verbs = ("return",)
        elif isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            name = cls._name(statement.targets[0])
            verbs = ("assign", "set")
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            name = cls._name(statement.target)
            verbs = ("assign", "set")
        elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            name = cls._name(statement.value.func)
            verbs = ("call",)

        words = cls._words(name or "")
        return {(verb, *words) for verb in verbs} if words else set()

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check adjacent full-line comments against supported statements."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        supported = (ast.Return, ast.Assign, ast.AnnAssign, ast.Expr)
        statements = {
            (node.lineno, node.col_offset): node
            for node in ast.walk(tree)
            if isinstance(node, supported)
        }
        lines = content.split("\n")
        issues: list[Issue] = []
        for comment in _get_cached_parser(content).get_comments():
            if comment.is_inline:
                continue
            statement = statements.get((comment.line + 1, comment.column - 1))
            if statement is None or self._words(comment.content) not in (
                self._expected_comments(statement)
            ):
                continue
            after_hash = lines[comment.line - 1][comment.column :]
            leading_space = len(after_hash) - len(after_hash.lstrip())
            column = comment.column + leading_space + 1
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Comment restates code: '{comment.content}'",
                    line=comment.line,
                    column=column,
                    end_column=column + len(comment.content),
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Delete it or explain why the code exists",
                )
            )
        return issues


class DocstringRepeatsSignatureRule(Rule):
    """C007: Detect opening docstring sentences that repeat the signature."""

    id = "C007"
    name = "Docstring Repeats Signature"
    description = "Detects function docstrings that only repeat signature words"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"python"}

    @staticmethod
    def _words(text: str) -> set[str]:
        return {match.group().casefold() for match in _IDENTIFIER_WORD.finditer(text)}

    @classmethod
    def _repeats_signature(cls, opening: str, docstring: Docstring) -> bool:
        signature = cls._words(
            " ".join((docstring.owner_name or "", *docstring.parameters))
        )
        if len(signature) < 2:
            return False
        opening_words = cls._words(opening)
        opening_words.difference_update(_SIGNATURE_CONNECTIVES - signature)
        return opening_words == signature

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check function docstring openings against their signatures."""
        parser = _get_cached_parser(content)
        if not parser.parse():
            return []

        sentences = parser.get_prose_sentences()
        issues: list[Issue] = []
        for docstring in parser.get_docstrings():
            if docstring.node_type != "function":
                continue
            opening = next(
                (
                    sentence
                    for sentence in sentences
                    if docstring.line <= sentence.start_line <= docstring.end_line
                ),
                None,
            )
            if opening is None or not self._repeats_signature(opening.text, docstring):
                continue
            line, column = opening.source_position()
            end_line, end_column = opening.source_position(len(opening.text))
            issues.append(
                Issue(
                    rule_id=self.id,
                    message="Docstring opening repeats the function signature",
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    severity=self.severity,
                    suggestion="Describe behavior, results, or constraints",
                )
            )
        return issues


class CommentedOutCodeRule(Rule):
    """C008: Detect full-line comments that parse as code statements."""

    id = "C008"
    name = "Commented-Out Code"
    description = "Detects full-line comments containing exact Python statements"
    severity = Severity.INFO
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"python"}

    @staticmethod
    def _statement_kind(text: str) -> str | None:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            if not text.rstrip().endswith(":"):
                return None
            try:
                tree = ast.parse(f"{text}\n    pass")
            except SyntaxError:
                return None

        if len(tree.body) != 1:
            return None
        statement = tree.body[0]
        if isinstance(statement, (ast.Assign, ast.AugAssign)) or (
            isinstance(statement, ast.AnnAssign) and statement.value is not None
        ):
            return "assignment"
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            return "call"
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            return "import"
        if isinstance(statement, (ast.If, ast.For, ast.While, ast.With)):
            return "control statement"
        return None

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check full-line Python comments for exact statement syntax."""
        lines = content.split("\n")
        issues: list[Issue] = []
        for comment in _get_cached_parser(content).get_comments():
            if comment.is_inline:
                continue
            kind = self._statement_kind(comment.content)
            if kind is None:
                continue
            after_hash = lines[comment.line - 1][comment.column :]
            leading_space = len(after_hash) - len(after_hash.lstrip())
            column = comment.column + leading_space + 1
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Commented-out code: {kind}",
                    line=comment.line,
                    column=column,
                    end_column=column + len(comment.content),
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Delete it or restore it as executable code",
                )
            )
        return issues
