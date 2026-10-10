"""Markup detection rules (M001-M012)."""

import html
import os
import re
import string
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from fnmatch import fnmatchcase
from html.parser import HTMLParser
from itertools import pairwise
from pathlib import Path
from threading import Lock
from typing import ClassVar
from urllib.parse import unquote, urlsplit

from proseprobe.parsers.markdown import (
    MarkdownParser,
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


@dataclass(frozen=True)
class _LocalTarget:
    status: str
    anchors: frozenset[str] = frozenset()
    detail: str = ""


class LocalMarkdownLinkRule(Rule):
    """M012: Check literal Markdown files inside an explicit project root."""

    id = "M012"
    name = "Unresolved Local Markdown Target"
    description = "Checks literal local Markdown files and supported GitHub fragments"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "non_code"
    config_key = "local_links"

    def __init__(
        self,
        local_links: bool = False,
        project_root: str | None = None,
        markdown_anchor_style: str = "off",
        local_link_exclude: list[str] | None = None,
    ) -> None:
        super().__init__()
        if markdown_anchor_style not in {"off", "github"}:
            raise ValueError("markdown_anchor_style must be off or github")
        self._root = Path(project_root).resolve() if project_root else None
        if local_links and (
            project_root is None
            or not Path(project_root).is_absolute()
            or self._root is None
            or not self._root.is_dir()
        ):
            raise ValueError("local_links requires an absolute existing project_root")
        self._enabled = local_links
        self._style = markdown_anchor_style
        self._exclude = tuple(local_link_exclude or [])
        self._cache: dict[Path, _LocalTarget] = {}
        self._cache_lock = Lock()
        self._batch = False
        if not local_links:
            self.severity = Severity.OFF

    def begin_scan(self) -> None:
        """Start one file batch with a fresh bounded target-read cache."""
        with self._cache_lock:
            self._cache.clear()
        self._batch = True

    def end_scan(self) -> None:
        """Finish the batch so standalone checks start fresh."""
        self._batch = False

    def _resolve_target(
        self, source: Path, destination: str
    ) -> tuple[Path, str] | None:
        assert self._root is not None
        resolved = html.unescape(SameDocumentFragmentRule._unescape(destination))
        if (
            any(ord(char) < 32 for char in resolved)
            or re.search(r"%(?![0-9a-fA-F]{2})", resolved)
            or "?" in resolved
        ):
            return None
        try:
            parts = urlsplit(resolved)
        except ValueError:
            return None
        if parts.scheme or parts.netloc or not parts.path or parts.path.startswith("/"):
            return None
        if re.search(r"%2f|%5c", parts.path, re.IGNORECASE):
            return None
        try:
            path = unquote(parts.path, errors="strict")
            fragment = unquote(parts.fragment, errors="strict")
        except UnicodeDecodeError:
            return None
        if (
            "\\" in path
            or any(ord(char) < 32 for char in path)
            or Path(path).suffix.lower() not in {".md", ".markdown"}
        ):
            return None
        lexical = Path(os.path.normpath(source.parent / path))
        try:
            relative = lexical.relative_to(self._root)
        except ValueError:
            return None
        if any(fnmatchcase(relative.as_posix(), pattern) for pattern in self._exclude):
            return None
        try:
            target = lexical.resolve()
            relative = target.relative_to(self._root)
        except (OSError, RuntimeError, ValueError):
            return None
        if any(fnmatchcase(relative.as_posix(), pattern) for pattern in self._exclude):
            return None
        return target, fragment

    def _read_target(self, path: Path) -> _LocalTarget:
        with self._cache_lock:
            if path in self._cache:
                return self._cache[path]
            try:
                content = path.read_text(encoding="utf-8")
            except FileNotFoundError:
                result = _LocalTarget("missing")
            except (OSError, UnicodeDecodeError) as exc:
                result = _LocalTarget("unreadable", detail=str(exc))
            else:
                document = (
                    SameDocumentFragmentRule._document(content)
                    if self._style == "github"
                    else None
                )
                result = (
                    _LocalTarget(
                        "unsupported",
                        detail="generated markup has no static anchor contract",
                    )
                    if self._style == "github" and document is None
                    else _LocalTarget(
                        "present", frozenset(document[0]) if document else frozenset()
                    )
                )
            self._cache[path] = result
            return result

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check supported destinations with absolute source identity."""
        if not self._enabled or self._root is None or not is_markdown_file(filename):
            return []
        source = Path(filename)
        if not source.is_absolute():
            return []
        try:
            source = source.resolve()
            source.relative_to(self._root)
        except (OSError, RuntimeError, ValueError):
            return []
        document = SameDocumentFragmentRule._document(content)
        if document is None:
            return []
        if not self._batch:
            with self._cache_lock:
                self._cache.clear()
        issues: list[Issue] = []
        for destination, line, column, end_column in document[1]:
            resolved = self._resolve_target(source, destination)
            if resolved is None:
                continue
            path, fragment = resolved
            target = self._read_target(path)
            if target.status == "missing":
                message = f"No local Markdown file for '{destination}'"
            elif target.status == "unreadable" or (
                target.status == "unsupported" and fragment and self._style == "github"
            ):
                message = (
                    f"Could not validate local target '{destination}': {target.detail}"
                )
            elif (
                fragment and self._style == "github" and fragment not in target.anchors
            ):
                message = f"No GitHub fragment target for '{destination}'"
            else:
                continue
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=message,
                    line=line,
                    column=column,
                    end_column=end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Check the file path, selected renderer, and target access",
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

        parser = _get_cached_markdown_parser(content)
        issues: list[Issue] = []
        for previous, current in pairwise(parser.get_headings()):
            if current.level <= previous.level + 1:
                continue
            column, end_column = parser.heading_diagnostic_span(current)
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=(
                        f"Heading level jumps from {previous.level} to {current.level}"
                    ),
                    line=current.start_line,
                    column=column,
                    end_column=end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion=(
                        f"Add a level-{previous.level + 1} heading before this "
                        f"level-{current.level} heading"
                    ),
                )
            )
        return issues


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


@dataclass(frozen=True)
class _InlineLink:
    start: int
    end: int
    text: str
    destination: str
    destination_start: int
    destination_end: int
    is_image: bool


class _ExplicitAnchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "textarea"}:
            return
        attributes = dict(attrs)
        if value := attributes.get("id"):
            self.targets.add(value)
        if tag == "a" and (value := attributes.get("name")):
            self.targets.add(value)


class SameDocumentFragmentRule(Rule):
    """M011: Validate fragments under an explicitly selected GitHub anchor policy."""

    id = "M011"
    name = "Unresolved Same-Document Fragment"
    description = (
        "Detects unresolved same-document links under the GitHub anchor policy"
    )
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "non_code"
    config_key = "markdown_anchor_style"

    def __init__(self, markdown_anchor_style: str = "off") -> None:
        super().__init__()
        if markdown_anchor_style not in {"off", "github"}:
            raise ValueError("markdown_anchor_style must be off or github")
        self._style = markdown_anchor_style
        if self._style == "off":
            self.severity = Severity.OFF

    @staticmethod
    def _escaped(text: str, index: int) -> bool:
        backslashes = 0
        while index > 0 and text[index - 1] == "\\":
            backslashes += 1
            index -= 1
        return backslashes % 2 == 1

    @classmethod
    def _destination(cls, text: str, start: int) -> tuple[str, int, int, int] | None:
        while start < len(text) and text[start] in " \t":
            start += 1
        if start >= len(text):
            return None
        if text[start] == "<":
            index = start + 1
            while index < len(text):
                if text[index] == ">" and not cls._escaped(text, index):
                    return text[start + 1 : index], start + 1, index, index + 1
                if text[index] in "<\n\r" and not cls._escaped(text, index):
                    return None
                index += 1
            return None
        depth = 0
        index = start
        while index < len(text):
            char = text[index]
            if (
                char == "\\"
                and index + 1 < len(text)
                and text[index + 1] in string.punctuation
            ):
                index += 2
                continue
            if char in " \t\n\r" or (char == ")" and depth == 0):
                break
            if char == "<" or ord(char) < 32:
                return None
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        if depth != 0:
            return None
        return text[start:index], start, index, index

    @classmethod
    def _link_end(cls, text: str, index: int) -> int | None:
        had_space = index < len(text) and text[index] in " \t"
        while index < len(text) and text[index] in " \t":
            index += 1
        if index < len(text) and text[index] == ")":
            return index + 1
        if not had_space or index >= len(text) or text[index] not in "\"'(":
            return None
        closing = ")" if text[index] == "(" else text[index]
        index += 1
        while index < len(text) and (
            text[index] != closing or cls._escaped(text, index)
        ):
            index += 1
        if index == len(text):
            return None
        index += 1
        while index < len(text) and text[index] in " \t":
            index += 1
        return index + 1 if index < len(text) and text[index] == ")" else None

    @classmethod
    def _links(cls, text: str) -> Iterator[_InlineLink]:
        index = 0
        while index < len(text):
            if text[index] != "[" or cls._escaped(text, index):
                index += 1
                continue
            start = index
            depth = 1
            index += 1
            while index < len(text) and depth:
                if text[index] == "\\" and index + 1 < len(text):
                    index += 2
                    continue
                depth += (text[index] == "[") - (text[index] == "]")
                index += 1
            if depth or index >= len(text) or text[index] != "(":
                continue
            parsed = cls._destination(text, index + 1)
            if parsed is None:
                continue
            destination, value_start, value_end, after = parsed
            end = cls._link_end(text, after)
            if end is None:
                continue
            yield _InlineLink(
                start,
                end,
                text[start + 1 : index - 1],
                destination,
                value_start,
                value_end,
                start > 0
                and text[start - 1] == "!"
                and not cls._escaped(text, start - 1),
            )
            index = end

    @staticmethod
    def _unescape(text: str) -> str:
        return re.sub(r"\\([" + re.escape(string.punctuation) + r"])", r"\1", text)

    @classmethod
    def _heading_text(cls, title: str, parser: MarkdownParser) -> str:
        code: dict[str, str] = {}
        for index, (start, end) in reversed(
            list(enumerate(parser._find_inline_code_spans(title)))
        ):
            raw = title[start:end]
            delimiter = len(raw) - len(raw.lstrip("`"))
            value = raw[delimiter:-delimiter].replace("\n", " ")
            if value.startswith(" ") and value.endswith(" ") and value.strip():
                value = value[1:-1]
            marker = f"\x00{index}\x00"
            code[marker] = value
            title = title[:start] + marker + title[end:]
        for link in reversed(list(cls._links(title))):
            title = title[: link.start] + link.text + title[link.end :]
        definitions = {
            reference.label
            for reference in parser.get_references()
            if reference.is_definition
        }
        title = re.sub(
            r"\[([^\]]+)\]\[([^\]]*)\]",
            lambda match: (
                match.group(1)
                if parser._normalize_reference_label(match.group(2) or match.group(1))
                in definitions
                else match.group()
            ),
            title,
        )
        title = re.sub(r"<!--.*?-->", "", title)
        title = re.sub(r"</?[A-Za-z][\w-]*(?:\s+[^<>]*?)?\s*/?>", "", title)
        title = re.sub(r"(?<!\\)(\*{1,2})(?=\S)(.+?)(?<=\S)\1", r"\2", title)
        title = re.sub(r"(?<![\w\\])(_{1,2})(?=\S)(.+?)(?<=\S)\1(?!\w)", r"\2", title)
        title = html.unescape(cls._unescape(title))
        for marker, value in code.items():
            title = title.replace(marker, value)
        return title

    @classmethod
    def _targets(cls, parser: MarkdownParser, anchor_source: str) -> set[str]:
        headings: set[str] = set()
        for heading in parser.get_headings():
            text = cls._heading_text(heading.title, parser).lower()
            base = "".join(
                "-" if char == " " else char
                for char in text
                if char == " " or char in "_-" or unicodedata.category(char)[0] in "LNM"
            )
            candidate = base
            suffix = 0
            while candidate in headings:
                suffix += 1
                candidate = f"{base}-{suffix}"
            headings.add(candidate)
        custom = _ExplicitAnchors()
        custom.feed(anchor_source)
        return headings | custom.targets

    @classmethod
    def _document(
        cls, content: str
    ) -> tuple[set[str], list[tuple[str, int, int, int]]] | None:
        """Extract static anchors and supported link destination source spans."""
        parser = _get_cached_markdown_parser(content)
        excluded = parser._code_lines() | parser._front_matter_lines()
        masked_lines = [
            " " * len(line) if number in excluded else parser._mask_inline_code(line)
            for number, line in enumerate(content.split("\n"), 1)
        ]
        masked_source = "\n".join(masked_lines)
        chars = list(masked_source)
        for comment in re.finditer(r"<!--.*?(?:-->|$)", masked_source, re.DOTALL):
            for index in range(comment.start(), comment.end()):
                if chars[index] != "\n":
                    chars[index] = " "
        masked_lines = "".join(chars).split("\n")
        anchor_lines = list(enumerate(masked_lines, 1))
        active = {number for number, line in anchor_lines if line.strip()}
        if parser._mdx_block_lines() & active or any(
            "{%" in line or "{{" in line for _, line in anchor_lines
        ):
            return None
        references = parser.get_references()
        definition_lines = {
            reference.line for reference in references if reference.is_definition
        }
        reference_uses: dict[int, list[MarkdownReference]] = {}
        for reference in references:
            if not reference.is_definition:
                reference_uses.setdefault(reference.line, []).append(reference)
        html_lines: list[str] = []
        for number, line in anchor_lines:
            if number in definition_lines:
                html_lines.append("")
                continue
            chars = list(line)
            for link in cls._links(line):
                start = (
                    link.start - 1 if link.is_image else link.start + len(link.text) + 2
                )
                chars[start : link.end] = " " * (link.end - start)
            for reference in reference_uses.get(number, []):
                start = reference.column - 1
                if (
                    reference.line == number
                    and not reference.is_definition
                    and line[start : start + 2] == "!["
                    and not cls._escaped(line, start)
                ):
                    end = reference.end_column - 1
                    chars[start:end] = " " * (end - start)
            html_lines.append("".join(chars))
        anchor_source = "\n".join(
            "".join(
                "&lt;" if char == "<" and cls._escaped(line, index) else char
                for index, char in enumerate(line)
            )
            for line in html_lines
        )
        targets = cls._targets(parser, anchor_source)
        visible = {number for number, _ in parser.get_lines()} - excluded
        source_lines = content.split("\n")
        destinations: list[tuple[str, int, int, int]] = []
        for line_num, line in anchor_lines:
            if line_num not in visible or line_num in definition_lines:
                continue
            for link in cls._links(line):
                if not link.is_image:
                    destinations.append(
                        (
                            link.destination,
                            line_num,
                            link.destination_start + 1,
                            link.destination_end + 1,
                        )
                    )
        used = {
            reference.label
            for reference in references
            if not reference.is_definition
            and reference.line in visible
            and masked_lines[reference.line - 1][
                reference.column - 1 : reference.column
            ]
            in {"[", "!"}
            and (
                not source_lines[reference.line - 1][reference.column - 1 :].startswith(
                    "!["
                )
                or cls._escaped(source_lines[reference.line - 1], reference.column - 1)
            )
        }
        seen: set[str] = set()
        for reference in references:
            if not reference.is_definition or reference.label in seen:
                continue
            seen.add(reference.label)
            if reference.label not in used or reference.line not in visible:
                continue
            parsed = cls._destination(
                source_lines[reference.line - 1], reference.destination_start - 1
            )
            if parsed is not None:
                destination, start, end, after = parsed
                source = source_lines[reference.line - 1]
                if cls._link_end(source + ")", after) == len(source) + 1:
                    destinations.append(
                        (destination, reference.line, start + 1, end + 1)
                    )
        return targets, destinations

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check supported static fragments while preserving destination spans."""
        if self._style == "off" or not is_markdown_file(filename):
            return []
        document = self._document(content)
        if document is None:
            return []
        targets, destinations = document
        issues: list[Issue] = []
        for destination, line_num, column, end_column in destinations:
            resolved = html.unescape(self._unescape(destination))
            if not resolved.startswith("#") or resolved == "#":
                continue
            fragment = unquote(resolved[1:])
            if fragment in targets:
                continue
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"No same-document target for '{destination}'",
                    line=line_num,
                    column=column,
                    end_column=end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Use an existing heading fragment or explicit anchor",
                )
            )
        return sorted(issues, key=lambda issue: (issue.line, issue.column))
