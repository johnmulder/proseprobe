"""Structural detection rules (S001-S021 and S025)."""

import re
from itertools import groupby, pairwise
from typing import ClassVar

from proseprobe.data.patterns import (
    ANECDOTE_EVIDENCE_PATTERNS,
    CHALLENGE_CONCLUSION_PATTERNS,
    CITATION_NAME_DROP_PATTERN,
    INLINE_HEADER_LIST_PATTERN,
    LISTICLE_PROSE_PATTERNS,
    NEGATIVE_PARALLELISM_PATTERNS,
    PARTICIPLE_CHAIN_PATTERNS,
    RULE_OF_THREE_PATTERNS,
    SIGNIFICANCE_PATTERNS,
    SLIDE_DECK_BUZZWORDS,
)
from proseprobe.data.phrases import (
    ALIGNMENT_RITUAL_PHRASES,
    CORPORATE_EUPHEMISM_PHRASES,
    FRACTAL_SUMMARY_PHRASES,
    SIGNPOSTED_CONCLUSION_PHRASES,
)
from proseprobe.parsers.markdown import _get_cached_parser, is_markdown_file
from proseprobe.parsers.prose import (
    ProseSentence,
    iter_prose_blocks,
    iter_prose_scopes,
    iter_prose_sentences,
)
from proseprobe.rules.base import Confidence, Issue, Rule, Severity


class RuleOfThreeRule(Rule):
    """S001: Detect excessive triadic patterns."""

    id = "S001"
    name = "Rule of Three"
    description = "Detects excessive 'X, Y, and Z' patterns"
    severity = Severity.INFO
    config_key = "thresholds.rule_of_three"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def __init__(self, threshold: int = 3) -> None:
        """Initialize rule with configurable threshold.

        Args:
            threshold: Flag if more than N triads in content.
        """
        super().__init__()
        self._threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for rule of three patterns."""
        issues: list[Issue] = []
        for block in iter_prose_scopes(content, filename):
            triads_found: list[tuple[int, int, int, str]] = []
            for line_num, line in block.lines:
                for pattern in RULE_OF_THREE_PATTERNS:
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        triads_found.append(
                            (
                                line_num,
                                match.start() + 1,
                                match.end() + 1,
                                match.group(),
                            )
                        )

            if len(triads_found) > self._threshold:
                for line_num, col, end_col, text in triads_found:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Triadic pattern (rule of three): '{text}'",
                            line=line_num,
                            column=col,
                            end_column=end_col,
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
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
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
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
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
    config_key = "thresholds.inline_header_lists"
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "non_code"

    def __init__(self, threshold: int = 3) -> None:
        """Initialize rule with configurable threshold.

        Args:
            threshold: Flag if >= N consecutive inline headers.
        """
        super().__init__()
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
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
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
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
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
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    # Common false range patterns
    _patterns: ClassVar[list[str]] = [
        r"from\s+(\w+)\s+to\s+(\w+)",
        r"ranging from\s+(\w+)\s+to\s+(\w+)",
    ]

    # Known incoherent pairs (both should be flagged)
    _incoherent_pairs: ClassVar[set[tuple[str, str]]] = {
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


# ---------- Phase 10: S008-S016 ----------


class DramaticCountdownRule(Rule):
    """S008: Detect 'Not X. Not Y. Just Z.' countdown pattern."""

    id = "S008"
    name = "Dramatic Countdown"
    description = "Detects 'Not X. Not Y. Just Z.' dramatic countdown"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _pattern = re.compile(
        r"Not\s+[^.!?\n]+[.!]\s*Not\s+[^.!?\n]+[.!]\s*"
        r"(?:Just|But|Only|Simply)\s+[^.!?\n]+[.!]",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 'Not X. Not Y. Just Z.' countdown pattern."""
        """Check content for detect 'Not X. Not Y. Just Z.' countdown pattern."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            match = self._pattern.search(line)
            if match:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Dramatic countdown: '{match.group().strip()}'",
                        line=line_num,
                        column=match.start() + 1,
                        end_column=match.end() + 1,
                        severity=self.severity,
                    )
                )
        return issues


class RhetoricalSelfAnswerRule(Rule):
    """S009: Detect 'The X? A Y.' rhetorical self-answer."""

    id = "S009"
    name = "Rhetorical Self-Answer"
    description = "Detects 'The X? Y.' self-posed rhetorical question"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    # Short question (<60 chars) followed by short answer (<60 chars)
    _pattern = re.compile(
        r"([A-Z][^.!?\n]{0,60}\?)\s+([A-Z][^.!?\n]{0,50}[.!])",
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 'The X? A Y.' rhetorical self-answer."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for match in self._pattern.finditer(line):
                answer = match.group(2)
                # Only flag if the answer is short (< 8 words) — fragment
                if len(answer.split()) < 8:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Rhetorical self-answer: '{match.group().strip()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class AnaphoraAbuseRule(Rule):
    """S010: Detect 3+ consecutive sentences with the same opening."""

    id = "S010"
    name = "Anaphora Abuse"
    description = "Detects repeated sentence openings (anaphora)"
    severity = Severity.WARNING
    config_key = "thresholds.anaphora_abuse"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def __init__(self, threshold: int = 3) -> None:
        super().__init__()
        self._threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 3+ consecutive sentences with the same opening."""
        issues: list[Issue] = []
        records = iter_prose_sentences(content, filename)
        for _scope, group in groupby(records, key=lambda sentence: sentence.scope_id):
            sentences = [
                sentence
                for sentence in group
                if sentence.context in {"body", "blockquote"}
            ]
            if not sentences:
                continue
            run_start = 0
            for index in range(1, len(sentences) + 1):
                same_opening = index < len(sentences) and (
                    sentences[index].text.split()[0].casefold()
                    == sentences[index - 1].text.split()[0].casefold()
                )
                if same_opening:
                    continue
                run_len = index - run_start
                if run_len >= self._threshold:
                    first = sentences[run_start]
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=(
                                f"Anaphora: {run_len} consecutive sentences "
                                f"starting with '{first.text.split()[0]}'"
                            ),
                            line=first.start_line,
                            column=first.start_column,
                            severity=self.severity,
                        )
                    )
                run_start = index

        return issues


class GerundFragmentLitanyRule(Rule):
    """S011: Detect 3+ consecutive gerund-phrase fragments."""

    id = "S011"
    name = "Gerund Fragment Litany"
    description = "Detects consecutive gerund fragments ('Fixing X. Writing Y.')"
    severity = Severity.INFO
    config_key = "thresholds.gerund_fragment_litany"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _gerund_fragment = re.compile(r"^[A-Z][a-z]*ing\b[^.!?]{0,60}[.!?]$")

    def __init__(self, threshold: int = 3) -> None:
        super().__init__()
        self._threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 3+ consecutive gerund-phrase fragments."""
        issues: list[Issue] = []
        records = iter_prose_sentences(content, filename)
        for _scope, group in groupby(records, key=lambda sentence: sentence.scope_id):
            sentences = [
                sentence
                for sentence in group
                if sentence.context in {"body", "blockquote"}
            ]
            run_start = 0
            run_count = 0
            for index, sentence in enumerate(sentences):
                if self._gerund_fragment.fullmatch(sentence.text):
                    if run_count == 0:
                        run_start = index
                    run_count += 1
                    continue
                if run_count >= self._threshold:
                    first = sentences[run_start]
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=(
                                f"Gerund fragment litany: {run_count} consecutive "
                                "gerund fragments"
                            ),
                            line=first.start_line,
                            column=first.start_column,
                            severity=self.severity,
                        )
                    )
                run_count = 0
            if run_count >= self._threshold:
                first = sentences[run_start]
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=(
                            f"Gerund fragment litany: {run_count} consecutive "
                            "gerund fragments"
                        ),
                        line=first.start_line,
                        column=first.start_column,
                        severity=self.severity,
                    )
                )

        return issues


class ListicleInProseRule(Rule):
    """S012: Detect 'The first... The second... The third...' in prose."""

    id = "S012"
    name = "Listicle in Prose"
    description = "Detects ordinal-based listicle disguised as prose"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _ordinals: ClassVar[list[str]] = ["first", "second", "third", "fourth", "fifth"]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 'The first... The second... The third...' in prose."""
        issues: list[Issue] = []
        for block in iter_prose_blocks(content, filename):
            if block.context not in {"body", "blockquote"}:
                continue
            lines = block.lines
            full_text = " ".join(line for _, line in lines).lower()
            found_ordinals: list[str] = []
            for ordinal in self._ordinals:
                if re.search(rf"\bthe {ordinal}\b", full_text):
                    found_ordinals.append(ordinal)
                else:
                    break
            if len(found_ordinals) >= 3:
                for line_num, line in lines:
                    if re.search(rf"\bthe {found_ordinals[0]}\b", line, re.IGNORECASE):
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message=f"Listicle in prose: 'the {found_ordinals[0]}... the {found_ordinals[1]}... the {found_ordinals[2]}...'",
                                line=line_num,
                                column=1,
                                severity=self.severity,
                            )
                        )
                        break
                continue

            for line_num, line in lines:
                for pattern in LISTICLE_PROSE_PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match is None:
                        continue
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message="Listicle in prose pattern",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
                    break

        return issues


