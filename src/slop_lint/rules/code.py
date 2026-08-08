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
from slop_lint.data.vocabulary import AI_VOCABULARY, DOCSTRING_AI_VOCABULARY
from slop_lint.parsers.python import _get_cached_parser
from slop_lint.rules.base import Issue, Rule, Severity


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
    description = "Detects generic TODO patterns and boilerplate"
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
                    break

            # Inline code + comment placeholders
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
