"""Markup detection rules (M001-M010)."""

import re
from itertools import pairwise
from typing import ClassVar

from proseprobe.parsers.markdown import (
    MarkdownReference,
    is_example_line,
    is_markdown_file,
)
from proseprobe.parsers.markdown import (
    _get_cached_parser as _get_cached_markdown_parser,
)
from proseprobe.parsers.prose import iter_prose_sentences
from proseprobe.parsers.python import _get_cached_parser as _get_cached_python_parser
from proseprobe.rules.base import Confidence, Issue, Rule, Severity


class WrongMarkupRule(Rule):
    """M001: Detect Markdown in wrong context."""

    id = "M001"
    name = "Wrong Markup"
    description = "Detects **bold** in Python comments"
    severity = Severity.WARNING
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"python"}

    # Markdown patterns that don't belong in code
    _md_patterns: ClassVar[list[tuple[str, str]]] = [
        (r"\*\*[^*]+\*\*", "bold (**text**)"),
        (r"(?<!\*)\*[^*]+\*(?!\*)", "italic (*text*)"),
        (r"`[^`]+`", "inline code (`code`)"),
        (r"\[[^\]]+\]\([^)]+\)", "link ([text](url))"),
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for wrong markup."""
        issues: list[Issue] = []

        # Build a set of line numbers inside string literals so we can
        # skip #-prefixed lines that are really part of a string.
        string_lines: set[int] = set()
        parser = _get_cached_python_parser(content)
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
                                end_column=match.end() + 1,
                                severity=self.severity,
                                confidence=self.default_confidence,
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
            from proseprobe.parsers.markdown import MarkdownParser

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
    description = "Detects broken markers and placeholder link destinations"
    severity = Severity.ERROR
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "prose"

    _PLACEHOLDER_DESTINATIONS: ClassVar[frozenset[str]] = frozenset(
        {"url_here", "insert_url", "todo", "tbd"}
    )

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

        if is_markdown_file(filename):
            parser = _get_cached_markdown_parser(content)
            destinations = {
                (link.line, link.url_start, link.url_end): link.url
                for link in parser.get_links()
                if link.url_start
            }
            for reference in parser.get_references():
                if not reference.is_definition or reference.destination is None:
                    continue
                destinations[
                    (
                        reference.line,
                        reference.destination_start,
                        reference.destination_end,
                    )
                ] = reference.destination

            for (line_num, column, end_column), destination in sorted(
                destinations.items()
            ):
                normalized = destination.strip()
                if normalized.casefold() in self._PLACEHOLDER_DESTINATIONS:
                    confidence = Confidence.HIGH
                elif normalized in {"", "#"}:
                    confidence = Confidence.LOW
                else:
                    continue
                if is_example_line(content, filename, line_num):
                    continue
                display = normalized or "(empty)"
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Placeholder link destination: '{display}'",
                        line=line_num,
                        column=column,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=confidence,
                        suggestion="Replace the placeholder with a real destination",
                    )
                )

        return sorted(issues, key=lambda issue: (issue.line, issue.column))


class UnresolvedMarkdownReferencesRule(Rule):
    """M005: Detect undefined references and conflicting definitions."""

    id = "M005"
    name = "Unresolved Markdown References"
    description = "Detects undefined reference labels and conflicting definitions"
    severity = Severity.ERROR
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "non_code"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check Markdown reference uses and definitions."""
        if not is_markdown_file(filename):
            return []

        references = _get_cached_markdown_parser(content).get_references()
        definitions: dict[str, list[MarkdownReference]] = {}
        for reference in references:
            if reference.is_definition:
                definitions.setdefault(reference.label, []).append(reference)

        issues = [
            Issue(
                rule_id=self.id,
                message=f"Undefined reference label: '{reference.label}'",
                line=reference.line,
                column=reference.column,
                end_column=reference.end_column,
                severity=self.severity,
                confidence=self.default_confidence,
                suggestion=(
                    f"Define '[{reference.label}]: destination' or use an inline link"
                ),
            )
            for reference in references
            if not reference.is_definition and reference.label not in definitions
        ]

        for label, label_definitions in definitions.items():
            destinations = {reference.destination for reference in label_definitions}
            if len(destinations) < 2:
                continue
            issues.extend(
                Issue(
                    rule_id=self.id,
                    message=f"Conflicting reference definition: '{label}'",
                    line=reference.line,
                    column=reference.column,
                    end_column=reference.end_column,
                    severity=self.severity,
                    confidence=Confidence.LOW,
                    suggestion=f"Use one destination for reference label '{label}'",
                )
                for reference in label_definitions
            )

        return sorted(issues, key=lambda issue: (issue.line, issue.column))


class TemplateResidueRule(Rule):
    """M006: Detect unfinished template markers in Markdown."""

    id = "M006"
    name = "Template Residue"
    description = "Detects unfinished placeholder content in Markdown"
    severity = Severity.WARNING
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "prose"

    _patterns: ClassVar[tuple[tuple[re.Pattern[str], str, Confidence], ...]] = (
        (
            re.compile(r"\bLorem[ \t]+ipsum\b", re.IGNORECASE),
            "sample text",
            Confidence.HIGH,
        ),
        (
            re.compile(
                r"\[(?:(?:insert|add)\b[^\]\n]{0,64}\bhere"
                r"|replace\s+(?:this|me|with)\b[^\]\n]{0,64})\]",
                re.IGNORECASE,
            ),
            "replacement instruction",
            Confidence.HIGH,
        ),
        (
            re.compile(r"<replace-me>", re.IGNORECASE),
            "replacement marker",
            Confidence.HIGH,
        ),
        (
            re.compile(r"\bYOUR[ \t]+CONTENT[ \t]+HERE\b"),
            "content marker",
            Confidence.HIGH,
        ),
        (
            re.compile(
                r"^[ \t]*(?:TODO|TBD)(?:[ \t]*:[ \t]*[^\n]{0,100})?[.!]?[ \t]*$"
            ),
            "planning marker",
            Confidence.LOW,
        ),
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check Markdown prose for unfinished template markers."""
        if not is_markdown_file(filename):
            return []

        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            spans: list[tuple[int, int]] = []
            line_issues: list[Issue] = []
            for pattern, kind, confidence in self._patterns:
                for match in pattern.finditer(line):
                    start, end = match.span()
                    if any(
                        start < seen_end and seen_start < end
                        for seen_start, seen_end in spans
                    ):
                        continue
                    spans.append((start, end))
                    line_issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Template residue ({kind}): '{match.group()}'",
                            line=line_num,
                            column=start + 1,
                            end_column=end + 1,
                            severity=self.severity,
                            confidence=confidence,
                            suggestion="Replace this placeholder with final content",
                        )
                    )

            if line_issues and not is_example_line(content, filename, line_num):
                issues.extend(line_issues)

        return sorted(issues, key=lambda issue: (issue.line, issue.column))


class UnclosedCodeFenceRule(Rule):
    """M007: Detect fenced code blocks without a closing delimiter."""

    id = "M007"
    name = "Unclosed Code Fence"
    description = "Detects fenced code blocks without a matching closing delimiter"
    severity = Severity.ERROR
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "raw"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check Markdown for code fences that reach end of file."""
        if not is_markdown_file(filename):
            return []

        return [
            Issue(
                rule_id=self.id,
                message=f"Unclosed code fence: '{block.fence}'",
                line=block.start_line,
                column=block.column,
                end_column=block.column + len(block.fence),
                severity=self.severity,
                confidence=self.default_confidence,
                suggestion=f"Add a matching '{block.fence}' closing fence",
            )
            for block in _get_cached_markdown_parser(content).get_code_block_records()
            if not block.closed
        ]


class SkippedHeadingLevelRule(Rule):
    """M008: Detect upward Markdown heading jumps greater than one level."""

    id = "M008"
    name = "Skipped Heading Level"
    description = "Detects Markdown headings that skip an intermediate level"
    severity = Severity.WARNING
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "raw"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check consecutive visible Markdown headings for upward level jumps."""
        if not is_markdown_file(filename):
            return []

        headings = _get_cached_markdown_parser(content).get_headings()
        return [
            Issue(
                rule_id=self.id,
                message=(
                    f"Heading level jumps from {previous.level} to {current.level}"
                ),
                line=current.start_line,
                column=current.column,
                end_column=current.end_column,
                severity=self.severity,
                confidence=self.default_confidence,
                suggestion=(
                    f"Add a level-{previous.level + 1} heading before this "
                    f"level-{current.level} heading"
                ),
            )
            for previous, current in pairwise(headings)
            if current.level > previous.level + 1
        ]


class BareURLInProseRule(Rule):
    """M009: Detect raw HTTP(S) URLs in Markdown body prose."""

    id = "M009"
    name = "Bare URL in Prose"
    description = "Detects raw HTTP(S) URLs in Markdown body prose"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "prose"

    _URL: ClassVar[re.Pattern[str]] = re.compile(
        r"\bhttps?://[^\s<>\[\]{}\"'`]+", re.IGNORECASE
    )
    _LITERAL_CONTEXT: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:literal URL|URL (?:literal|string|value|format|syntax))\b",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check body prose for unwrapped HTTP(S) URLs."""
        if not is_markdown_file(filename):
            return []

        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context != "body" or is_example_line(
                content, filename, sentence.start_line
            ):
                continue
            if self._LITERAL_CONTEXT.search(sentence.text):
                continue

            for match in self._URL.finditer(sentence.text):
                url = match.group().rstrip(".,;:!?")
                while url.endswith(")") and url.count(")") > url.count("("):
                    url = url[:-1]

                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(
                    match.start() + len(url)
                )
                assert line == end_line
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Bare URL in prose: '{url}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion="Use descriptive Markdown link text",
                    )
                )

        return issues


