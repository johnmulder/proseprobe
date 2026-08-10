"""Style detection rules (T001-T010, T012-T016)."""

import re
from itertools import groupby
from typing import ClassVar

from proseprobe.data.style_patterns import (
    ELEGANT_VARIATION_PAIRS,
    TITLE_CASE_SMALL_WORDS,
)
from proseprobe.parsers.markdown import (
    MarkdownParser,
    is_example_line,
    is_markdown_file,
)
from proseprobe.parsers.prose import iter_prose_blocks, iter_prose_sentences
from proseprobe.rules.base import Confidence, Issue, Rule, Severity


class TitleCaseHeadingsRule(Rule):
    """T001: Detect improper title case in headings."""

    id = "T001"
    name = "Title Case Headings"
    description = "Detects improper capitalization in headings"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown"}

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for title case headings."""
        issues: list[Issue] = []
        if not is_markdown_file(filename):
            return issues

        parser = MarkdownParser(content)
        for section in parser.get_headings():
            words = section.title.split()

            # Check if it looks like title case
            capitalized_count = sum(
                1
                for w in words
                if w[0].isupper() and w.lower() not in TITLE_CASE_SMALL_WORDS
            )

            # If more than 60% of words are capitalized, it's likely title case
            if len(words) >= 3 and capitalized_count / len(words) > 0.6:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message="Title case heading (consider sentence case)",
                        line=section.start_line,
                        column=section.column,
                        end_column=section.end_column,
                        severity=self.severity,
                    )
                )

        return issues


class BoldOveruseRule(Rule):
    """T002: Detect excessive bold emphasis."""

    id = "T002"
    name = "Bold Overuse"
    description = "Detects excessive **bold** usage per paragraph"
    severity = Severity.INFO
    config_key = "thresholds.bold_overuse"
    applies_to: ClassVar[set[str]] = {"markdown"}

    def __init__(self, threshold: int = 3) -> None:
        """Initialize rule with configurable threshold.

        Args:
            threshold: Max bold phrases per paragraph.
        """
        super().__init__()
        self._threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for bold overuse."""
        issues: list[Issue] = []
        if is_markdown_file(filename):
            parser = MarkdownParser(content)
            paragraphs = parser.get_paragraphs()
        else:
            paragraphs = []
            lines = content.split("\n")
            start_line = 1
            current_lines: list[str] = []
            for line_num, line in enumerate(lines, start=1):
                if not line.strip():
                    if current_lines:
                        paragraphs.append(
                            (start_line, line_num - 1, "\n".join(current_lines))
                        )
                        current_lines = []
                    start_line = line_num + 1
                else:
                    if not current_lines:
                        start_line = line_num
                    current_lines.append(line)
            if current_lines:
                paragraphs.append((start_line, len(lines), "\n".join(current_lines)))

        for start_line, _, text in paragraphs:
            bold_count = len(re.findall(r"\*\*[^*]+\*\*", text))
            if bold_count > self._threshold:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Bold overuse: {bold_count} bold phrases in paragraph",
                        line=start_line,
                        column=1,
                        severity=self.severity,
                    )
                )

        return issues


class EmDashOveruseRule(Rule):
    """T003: Detect excessive em dash usage."""

    id = "T003"
    name = "Em Dash Overuse"
    description = "Detects excessive — for dramatic effect"
    severity = Severity.INFO
    config_key = "thresholds.em_dash_overuse"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def __init__(self, threshold: int = 5) -> None:
        """Initialize rule with configurable threshold.

        Args:
            threshold: Max em dashes per document.
        """
        super().__init__()
        self._threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for em dash overuse."""
        issues: list[Issue] = []
        # Find all em dashes
        em_dash_locations: list[tuple[int, int]] = []

        for line_num, line in self.iter_lines(content, filename):
            # Match em dash (—) or double hyphen (--)
            for match in re.finditer(r"—|--", line):
                em_dash_locations.append((line_num, match.start() + 1))

        if len(em_dash_locations) > self._threshold:
            # Report the first occurrence with a summary
            first_line, first_col = em_dash_locations[0]
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Em dash overuse: {len(em_dash_locations)} occurrences",
                    line=first_line,
                    column=first_col,
                    severity=self.severity,
                )
            )

        return issues


class QuoteInconsistencyRule(Rule):
    """T004: Detect mixed quote styles."""

    id = "T004"
    name = "Quote Inconsistency"
    description = "Detects mixed curly and straight quotes"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for quote inconsistency."""
        issues: list[Issue] = []
        lines = self.iter_lines(content, filename)
        masked_content = "\n".join(line for _, line in lines)

        has_straight = '"' in masked_content or "'" in masked_content
        # Check for curly quotes using explicit Unicode
        curly_quotes = "\u201c\u201d\u2018\u2019"  # ""''
        has_curly = any(c in masked_content for c in curly_quotes)

        if has_straight and has_curly:
            # Find first curly quote to report
            for line_num, line in lines:
                for match in re.finditer(r"[\u201c\u201d\u2018\u2019]", line):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message="Mixed quote styles (curly and straight)",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
                    return issues  # Only report once

        return issues


