"""Markup detection rules (M001-M004)."""

import re
from typing import ClassVar

from slop_lint.parsers.markdown import is_markdown_file
from slop_lint.rules.base import Issue, Rule, Severity, remove_text_range


class WrongMarkupRule(Rule):
    """M001: Detect Markdown in wrong context."""

    id = "M001"
    name = "Wrong Markup"
    description = "Detects **bold** in Python comments"
    severity = Severity.WARNING
    fixable = False
    applies_to = {"python"}

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

        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
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
    fixable = True
    applies_to = {"markdown"}
    content_scope = "prose"

    _patterns = [
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
                            fixable=True,
                        )
                    )

        return issues

    def fix(self, content: str, issue: Issue) -> str:
        """Remove ChatGPT marker from content."""
        return remove_text_range(content, issue.line, issue.column, issue.end_column)


class UTMParametersRule(Rule):
    """M003: Detect tracking UTM parameters in URLs."""

    id = "M003"
    name = "UTM Parameters"
    description = "Detects utm_source=chatgpt.com or openai"
    severity = Severity.WARNING
    fixable = True
    applies_to = {"markdown"}

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
                            fixable=True,
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
                            fixable=True,
                        )
                    )

        return issues

    def fix(self, content: str, issue: Issue) -> str:
        """Remove UTM parameters from URL."""
        lines = content.split("\n")
        line_idx = issue.line - 1
        line = lines[line_idx]

        # Find and remove the UTM parameter
        col_start = issue.column - 1
        col_end = issue.end_column - 1 if issue.end_column else col_start + 20

        # Get the matched text
        matched = line[col_start:col_end]

        # If it starts with ?, we need to handle the next parameter
        if matched.startswith("?"):
            # Check if there are more parameters after
            rest = line[col_end:]
            if rest.startswith("&"):
                # Remove the ? param and the following &, replace with ?
                lines[line_idx] = line[:col_start] + "?" + rest[1:]
            else:
                # Just remove the whole ?param
                lines[line_idx] = line[:col_start] + rest
        else:
            # Starts with &, just remove the &param
            lines[line_idx] = line[:col_start] + line[col_end:]

        return "\n".join(lines)


class BrokenReferencesRule(Rule):
    """M004: Detect broken references."""

    id = "M004"
    name = "Broken References"
    description = "Detects [attached_file:1], grok_card tags"
    severity = Severity.ERROR
    fixable = True
    applies_to = {"markdown"}
    content_scope = "prose"

    _patterns = [
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
                            fixable=True,
                        )
                    )

        return issues

    def fix(self, content: str, issue: Issue) -> str:
        """Remove broken reference from content."""
        return remove_text_range(content, issue.line, issue.column, issue.end_column)