class NonDescriptiveLinkTextRule(Rule):
    """M010: Detect vague Markdown link labels."""

    id = "M010"
    name = "Non-Descriptive Link Text"
    description = "Detects vague Markdown link labels"
    severity = Severity.WARNING
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "non_code"

    _WEAK_LABELS: ClassVar[frozenset[str]] = frozenset(
        {"here", "click here", "this link", "link"}
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check rendered Markdown links for non-descriptive labels."""
        if not is_markdown_file(filename):
            return []

        parser = _get_cached_markdown_parser(content)
        definition_destinations = {
            (reference.line, reference.destination_start, reference.destination_end)
            for reference in parser.get_references()
            if reference.is_definition
        }
        lines = content.split("\n")
        issues: list[Issue] = []

        for link in parser.get_links():
            if " ".join(link.text.split()).casefold() not in self._WEAK_LABELS:
                continue
            if (link.line, link.url_start, link.url_end) in definition_destinations:
                continue

            source = lines[link.line - 1]
            offset = link.column - 1
            if source[offset : offset + 2] == "![" or (
                offset > 0 and source[offset - 1 : offset + 1] == "!["
            ):
                continue
            if offset >= len(source) or source[offset] != "[":
                continue
            if is_example_line(content, filename, link.line):
                continue

            column = link.column + 1
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Non-descriptive link text: '{link.text}'",
                    line=link.line,
                    column=column,
                    end_column=column + len(link.text),
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Replace with text that describes the destination",
                )
            )

        return sorted(issues, key=lambda issue: (issue.line, issue.column))