class EmojiInProseRule(Rule):
    """T005: Detect non-technical emoji in prose."""

    id = "T005"
    name = "Emoji in Prose"
    description = "Detects 🚀, ✨, etc. in headings or body text"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    # Common promotional/decorative emoji
    _emoji_pattern = r"[\U0001F300-\U0001F9FF]"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for emoji in prose."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for match in re.finditer(self._emoji_pattern, line):
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Emoji in prose: '{match.group()}'",
                        line=line_num,
                        column=match.start() + 1,
                        end_column=match.end() + 1,
                        severity=self.severity,
                    )
                )

        return issues


class ElegantVariationRule(Rule):
    """T006: Detect unnatural synonym usage."""

    id = "T006"
    name = "Elegant Variation"
    description = "Detects awkward synonyms to avoid repetition"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for elegant variation."""
        issues: list[Issue] = []
        for _scope, group in groupby(
            iter_prose_sentences(content, filename),
            key=lambda sentence: sentence.scope_id,
        ):
            sentences = list(group)
            scope_text = "\n".join(sentence.text for sentence in sentences).lower()
            for simple, formal in ELEGANT_VARIATION_PAIRS:
                if not re.search(simple, scope_text) or not re.search(
                    formal, scope_text
                ):
                    continue
                simple_word = simple.replace(r"\b", "")
                for sentence in sentences:
                    match = re.search(formal, sentence.text, re.IGNORECASE)
                    if match is None:
                        continue
                    line, column = sentence.source_position(match.start())
                    end_line, end_column = sentence.source_position(match.end())
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=(
                                f"Elegant variation: '{match.group()}' "
                                f"(also uses '{simple_word}')"
                            ),
                            line=line,
                            column=column,
                            end_line=end_line,
                            end_column=end_column,
                            severity=self.severity,
                        )
                    )
                    break

        return issues


class ShortPunchyFragmentsRule(Rule):
    """T007: Detect 3+ consecutive short-sentence paragraphs."""

    id = "T007"
    name = "Short Punchy Fragments"
    description = "Detects consecutive very short paragraphs for manufactured emphasis"
    severity = Severity.INFO
    config_key = "thresholds.short_punchy_fragments"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _MAX_WORDS = 5

    def __init__(self, threshold: int = 3) -> None:
        super().__init__()
        self._threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 3+ consecutive short-sentence paragraphs."""
        issues: list[Issue] = []
        run: list[int] = []

        def flush() -> None:
            nonlocal run
            if len(run) >= self._threshold:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Short punchy fragments: {len(run)} consecutive short paragraphs",
                        line=run[0],
                        column=1,
                        severity=self.severity,
                    )
                )
            run = []

        for block in iter_prose_blocks(content, filename):
            if block.break_before or block.context != "body":
                flush()
            if block.context != "body":
                continue
            text = " ".join(line.strip() for _, line in block.lines)
            if len(text.split()) <= self._MAX_WORDS:
                run.append(block.start_line)
            else:
                flush()
        flush()

        return issues