class HistoricalAnalogyStackingRule(Rule):
    """S013: Detect rapid-fire company/product name-drops."""

    id = "S013"
    name = "Historical Analogy Stacking"
    description = "Detects rapid-fire historical company analogies"
    severity = Severity.INFO
    config_key = "thresholds.historical_analogy_stacking"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _tech_companies: ClassVar[set[str]] = {
        "apple",
        "google",
        "microsoft",
        "amazon",
        "meta",
        "facebook",
        "netflix",
        "uber",
        "airbnb",
        "spotify",
        "stripe",
        "shopify",
        "twitter",
        "tesla",
        "openai",
        "anthropic",
        "discord",
        "slack",
        "dropbox",
        "github",
        "aws",
        "ibm",
        "oracle",
        "salesforce",
        "snapchat",
        "tiktok",
        "linkedin",
        "pinterest",
        "zoom",
    }

    def __init__(self, threshold: int = 3) -> None:
        super().__init__()
        self._threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for rule violations."""
        issues: list[Issue] = []
        lines = self.iter_lines(content, filename)

        # Check for company mentions per paragraph/nearby lines
        window: list[tuple[int, str]] = []
        for line_num, line in lines:
            words = {w.lower().rstrip(".,;:!?'\"") for w in line.split()}
            companies_in_line = words & self._tech_companies
            if companies_in_line:
                window.append((line_num, line))
            else:
                self._check_window(window, issues)
                window = []

        self._check_window(window, issues)
        return issues

    def _check_window(self, window: list[tuple[int, str]], issues: list[Issue]) -> None:
        if not window:
            return
        all_text = " ".join(line for _, line in window)
        words = {w.lower().rstrip(".,;:!?'\"") for w in all_text.split()}
        unique_companies = words & self._tech_companies
        if len(unique_companies) >= self._threshold:
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Historical analogy stacking: {len(unique_companies)} companies ({', '.join(sorted(unique_companies))})",
                    line=window[0][0],
                    column=1,
                    severity=self.severity,
                )
            )


class SignpostedConclusionRule(Rule):
    """S014: Detect 'In conclusion', 'To sum up' signposted conclusions."""

    id = "S014"
    name = "Signposted Conclusion"
    description = "Detects explicitly signposted conclusions"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 'In conclusion', 'To sum up' signposted conclusions."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            line_lower = line.casefold()
            for phrase in SIGNPOSTED_CONCLUSION_PHRASES:
                if phrase in line_lower:
                    col = line_lower.find(phrase)
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Signposted conclusion: '{phrase}'",
                            line=line_num,
                            column=col + 1,
                            end_column=col + len(phrase) + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class FractalSummaryRule(Rule):
    """S015: Detect 'In this section, we'll explore...' framing."""

    id = "S015"
    name = "Fractal Summary"
    description = "Detects section intro/outro summary framing"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 'In this section, we'll explore...' framing."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in FRACTAL_SUMMARY_PHRASES:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Fractal summary: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class ContentDuplicationRule(Rule):
    """S016: Detect repeated paragraphs within the same document."""

    id = "S016"
    name = "Content Duplication"
    description = "Detects duplicate paragraphs in the same document"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "raw"

    _MIN_WORDS = 8  # Don't flag very short paragraphs

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect repeated paragraphs within the same document."""
        issues: list[Issue] = []
        paragraphs: list[tuple[int, int, int, int, str]] = []
        current_lines: list[tuple[int, str]] = []

        def flush() -> None:
            if not current_lines:
                return
            first_line_num, first_line = current_lines[0]
            last_line_num, last_line = current_lines[-1]
            start_column = len(first_line) - len(first_line.lstrip()) + 1
            end_column = len(last_line.rstrip()) + 1
            paragraphs.append(
                (
                    first_line_num,
                    start_column,
                    last_line_num,
                    end_column,
                    " ".join(line.strip() for _, line in current_lines),
                )
            )

        for line_num, line in enumerate(content.split("\n"), start=1):
            if line.strip():
                current_lines.append((line_num, line))
            else:
                flush()
                current_lines = []
        flush()

        # Compare paragraphs by normalized word content
        seen: dict[str, int] = {}
        for line_num, column, end_line, end_column, text in paragraphs:
            words = text.lower().split()
            if len(words) < self._MIN_WORDS:
                continue
            key = " ".join(words)
            if key in seen:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Duplicate paragraph (first seen at line {seen[key]})",
                        line=line_num,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                    )
                )
            else:
                seen[key] = line_num

        return issues


# ---------- Phase 1 (Journalism Tropes): S017 ----------


class AnecdoteAsEvidenceRule(Rule):
    """S017: Detect single-anecdote generalizations."""

    id = "S017"
    name = "Anecdote As Evidence"
    description = (
        "Detects 'For [Name] of [Location]', 'Take [Name]', 'Meet [Name]' patterns"
    )
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _example_context = re.compile(
        r"\b(?:example|dateline|format|quoted sentence)\b",
        re.IGNORECASE,
    )
    _generalization = re.compile(
        r"\b(?:shows?|proves?|demonstrates?|illustrates?|every|all|broader|"
        r"nationwide|generally)\b",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect single-anecdote generalizations."""
        issues: list[Issue] = []
        sentences = iter_prose_sentences(content, filename)
        for index, sentence in enumerate(sentences):
            if self._example_context.search(sentence.text):
                continue
            window = sentence.text
            if (
                index + 1 < len(sentences)
                and sentences[index + 1].scope_id == sentence.scope_id
            ):
                window = f"{window} {sentences[index + 1].text}"
            if not self._generalization.search(window):
                continue
            for pattern in ANECDOTE_EVIDENCE_PATTERNS:
                match = re.search(pattern, sentence.text)
                if match:
                    line, column = sentence.source_position(match.start())
                    end_line, end_column = sentence.source_position(match.end())
                    assert line == end_line
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Anecdote as evidence: '{match.group()}'",
                            line=line,
                            column=column,
                            end_column=end_column,
                            severity=self.severity,
                        )
                    )
        return issues


class CitationNameDroppingRule(Rule):
    """S018: Detect consecutive 'Author (Year) verb' citation patterns."""

    id = "S018"
    name = "Citation Name-Dropping"
    description = "Detects 3+ consecutive 'Author (Year) verb' sentences"
    severity = Severity.INFO
    config_key = "thresholds.citation_name_drop"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def __init__(self, threshold: int = 3) -> None:
        super().__init__()
        self.threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect consecutive 'Author (Year) verb' citation patterns."""
        issues: list[Issue] = []
        records = iter_prose_sentences(content, filename)

        def flush(run: list[ProseSentence]) -> None:
            if len(run) < self.threshold:
                return
            first = run[0]
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=(
                        f"Citation name-dropping: {len(run)} consecutive "
                        "'Author (Year) verb' sentences"
                    ),
                    line=first.start_line,
                    column=first.start_column,
                    severity=self.severity,
                )
            )

        for _scope, group in groupby(records, key=lambda sentence: sentence.scope_id):
            run: list[ProseSentence] = []
            for sentence in group:
                if re.match(CITATION_NAME_DROP_PATTERN, sentence.text):
                    run.append(sentence)
                    continue
                flush(run)
                run = []
            flush(run)
        return issues


# ---------- Business Writing Tropes: S019-S021 ----------


class CorporateEuphemismRule(Rule):
    """S019: Detect corporate euphemisms that obscure meaning."""

    id = "S019"
    name = "Corporate Euphemism"
    description = "Detects euphemistic reframing of negative events"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _AMBIGUOUS_PHRASES: ClassVar[frozenset[str]] = frozenset(
        {"restructuring", "resource optimization", "realignment"}
    )
    _ORGANIZATIONAL_CONTEXT: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:company|corporate|departments?|employees?|headcount|jobs?|"
        r"organization(?:al)?|personnel|positions?|roles?|staff(?:ing)?|"
        r"teams?|workforce)\b"
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect corporate euphemisms that obscure meaning."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            sentence_lower = sentence.text.casefold()
            for phrase in CORPORATE_EUPHEMISM_PHRASES:
                match = re.search(re.escape(phrase), sentence.text, re.IGNORECASE)
                if match is None:
                    continue
                if (
                    phrase in self._AMBIGUOUS_PHRASES
                    and not self._ORGANIZATIONAL_CONTEXT.search(sentence_lower)
                ):
                    continue
                line_num, column = sentence.source_position(match.start())
                _, end_column = sentence.source_position(match.end())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Corporate euphemism: '{phrase}' \u2014 consider stating the action directly",
                        line=line_num,
                        column=column,
                        end_column=end_column,
                        severity=self.severity,
                    )
                )
        return issues


class AlignmentRitualRule(Rule):
    """S020: Detect alignment-signaling without substance."""

    id = "S020"
    name = "Alignment Ritual"
    description = "Detects statements that signal agreement without conveying substance"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect alignment-signaling without substance."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in ALIGNMENT_RITUAL_PHRASES:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Alignment ritual: '{match.group()}' \u2014 consider specifying what was agreed and what happens next",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class SlideDeckFragmentRule(Rule):
    """S021: Detect verbless buzzword-heavy fragments from slide-deck writing."""

    id = "S021"
    name = "Slide Deck Fragment"
    description = "Detects verbless noun-phrase fragments with stacked buzzwords"
    severity = Severity.INFO
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _MIN_BUZZWORDS = 2

    # Simple heuristic for a conjugated main verb (not gerund/participle-only)
    _FINITE_VERB: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?:i|we|you|he|she|it|they)(?:"
        r"['\u2019](?:m|re|s|ve|d|ll)\b|\s+(?![a-z-]+ing\b)[a-z-]+\b)"
        r"|\b(?:is|are|was|were|has|have|had|do|does|did|will|shall|can|could"
        r"|would|should|may|might|must)\b",
        re.IGNORECASE,
    )
    _RELATIVE_CLAUSE: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:that|which|who)\b", re.IGNORECASE
    )
    _GERUND_LED: ClassVar[re.Pattern[str]] = re.compile(r"^[a-z-]+ing\b", re.IGNORECASE)

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect verbless buzzword-heavy fragments from slide-deck writing."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            stripped = line.strip()
            start = len(line) - len(line.lstrip())
            end = len(line.rstrip())
            # Skip very short or very long lines
            if len(stripped.split()) < 4 or len(stripped.split()) > 20:
                continue
            # Must end with a period (sentence-like fragment)
            if not stripped.endswith("."):
                continue
            # Skip if it has a conjugated main verb
            words_lower = {w.lower().rstrip(".,;:!?'\"") for w in stripped.split()}
            main_clause = stripped
            relative_clause = self._RELATIVE_CLAUSE.search(stripped)
            if relative_clause is not None and relative_clause.start() > 0:
                prefix = stripped[: relative_clause.start()].rstrip()
                prefix_words = {
                    word.casefold().strip(".,;:!?'\"") for word in prefix.split()
                }
                fragment_prefix = (
                    self._GERUND_LED.match(prefix)
                    or len(prefix_words & SLIDE_DECK_BUZZWORDS) >= self._MIN_BUZZWORDS
                )
                final_word = (
                    stripped.rsplit(maxsplit=1)[-1].casefold().strip(".,;:!?'\"")
                )
                if fragment_prefix and final_word in SLIDE_DECK_BUZZWORDS:
                    main_clause = prefix
            if self._FINITE_VERB.search(main_clause):
                continue
            # Count buzzwords
            buzzword_count = len(words_lower & SLIDE_DECK_BUZZWORDS)
            if buzzword_count >= self._MIN_BUZZWORDS:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Slide deck fragment: '{stripped}' \u2014 consider adding a subject and verb",
                        line=line_num,
                        column=start + 1,
                        end_column=end + 1,
                        severity=self.severity,
                        confidence=self.default_confidence,
                    )
                )
        return issues


class HeadingWithoutBodyRule(Rule):
    """S025: Detect headings without content before a peer or ancestor."""

    id = "S025"
    name = "Heading Without Body"
    description = "Detects headings without body content"
    severity = Severity.WARNING
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "raw"

    _BLOCKQUOTE_PREFIX = re.compile(r"^(?:\s{0,3}>\s?)+")
    _ATX_HEADING = re.compile(r"^ {0,3}#{1,6}\s+")
    _SETEXT_UNDERLINE = re.compile(r"^ {0,3}(?:=+|-+)\s*$")

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for headings with no body before a peer or ancestor."""
        if not is_markdown_file(filename):
            return []

        lines = content.split("\n")
        headings = _get_cached_parser(content).get_headings()
        issues: list[Issue] = []

        for current, following in pairwise(headings):
            if following.level > current.level:
                continue

            body_start = current.start_line
            heading_line = self._BLOCKQUOTE_PREFIX.sub(
                "", lines[current.start_line - 1]
            )
            if not self._ATX_HEADING.match(heading_line) and body_start < len(lines):
                underline = self._BLOCKQUOTE_PREFIX.sub("", lines[body_start])
                if self._SETEXT_UNDERLINE.fullmatch(underline):
                    body_start += 1

            body_end = following.start_line - 1
            if any(
                self._BLOCKQUOTE_PREFIX.sub("", line).strip()
                for line in lines[body_start:body_end]
            ):
                continue

            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Heading without body: '{current.title}'",
                    line=current.start_line,
                    column=current.column,
                    end_column=current.end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Add content under this heading or remove it",
                )
            )

        return issues
