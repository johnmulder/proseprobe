"""Vocabulary detection rules (V001-V005)."""

import re

from humanize.data.phrases import (
    COLLABORATIVE_PHRASES,
    KNOWLEDGE_CUTOFF_PATTERNS,
    PROMOTIONAL_PHRASES,
    WEASEL_PHRASES,
)
from humanize.data.vocabulary import AI_VOCABULARY, VOCABULARY_SUGGESTIONS
from humanize.rules.base import Issue, Rule, Severity


class AIVocabularyRule(Rule):
    """V001: Detect AI-specific vocabulary."""

    id = "V001"
    name = "AI Vocabulary"
    description = "Detects overused AI-specific words"
    severity = Severity.WARNING
    fixable = True

    # Patterns for words that need suffix matching (verbs, etc.)
    _WORD_PATTERNS: dict[str, str] = {
        "delve": r"delv(?:e|es|ed|ing)",
        "embark": r"embark(?:s|ed|ing)?",
        "foster": r"foster(?:s|ed|ing)?",
        "garner": r"garner(?:s|ed|ing)?",
        "harness": r"harness(?:es|ed|ing)?",
        "leverage": r"leverag(?:e|es|ed|ing)",
        "navigate": r"navigat(?:e|es|ed|ing)",
        "showcase": r"showcas(?:e|es|ed|ing)",
        "spearhead": r"spearhead(?:s|ed|ing)?",
        "streamline": r"streamlin(?:e|es|ed|ing)",
        "underscore": r"underscor(?:e|es|ed|ing)",
        "unravel": r"unravel(?:s|ed|ing)?",
    }

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for AI vocabulary words."""
        issues: list[Issue] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            line_lower = line.lower()
            for word in AI_VOCABULARY:
                # Use custom pattern if available, otherwise exact match
                if word in self._WORD_PATTERNS:
                    pattern = rf"\b{self._WORD_PATTERNS[word]}\b"
                else:
                    pattern = rf"\b{re.escape(word)}\b"

                for match in re.finditer(pattern, line_lower):
                    suggestion = VOCABULARY_SUGGESTIONS.get(word)
                    matched_word = match.group()
                    message = f"AI vocabulary: '{matched_word}'"
                    if suggestion:
                        message += f" → consider '{suggestion}'"

                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=message,
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                            fixable=suggestion is not None,
                            suggestion=suggestion,
                        )
                    )

        return issues

    def fix(self, content: str, issue: Issue) -> str:
        """Replace AI vocabulary with suggestion."""
        if not issue.suggestion:
            return content

        lines = content.split("\n")
        line_idx = issue.line - 1
        line = lines[line_idx]

        # Find and replace the word (case-preserving)
        col_start = issue.column - 1
        col_end = (
            issue.end_column - 1
            if issue.end_column
            else col_start + len(issue.suggestion)
        )
        original = line[col_start:col_end]

        # Preserve case
        if original.isupper():
            replacement = issue.suggestion.upper()
        elif original[0].isupper():
            replacement = issue.suggestion.capitalize()
        else:
            replacement = issue.suggestion

        lines[line_idx] = line[:col_start] + replacement + line[col_end:]
        return "\n".join(lines)


class CollaborativePhrasesRule(Rule):
    """V002: Detect collaborative/chat-like phrases."""

    id = "V002"
    name = "Collaborative Phrases"
    description = "Detects chat-like communication patterns"
    severity = Severity.WARNING
    fixable = False

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for collaborative phrases."""
        issues: list[Issue] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            line_lower = line.lower()
            for phrase in COLLABORATIVE_PHRASES:
                if phrase.lower() in line_lower:
                    col = line_lower.find(phrase.lower())
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Collaborative phrase: '{phrase}'",
                            line=line_num,
                            column=col + 1,
                            end_column=col + len(phrase) + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class KnowledgeCutoffRule(Rule):
    """V003: Detect knowledge cutoff disclaimers."""

    id = "V003"
    name = "Knowledge Cutoff"
    description = "Detects temporal/knowledge cutoff disclaimers"
    severity = Severity.INFO
    fixable = False

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for knowledge cutoff patterns."""
        issues: list[Issue] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for pattern in KNOWLEDGE_CUTOFF_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Knowledge cutoff phrase: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class PromotionalLanguageRule(Rule):
    """V004: Detect promotional/puffery language."""

    id = "V004"
    name = "Promotional Language"
    description = "Detects puffery and marketing speak"
    severity = Severity.WARNING
    fixable = False

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for promotional language."""
        issues: list[Issue] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            line_lower = line.lower()
            for phrase in PROMOTIONAL_PHRASES:
                if phrase.lower() in line_lower:
                    col = line_lower.find(phrase.lower())
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Promotional language: '{phrase}'",
                            line=line_num,
                            column=col + 1,
                            end_column=col + len(phrase) + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class WeaselWordsRule(Rule):
    """V005: Detect weasel words and vague attributions."""

    id = "V005"
    name = "Weasel Words"
    description = "Detects vague attributions and weasel phrases"
    severity = Severity.INFO
    fixable = False

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for weasel words."""
        issues: list[Issue] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for pattern in WEASEL_PHRASES:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Weasel phrase: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues
