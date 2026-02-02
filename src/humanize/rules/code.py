"""Code-specific detection rules (C001-C004)."""

import ast
import re
from typing import ClassVar

from humanize.rules.base import Issue, Rule, Severity


class DocstringVocabularyRule(Rule):
    """C001: Detect AI vocabulary in docstrings."""

    id = "C001"
    name = "Docstring Vocabulary"
    description = "Detects AI-specific words in Python docstrings"
    severity = Severity.WARNING
    fixable = True

    # AI vocabulary to flag in docstrings with replacements
    _ai_words: ClassVar[list[tuple[str, str, str]]] = [
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

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for AI vocabulary in docstrings."""
        issues: list[Issue] = []

        # Only check Python files
        if not filename.endswith(".py"):
            return issues

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            # Only get docstrings from nodes that can have them
            if not isinstance(
                node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                continue
            docstring = ast.get_docstring(node)
            if docstring:
                for pattern, word, replacement in self._ai_words:
                    match = re.search(pattern, docstring, re.IGNORECASE)
                    if match:
                        # Get line number from node
                        line = getattr(node, "lineno", 1)
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message=f"AI vocabulary in docstring: '{word}'",
                                line=line,
                                column=1,
                                severity=self.severity,
                                fixable=True,
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

        # Only check Python files
        if not filename.endswith(".py"):
            return issues

        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for pattern, reason in self._verbose_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Verbose comment: {reason}",
                            line=line_num,
                            column=match.start() + 1,
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

        # Check both Python and other files with # comments
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for pattern, phrase in self._chat_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Chat phrase in comment: '{phrase}'",
                            line=line_num,
                            column=match.start() + 1,
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

    # Formulaic placeholder patterns
    _placeholder_patterns: ClassVar[list[tuple[str, str]]] = [
        (r"#\s*TODO:\s*Implement\s*$", "bare 'Implement'"),
        (r"#\s*TODO:\s*Add (?:logic|code) here", "generic placeholder"),
        (r"#\s*TODO:\s*Fill in", "generic placeholder"),
        (r"#\s*TODO:\s*Replace with actual", "generic placeholder"),
        (r"#\s*TODO:\s*Complete this", "generic placeholder"),
        (r"pass\s*#\s*(?:TODO|placeholder)", "pass with placeholder"),
        (r"raise NotImplementedError\([\"'].*[\"']\)", "template error"),
        (r"\.\.\.\s*#\s*(?:TODO|your code)", "ellipsis placeholder"),
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for AI placeholders."""
        issues: list[Issue] = []

        # Only check Python files
        if not filename.endswith(".py"):
            return issues

        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for pattern, kind in self._placeholder_patterns:
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
