"""Code-specific detection rules (C001-C004)."""

import re
from typing import ClassVar

from slop_lint.data.code_patterns import (
    AI_PLACEHOLDER_CODE_PATTERNS,
    AI_PLACEHOLDER_COMMENT_PATTERNS,
    AI_PLACEHOLDER_INLINE_PATTERNS,
    COLLABORATIVE_COMMENT_PATTERNS,
    VERBOSE_COMMENT_PATTERNS,
)
from slop_lint.data.vocabulary import DOCSTRING_AI_VOCABULARY
from slop_lint.parsers.python import PythonParser
from slop_lint.rules.base import Issue, Rule, Severity


class DocstringVocabularyRule(Rule):
    """C001: Detect overused vocabulary in docstrings."""

    id = "C001"
    name = "Docstring Vocabulary"
    description = "Detects overused words in Python docstrings"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"python"}

    def __init__(
        self,
        allowed: set[str] | None = None,
        additional: set[str] | None = None,
    ) -> None:
        self._allowed = {w.lower() for w in (allowed or set())}
        extra_words = {w.lower() for w in (additional or set()) if isinstance(w, str)}

        base_words = {word.lower() for _, word, _ in DOCSTRING_AI_VOCABULARY}
        extra_words = extra_words - self._allowed - base_words

        self._ai_words: list[tuple[str, str, str | None]] = list(
            DOCSTRING_AI_VOCABULARY
        )
        for word in sorted(extra_words):
            pattern = rf"\b{re.escape(word)}\b"
            self._ai_words.append((pattern, word, None))

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for overused vocabulary in docstrings."""
        issues: list[Issue] = []

        parser = PythonParser(content)
        if not parser.parse():
            return issues

        for doc in parser.get_docstrings():
            for pattern, word, replacement in self._ai_words:
                if word.lower() in self._allowed:
                    continue
                match = re.search(pattern, doc.content, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Overused word in docstring: '{word}'",
                            line=doc.line,
                            column=1,
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

        parser = PythonParser(content)
        comments = parser.get_comments()

        for comment in comments:
            comment_line = f"# {comment.content}".strip()
            for pattern, reason in VERBOSE_COMMENT_PATTERNS:
                match = re.search(pattern, comment_line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Verbose comment: {reason}",
                            line=comment.line,
                            column=comment.column + match.start(),
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
        parser = PythonParser(content)
        comments = parser.get_comments()

        for comment in comments:
            comment_line = f"# {comment.content}".strip()
            for pattern, phrase in COLLABORATIVE_COMMENT_PATTERNS:
                match = re.search(pattern, comment_line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Chat phrase in comment: '{phrase}'",
                            line=comment.line,
                            column=comment.column + match.start(),
                            severity=self.severity,
                        )
                    )
                    break

        return issues


class AIPlaceholdersRule(Rule):
    """C004: Detect formulaic placeholders."""

    id = "C004"
    name = "Formulaic Placeholders"
    description = "Detects generic TODO patterns and boilerplate"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"python"}

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for formulaic placeholders."""
        issues: list[Issue] = []

        lines = content.split("\n")
        parser = PythonParser(content)
        comments = parser.get_comments()

        # Comment-only placeholders
        for comment in comments:
            comment_line = f"# {comment.content}".strip()
            for pattern, kind in AI_PLACEHOLDER_COMMENT_PATTERNS:
                match = re.search(pattern, comment_line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Formulaic placeholder: {kind}",
                            line=comment.line,
                            column=comment.column + match.start(),
                            severity=self.severity,
                        )
                    )
                    break

            # Inline code + comment placeholders
            line_text = lines[comment.line - 1]
            before = line_text[: comment.column - 1]
            for code_pattern, todo_pattern, kind in AI_PLACEHOLDER_INLINE_PATTERNS:
                if re.search(code_pattern, before) and re.search(
                    todo_pattern, comment.content, re.IGNORECASE
                ):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Formulaic placeholder: {kind}",
                            line=comment.line,
                            column=comment.column,
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
                            severity=self.severity,
                        )
                    )
                    break

        return issues