class SentenceLengthRule(Rule):
    """T008: Detect excessively long sentences."""

    id = "T008"
    name = "Sentence Length"
    description = "Detects sentences exceeding a word count threshold"
    severity = Severity.INFO
    config_key = "thresholds.sentence_length_max"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def __init__(self, threshold: int = 40) -> None:
        super().__init__()
        self.threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect excessively long sentences."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            words = sentence.text.split()
            if len(words) <= self.threshold:
                continue
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=(
                        f"Long sentence: {len(words)} words "
                        f"(threshold {self.threshold})"
                    ),
                    line=sentence.start_line,
                    column=sentence.start_column,
                    end_line=sentence.end_line,
                    end_column=sentence.end_column,
                    severity=self.severity,
                )
            )
        return issues


class RepeatedOrMixedPunctuationRule(Rule):
    """T010: Detect repeated or mixed terminal punctuation."""

    id = "T010"
    name = "Repeated or Mixed Punctuation"
    description = "Detects repeated, mixed, and rhetorical punctuation clusters"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _CLUSTER: ClassVar[re.Pattern[str]] = re.compile(r"(?:\.{3,}|\u2026)[!?]+|[!?]{2,}")

    def check(self, content: str, filename: str) -> list[Issue]:
        """Report repeated or mixed punctuation in source-mapped prose."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if is_example_line(content, filename, sentence.start_line):
                continue
            for match in self._CLUSTER.finditer(sentence.text):
                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(match.end())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Repeated or mixed punctuation: '{match.group()}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion="Use a single terminal punctuation mark",
                    )
                )
        return issues


class RhetoricalEllipsisRule(Rule):
    """T012: Detect rhetorical three-period ellipses in prose."""

    id = "T012"
    name = "Rhetorical Ellipsis"
    description = "Detects rhetorical three-period ellipses in prose"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _ELLIPSIS: ClassVar[re.Pattern[str]] = re.compile(r"(?<![\d.])\.{3}(?![\d.!?])")
    _EXPLICIT_CONTEXT: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:ellipsis|omission|omit(?:ted|s|ting)?|truncat(?:e|ed|es|ion))\b",
        re.IGNORECASE,
    )
    _OUTPUT_PREFIX: ClassVar[re.Pattern[str]] = re.compile(
        r"^\s*(?:console|log|message|output)\s*:", re.IGNORECASE
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Report rhetorical ellipses in source-mapped prose."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if (
                is_example_line(content, filename, sentence.start_line)
                or self._EXPLICIT_CONTEXT.search(sentence.text)
                or self._OUTPUT_PREFIX.match(sentence.text)
                or sentence.text.strip().strip("'\"\u201c\u201d\u2018\u2019`()[]{}")
                == "..."
            ):
                continue
            for match in self._ELLIPSIS.finditer(sentence.text):
                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(match.end())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message="Rhetorical ellipsis: '...'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion=("Use direct punctuation or complete the thought"),
                    )
                )
        return issues


class AllCapsEmphasisRule(Rule):
    """T013: Detect emphatic runs of uppercase prose words."""

    id = "T013"
    name = "ALL-CAPS Emphasis"
    description = "Detects emphatic runs of uppercase words in prose"
    severity = Severity.INFO
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _RUN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?<![\w'-])[A-Z]+(?:'[A-Z]+)?"
        r"(?:[ \t]+[A-Z]+(?:'[A-Z]+)?){2,}(?![\w'-])"
    )
    _WORD: ClassVar[re.Pattern[str]] = re.compile(r"[A-Z]+(?:'[A-Z]+)?")
    _EMPHASIS_CUES = frozenset(
        {
            "ALWAYS",
            "CANNOT",
            "CAUTION",
            "DANGER",
            "DO",
            "DOES",
            "DON'T",
            "IMPORTANT",
            "MUST",
            "NEVER",
            "NOT",
            "ONLY",
            "REQUIRED",
            "SHALL",
            "SHOULD",
            "THIS",
            "URGENT",
            "WARNING",
            "WILL",
            "YOU",
        }
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Report uppercase prose runs with an emphasis cue."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item"} or is_example_line(
                content, filename, sentence.start_line
            ):
                continue
            for match in self._RUN.finditer(sentence.text):
                if self._EMPHASIS_CUES.isdisjoint(self._WORD.findall(match.group())):
                    continue
                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(match.end())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"ALL-CAPS emphasis: '{match.group()}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion=(
                            "Use normal sentence casing unless uppercase is required"
                        ),
                    )
                )
        return issues


class ParentheticalOverloadRule(Rule):
    """T014: Detect multiple substantial parentheticals in one sentence."""

    id = "T014"
    name = "Parenthetical Overload"
    description = "Detects sentences overloaded with substantial parentheticals"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _MIN_PARENTHESES = 3
    _MIN_WORDS = 3
    _WORD: ClassVar[re.Pattern[str]] = re.compile(r"\b\w+(?:[-'\u2019]\w+)*\b")

    def check(self, content: str, filename: str) -> list[Issue]:
        """Report sentences with three substantial top-level parentheticals."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            if is_example_line(content, filename, sentence.start_line):
                continue

            openings: list[int] = []
            spans: list[tuple[int, int]] = []
            for offset, char in enumerate(sentence.text):
                if char == "(":
                    openings.append(offset)
                elif char == ")" and openings:
                    start = openings.pop()
                    if (
                        not openings
                        and len(self._WORD.findall(sentence.text[start + 1 : offset]))
                        >= self._MIN_WORDS
                    ):
                        spans.append((start, offset + 1))

            if len(spans) < self._MIN_PARENTHESES:
                continue
            start_line, start_column = sentence.source_position(spans[0][0])
            end_line, end_column = sentence.source_position(spans[-1][1])
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=(
                        "Parenthetical overload: "
                        f"{len(spans)} substantial parentheticals in one sentence"
                    ),
                    line=start_line,
                    column=start_column,
                    end_line=end_line,
                    end_column=end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion=(
                        "Rewrite the sentence or move parenthetical details "
                        "into separate sentences"
                    ),
                )
            )
        return issues


