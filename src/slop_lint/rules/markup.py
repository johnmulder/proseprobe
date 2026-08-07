"""Markup detection rules (M001-M004)."""

import re
from typing import ClassVar

from slop_lint.parsers.markdown import is_markdown_file
from slop_lint.parsers.python import _get_cached_parser
from slop_lint.rules.base import Confidence, Issue, Rule, Severity


class WrongMarkupRule(Rule):
    """M001: Detect Markdown in wrong context."""

    id = "M001"
    name = "Wrong Markup"
    description = "Detects **bold** in Python comments"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"python"}

    # Markdown patterns that don't belong in code
    _md_patterns: ClassVar[list[tuple[str, str]]] = [
        (r"#\s*.*\*\*[^*]+\*\*", "bold (**text**)"),
        (r"#\s*.*\*[^*]+\*(?!\*)", "italic (*text*)"),
        (r"#\s*.*`[^`]+`", "inline code (`code`)"),
        (r"#\s*.*\[[^\]]+\]\([^)]+\)", "link ([text](url))"),
        (r'"""[^"]*\*\*[^*]+\*\*[^"]*"""', "bold in docstring"),
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for wrong markup."""
        issues: list[Issue] = []

        # Build a set of line numbers inside string literals so we can
        # skip #-prefixed lines that are really part of a string.
        string_lines: set[int] = set()
        parser = _get_cached_parser(content)
        if parser.parse():
            for start_line, _col, value in parser.get_string_literals():
                line_count = value.count("\n")
                if line_count > 0:
                    for ln in range(start_line, start_line + line_count + 1):
                        string_lines.add(ln)

        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            if line_num in string_lines:
                continue
            # Check for Markdown in # comments
            if line.strip().startswith("#"):
                for pattern, markup_type in self._md_patterns[:4]:
                    match = re.search(pattern, line)
                    if match:
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message=f"Markdown in comment: {markup_type}",
                                line=line_num,
                                column=match.start() + 1,
                                severity=self.severity,
                                confidence=Confidence.LOW,
                            )
                        )
                        break

        return issues


class ChatGPTMarkersRule(Rule):
    """M002: Detect ChatGPT reference markers."""

    id = "M002"
    name = "ChatGPT Markers"
    description = "Detects turn0search0, oai_citation, contentReference"
    severity = Severity.ERROR
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "prose"

    _patterns: ClassVar[list[str]] = [
        r"turn\d+search\d+",
        r"oai_citation",
        r"contentReference\[.*?\]",
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for ChatGPT markers."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in self._patterns:
                for match in re.finditer(pattern, line):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"ChatGPT marker: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class UTMParametersRule(Rule):
    """M003: Detect tracking UTM parameters in URLs."""

    id = "M003"
    name = "UTM Parameters"
    description = "Detects utm_source=chatgpt.com or openai"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"markdown"}

    _pattern = r"[?&]utm_source=(chatgpt\.com|openai)[^&\s]*"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for tracking UTM parameters."""
        issues: list[Issue] = []
        if is_markdown_file(filename):
            from slop_lint.parsers.markdown import MarkdownParser

            parser = MarkdownParser(content)
            for link in parser.get_links():
                for utm_match in re.finditer(self._pattern, link.url):
                    if link.url_start:
                        column = link.url_start + utm_match.start()
                        end_column = link.url_start + utm_match.end()
                    else:
                        column = link.column + utm_match.start()
                        end_column = link.column + utm_match.end()
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Tracking parameter: '{utm_match.group()}'",
                            line=link.line,
                            column=column,
                            end_column=end_column,
                            severity=self.severity,
                        )
                    )
        else:
            lines = content.split("\n")
            for line_num, line in enumerate(lines, start=1):
                for match in re.finditer(self._pattern, line):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Tracking parameter: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class BrokenReferencesRule(Rule):
    """M004: Detect broken references."""

    id = "M004"
    name = "Broken References"
    description = "Detects [attached_file:1], grok_card tags"
    severity = Severity.ERROR
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "prose"

    _patterns: ClassVar[list[str]] = [
        r"\[attached_file:\d+\]",
        r"grok_card",
        r"\[file_\d+\]",
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for broken references."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in self._patterns:
                for match in re.finditer(pattern, line):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Broken reference: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues
