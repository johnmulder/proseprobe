"""Markup detection rules (M001-M004)."""

import re
from typing import ClassVar

from humanize.rules.base import Issue, Rule, Severity


class WrongMarkupRule(Rule):
    """M001: Detect Markdown in wrong context."""

    id = "M001"
    name = "Wrong Markup"
    description = "Detects **bold** in Python comments"
    severity = Severity.WARNING
    fixable = False

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

        # Only check Python files
        if not filename.endswith(".py"):
            return issues

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

    _patterns = [
        r"turn\d+search\d+",
        r"oai_citation",
        r"contentReference\[.*?\]",
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for ChatGPT markers."""
        issues: list[Issue] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
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
        lines = content.split("\n")
        line_idx = issue.line - 1
        line = lines[line_idx]

        col_start = issue.column - 1
        col_end = issue.end_column - 1 if issue.end_column else col_start + 10

        # Remove the marker, clean up any extra whitespace
        before = line[:col_start].rstrip()
        after = line[col_end:].lstrip()

        # Rejoin with single space if both parts exist
        if before and after:
            lines[line_idx] = before + " " + after
        else:
            lines[line_idx] = before + after

        return "\n".join(lines)


class UTMParametersRule(Rule):
    """M003: Detect AI-related UTM parameters in URLs."""

    id = "M003"
    name = "UTM Parameters"
    description = "Detects utm_source=chatgpt.com or openai"
    severity = Severity.WARNING
    fixable = True

    _pattern = r"[?&]utm_source=(chatgpt\.com|openai)[^&\s]*"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for AI-related UTM parameters."""
        issues: list[Issue] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for match in re.finditer(self._pattern, line):
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"AI tracking parameter: '{match.group()}'",
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
    """M004: Detect broken AI references."""

    id = "M004"
    name = "Broken References"
    description = "Detects [attached_file:1], grok_card tags"
    severity = Severity.ERROR
    fixable = True

    _patterns = [
        r"\[attached_file:\d+\]",
        r"grok_card",
        r"\[file_\d+\]",
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for broken references."""
        issues: list[Issue] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for pattern in self._patterns:
                for match in re.finditer(pattern, line):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Broken AI reference: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                            fixable=True,
                        )
                    )

        return issues

    def fix(self, content: str, issue: Issue) -> str:
        """Remove broken AI reference from content."""
        lines = content.split("\n")
        line_idx = issue.line - 1
        line = lines[line_idx]

        col_start = issue.column - 1
        col_end = issue.end_column - 1 if issue.end_column else col_start + 10

        # Remove the reference, clean up any extra whitespace
        before = line[:col_start].rstrip()
        after = line[col_end:].lstrip()

        # Rejoin with single space if both parts exist
        if before and after:
            lines[line_idx] = before + " " + after
        else:
            lines[line_idx] = before + after

        return "\n".join(lines)
