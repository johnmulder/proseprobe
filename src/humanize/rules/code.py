"""Code-specific detection rules (C001-C004)."""

import re
from typing import ClassVar

from humanize.parsers.python import PythonParser
from humanize.rules.base import Issue, Rule, Severity


class DocstringVocabularyRule(Rule):
    """C001: Detect AI vocabulary in docstrings."""

    id = "C001"
    name = "Docstring Vocabulary"
    description = "Detects AI-specific words in Python docstrings"
    severity = Severity.WARNING
    fixable = True
    applies_to = {"python"}

    # AI vocabulary to flag in docstrings with replacements
    _base_ai_words: ClassVar[list[tuple[str, str, str]]] = [
        (r"\bdelve\b", "delve", "explore"),
        (r"\bleverage\b", "leverage", "use"),
        (r"\butilize\b", "utilize", "use"),
        (r"\bfacilitate\b", "facilitate", "help"),
        (r"\bseamless(?:ly)?\b", "seamless", "smooth"),
        (r"\brobust\b", "robust", "strong"),
        (r"\bcomprehensive\b", "comprehensive", "complete"),
        (r"\bbespoke\b", "bespoke", "custom"),
        (r"\bholistic\b", "holistic", "complete"),
        (r"\bfoster\b", "foster", "encourage"),
        (r"\bsynergy\b", "synergy", "cooperation"),
        (r"\bparadigm\b", "paradigm", "model"),
    ]

    def __init__(
        self,
        allowed: set[str] | None = None,
        additional: set[str] | None = None,
    ) -> None:
        self._allowed = {w.lower() for w in (allowed or set())}
        extra_words = {
            w.lower()
            for w in (additional or set())
            if isinstance(w, str)
        }

        base_words = {word.lower() for _, word, _ in self._base_ai_words}
        extra_words = extra_words - self._allowed - base_words

        self._ai_words: list[tuple[str, str, str | None]] = list(self._base_ai_words)
        for word in sorted(extra_words):
            pattern = rf"\b{re.escape(word)}\b"
            self._ai_words.append((pattern, word, None))

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for AI vocabulary in docstrings."""
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
                            message=f"AI vocabulary in docstring: '{word}'",
                            line=doc.line,
                            column=1,
                            severity=self.severity,
                            fixable=replacement is not None,
                            suggestion=replacement,
                        )
                    )

        return issues

    def fix(self, content: str, issue: Issue) -> str:
        """Replace AI vocabulary in docstrings with suggestion."""
        if not issue.suggestion:
            return content

        # Extract the word from the message
        # Message format: "AI vocabulary in docstring: 'word'"
        import re as re_module
        word_match = re_module.search(r"'(\w+)'", issue.message)
        if not word_match:
            return content

        word = word_match.group(1)

        # Replace the word case-insensitively, preserving case
        def replace_preserving_case(match: re_module.Match[str]) -> str:
            original = match.group(0)
            replacement = issue.suggestion
            if not replacement:
                return original
            if original.isupper():
                return replacement.upper()
            elif original[0].isupper():
                return replacement.capitalize()
            return replacement

        pattern = rf"\b{word}\b"
        return re_module.sub(pattern, replace_preserving_case, content, flags=re_module.IGNORECASE)


class VerboseCommentsRule(Rule):
    """C002: Detect over-explained code comments."""

    id = "C002"
    name = "Verbose Comments"
    description = "Detects comments with AI verbosity patterns"
    severity = Severity.INFO
    fixable = False
    applies_to = {"python"}

    # Patterns indicating over-explanation
    _verbose_patterns: ClassVar[list[tuple[str, str]]] = [
        (r"#\s*This (?:function|method|class|variable|code)", "explains obvious"),
        (r"#\s*The following (?:code|section)", "announces code"),
        (r"#\s*As (?:you can see|mentioned)", "conversational"),
        (r"#\s*In order to\b", "wordy (use 'to')"),
        (r"#\s*It is (?:important|worth|necessary) to note", "hedging"),
        (r"#\s*Basically,?\s", "filler word"),
        (r"#\s*Essentially,?\s", "filler word"),
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for verbose comments."""
        issues: list[Issue] = []

        parser = PythonParser(content)
        comments = parser.get_comments()

        for comment in comments:
            comment_line = f"# {comment.content}".strip()
            for pattern, reason in self._verbose_patterns:
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
    fixable = False
    applies_to = {"python"}

    # Chat-like phrases that shouldn't be in code
    _chat_patterns: ClassVar[list[tuple[str, str]]] = [
        (r"#\s*I hope this helps", "I hope this helps"),
        (r"#\s*Let me know if", "Let me know if"),
        (r"#\s*Feel free to", "Feel free to"),
        (r"#\s*Happy coding", "Happy coding"),
        (r"#\s*Hope this (?:helps|works)", "Hope this"),
        (r"#\s*Here's (?:a|an|the)", "Here's..."),
        (r"#\s*I've (?:added|created|implemented)", "I've..."),
        (r"#\s*As requested", "As requested"),
        (r"#\s*As per your", "As per your"),
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for collaborative comments."""
        issues: list[Issue] = []
        parser = PythonParser(content)
        comments = parser.get_comments()

        for comment in comments:
            comment_line = f"# {comment.content}".strip()
            for pattern, phrase in self._chat_patterns:
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
    """C004: Detect formulaic AI placeholders."""

    id = "C004"
    name = "AI Placeholders"
    description = "Detects generic TODO patterns from AI"
    severity = Severity.INFO
    fixable = False
    applies_to = {"python"}

    # Formulaic placeholder patterns (comment-only)
    _comment_patterns: ClassVar[list[tuple[str, str]]] = [
        (r"#\s*TODO:\s*Implement\s*$", "bare 'Implement'"),
        (r"#\s*TODO:\s*Add (?:logic|code) here", "generic placeholder"),
        (r"#\s*TODO:\s*Fill in", "generic placeholder"),
        (r"#\s*TODO:\s*Replace with actual", "generic placeholder"),
        (r"#\s*TODO:\s*Complete this", "generic placeholder"),
    ]
    _code_patterns: ClassVar[list[tuple[str, str]]] = [
        (r"raise NotImplementedError\([\"'].*[\"']\)", "template error"),
    ]
    _inline_comment_markers: ClassVar[list[tuple[str, str, str]]] = [
        (r"\bpass\b", r"(?:TODO|placeholder)", "pass with placeholder"),
        (r"\.\.\.", r"(?:TODO|your code)", "ellipsis placeholder"),
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for AI placeholders."""
        issues: list[Issue] = []

        lines = content.split("\n")
        parser = PythonParser(content)
        comments = parser.get_comments()

        # Comment-only placeholders
        for comment in comments:
            comment_line = f"# {comment.content}".strip()
            for pattern, kind in self._comment_patterns:
                match = re.search(pattern, comment_line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"AI placeholder: {kind}",
                            line=comment.line,
                            column=comment.column + match.start(),
                            severity=self.severity,
                        )
                    )
                    break

            # Inline code + comment placeholders
            line_text = lines[comment.line - 1]
            before = line_text[: comment.column - 1]
            for code_pattern, todo_pattern, kind in self._inline_comment_markers:
                if re.search(code_pattern, before) and re.search(
                    todo_pattern, comment.content, re.IGNORECASE
                ):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"AI placeholder: {kind}",
                            line=comment.line,
                            column=comment.column,
                            severity=self.severity,
                        )
                    )
                    break

        # Code-only placeholders
        for line_num, line in enumerate(lines, start=1):
            for pattern, kind in self._code_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"AI placeholder: {kind}",
                            line=line_num,
                            column=match.start() + 1,
                            severity=self.severity,
                        )
                    )
                    break

        return issues