class NestedParentheticalRule(Rule):
    """T015: Detect balanced parentheses nested inside other parentheses."""

    id = "T015"
    name = "Nested Parenthetical"
    description = "Detects parentheses nested within prose parentheses"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose blocks for balanced inner parentheticals."""
        issues: list[Issue] = []
        for block in iter_prose_blocks(content, filename):
            openings: list[tuple[int, int]] = []
            pairs: list[
                tuple[tuple[int, int], tuple[int, int], tuple[int, int] | None]
            ] = []
            for line_num, line in block.lines:
                for column, char in enumerate(line, start=1):
                    if char == "(":
                        openings.append((line_num, column))
                    elif char == ")" and openings:
                        start = openings.pop()
                        parent = openings[-1] if openings else None
                        pairs.append((start, (line_num, column + 1), parent))

            matched_starts = {start for start, _, _ in pairs}
            for start, end, parent in pairs:
                if parent is None or parent not in matched_starts:
                    continue
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message="Nested parenthetical",
                        line=start[0],
                        column=start[1],
                        end_line=end[0] if end[0] != start[0] else None,
                        end_column=end[1],
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion=(
                            "Remove one level of parentheses or rewrite the sentence"
                        ),
                    )
                )
        return sorted(issues, key=lambda issue: (issue.line, issue.column))


class SlashAlternativeRule(Rule):
    """T016: Detect the ambiguous slash alternative 'and/or'."""

    id = "T016"
    name = "Slash Alternative"
    description = "Detects ambiguous 'and/or' alternatives"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _AND_OR: ClassVar[re.Pattern[str]] = re.compile(
        r"(?<![/\w])and/or(?![/\w])", re.IGNORECASE
    )
    _URL: ClassVar[re.Pattern[str]] = re.compile(r"https?://\S+", re.IGNORECASE)

    def check(self, content: str, filename: str) -> list[Issue]:
        """Report standalone and/or phrases in source-mapped prose."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if is_example_line(content, filename, sentence.start_line):
                continue
            urls = tuple(self._URL.finditer(sentence.text))
            for match in self._AND_OR.finditer(sentence.text):
                if any(url.start() <= match.start() < url.end() for url in urls):
                    continue
                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(match.end())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Slash alternative: '{match.group()}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion="Choose 'and', 'or', or 'both' explicitly",
                    )
                )
        return issues
