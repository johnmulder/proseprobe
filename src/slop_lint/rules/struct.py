"""Structural detection rules (S001-S007)."""

import re

from slop_lint.data.patterns import (
    CHALLENGE_CONCLUSION_PATTERNS,
    INLINE_HEADER_LIST_PATTERN,
    NEGATIVE_PARALLELISM_PATTERNS,
    PARTICIPLE_CHAIN_PATTERNS,
    RULE_OF_THREE_PATTERNS,
    SIGNIFICANCE_PATTERNS,
)
from slop_lint.rules.base import Issue, Rule, Severity


class RuleOfThreeRule(Rule):
    """S001: Detect excessive triadic patterns."""

    id = "S001"
    name = "Rule of Three"
    description = "Detects excessive 'X, Y, and Z' patterns"
    severity = Severity.INFO
    fixable = False
    applies_to = {"markdown"}
    content_scope = "prose"

    def __init__(self, threshold: int = 3) -> None:
        """Initialize rule with configurable threshold.

        Args:
            threshold: Flag if more than N triads in content.
        """
        self._threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for rule of three patterns."""
        issues: list[Issue] = []
        triads_found: list[tuple[int, int, str]] = []

        for line_num, line in self.iter_lines(content, filename):
            for pattern in RULE_OF_THREE_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    triads_found.append((line_num, match.start() + 1, match.group()))

        # Only flag if excessive triads (more than threshold)
        if len(triads_found) > self._threshold:
            for line_num, col, text in triads_found:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Triadic pattern (rule of three): '{text}'",
                        line=line_num,
                        column=col,
                        severity=self.severity,
                    )
                )

        return issues


class NegativeParallelismRule(Rule):
    """S002: Detect contrastive constructions."""

    id = "S002"
    name = "Negative Parallelism"
    description = "Detects 'Not only... but also...' patterns"
    severity = Severity.INFO
    fixable = False
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for negative parallelism."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in NEGATIVE_PARALLELISM_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Negative parallelism: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class ChallengeConclusionsRule(Rule):
    """S003: Detect formulaic challenge conclusions."""

    id = "S003"
    name = "Challenge Conclusions"
    description = "Detects 'Despite its... faces challenges...' patterns"
    severity = Severity.WARNING
    fixable = False
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for challenge conclusions."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in CHALLENGE_CONCLUSION_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Formulaic conclusion: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class InlineHeaderListsRule(Rule):
    """S004: Detect bold headers in bullet lists."""

    id = "S004"
    name = "Inline-Header Lists"
    description = "Detects '- **Header:** Description' pattern"
    severity = Severity.INFO
    fixable = False
    applies_to = {"markdown"}
    content_scope = "prose"

    def __init__(self, threshold: int = 3) -> None:
        """Initialize rule with configurable threshold.

        Args:
            threshold: Flag if >= N consecutive inline headers.
        """
        self._threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for inline header lists."""
        issues: list[Issue] = []
        consecutive_count = 0
        consecutive_start = 0

        for line_num, line in self.iter_lines(content, filename):
            if re.match(INLINE_HEADER_LIST_PATTERN, line.strip()):
                if consecutive_count == 0:
                    consecutive_start = line_num
                consecutive_count += 1
            else:
                # End of consecutive block
                if consecutive_count >= self._threshold:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=(
                                f"Inline header list pattern "
                                f"({consecutive_count} items)"
                            ),
                            line=consecutive_start,
                            column=1,
                            severity=self.severity,
                        )
                    )
                consecutive_count = 0

        # Check final block
        if consecutive_count >= self._threshold:
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Inline header list pattern ({consecutive_count} items)",
                    line=consecutive_start,
                    column=1,
                    severity=self.severity,
                )
            )

        return issues


class SignificanceEmphasisRule(Rule):
    """S005: Detect undue importance claims."""

    id = "S005"
    name = "Significance Emphasis"
    description = "Detects 'pivotal moment', 'key turning point' patterns"
    severity = Severity.WARNING
    fixable = False
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for significance emphasis."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in SIGNIFICANCE_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Significance emphasis: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class SuperficialAnalysisRule(Rule):
    """S006: Detect present participle chains."""

    id = "S006"
    name = "Superficial Analysis"
    description = "Detects 'highlighting...underscoring...' chains"
    severity = Severity.WARNING
    fixable = False
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for superficial analysis patterns."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in PARTICIPLE_CHAIN_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Participle chain: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class FalseRangesRule(Rule):
    """S007: Detect incoherent scales."""

    id = "S007"
    name = "False Ranges"
    description = "Detects 'from X to Y' with incoherent extremes"
    severity = Severity.INFO
    fixable = False
    applies_to = {"markdown"}
    content_scope = "prose"

    # Common false range patterns
    _patterns = [
        r"from\s+(\w+)\s+to\s+(\w+)",
        r"ranging from\s+(\w+)\s+to\s+(\w+)",
    ]

    # Known incoherent pairs (both should be flagged)
    _incoherent_pairs = {
        ("small", "large"),
        ("simple", "complex"),
        ("basic", "advanced"),
        ("local", "global"),
        ("personal", "professional"),
        ("ancient", "modern"),
        ("traditional", "contemporary"),
    }

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for false ranges."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in self._patterns:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    word1 = match.group(1).lower()
                    word2 = match.group(2).lower()

                    # Check if this is a known incoherent pair
                    for pair in self._incoherent_pairs:
                        if (word1, word2) == pair or (word2, word1) == pair:
                            issues.append(
                                Issue(
                                    rule_id=self.id,
                                    message=f"Vague range: '{match.group()}'",
                                    line=line_num,
                                    column=match.start() + 1,
                                    end_column=match.end() + 1,
                                    severity=self.severity,
                                )
                            )
                            break

        return issues
