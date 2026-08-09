"""Vocabulary detection rules (V001-V011 and V013-V017)."""

import re
from typing import ClassVar

from proseprobe.data.phrases import (
    COLLABORATIVE_PHRASES,
    GRANDIOSE_STAKES_PHRASES,
    INFLAMMATORY_CLICHE_PHRASES,
    KNOWLEDGE_CUTOFF_PATTERNS,
    NEEDLESS_INTENSIFIER_REPLACEMENTS,
    PROMOTIONAL_PHRASES,
    REDUNDANT_MODIFIER_REPLACEMENTS,
    REDUNDANT_PAIR_REPLACEMENTS,
    TREND_OVERCLAIM_PHRASES,
    VERBOSE_VERB_PHRASE_REPLACEMENTS,
    WEASEL_PHRASES,
    WORDY_PHRASE_REPLACEMENTS,
)
from proseprobe.data.vocabulary import (
    AI_VOCABULARY,
    AI_VOCABULARY_TIER1,
    AI_VOCABULARY_TIER2,
    AI_VOCABULARY_TIER3,
    VOCABULARY_SUGGESTIONS,
)
from proseprobe.parsers.markdown import is_example_line
from proseprobe.parsers.prose import (
    ProseSentence,
    iter_prose_blocks,
    iter_prose_sentences,
)
from proseprobe.rules.base import Confidence, Issue, Rule, Severity

_MONTH = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\b",
    re.IGNORECASE,
)
_NAMED_SOURCE = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b")
_NUMBER = re.compile(r"\b\d+(?:\.\d+)?%?\b")
_LINK = re.compile(r"https?://|\[[^\]]+\]\([^)]+\)")
_QUANTITY_EVIDENCE = re.compile(
    r"\b(?:benchmark|measurement|report|study|survey)s?\b", re.IGNORECASE
)
_TESTED_BOUND = re.compile(
    r"(?:\b(?:across|during|for|in|over)\s+\d[\d,]*(?:\.\d+)?\s+"
    r"(?:tests?|trials?|test runs?|runs?|requests?|operations?|cases?|hours?|days?)\b"
    r"|\bunder\s+(?:our|the|these|this)\s+tested\s+"
    r"(?:conditions?|configuration|environment|setup)\b"
    r"|\b(?:benchmarked|measured|observed|tested)\b[^.!?\n]{0,80}"
    r"\b\d[\d,]*(?:\.\d+)?\s+"
    r"(?:tests?|trials?|test runs?|runs?|requests?|operations?|cases?|hours?|days?)\b)",
    re.IGNORECASE,
)


def _sentence_window_source(
    content: str,
    sentences: list[ProseSentence],
    index: int,
) -> str:
    """Return the adjacent same-scope sentence window as original source."""
    sentence = sentences[index]
    window = [
        candidate
        for candidate in sentences[max(0, index - 1) : index + 2]
        if candidate.scope_id == sentence.scope_id
    ]
    return " ".join(candidate.source_text(content) for candidate in window)


def _has_sentence_evidence(
    content: str,
    sentences: list[ProseSentence],
    index: int,
) -> bool:
    source = _sentence_window_source(content, sentences, index)
    numbers = _NUMBER.findall(source)
    return bool(
        _LINK.search(source)
        or _MONTH.search(source)
        or _NAMED_SOURCE.search(source)
        or "%" in source
        or len(numbers) >= 2
    )


def _has_tested_bound(
    content: str,
    sentences: list[ProseSentence],
    index: int,
) -> bool:
    """Return whether the local source states a concrete tested scope."""
    return bool(
        _TESTED_BOUND.search(_sentence_window_source(content, sentences, index))
    )


def _has_quantity_evidence(
    content: str,
    sentences: list[ProseSentence],
    index: int,
) -> bool:
    """Return whether the local source supplies quantitative context."""
    source = _sentence_window_source(content, sentences, index)
    return bool(
        _NUMBER.search(source)
        or _LINK.search(source)
        or _MONTH.search(source)
        or _NAMED_SOURCE.search(source)
        or _QUANTITY_EVIDENCE.search(source)
    )


def _replacement_phrase_issues(
    rule: Rule,
    content: str,
    filename: str,
    replacements: dict[str, str],
) -> list[Issue]:
    """Return exact prose findings for a fixed replacement table."""
    issues: list[Issue] = []
    for block in iter_prose_blocks(content, filename):
        if block.context == "heading":
            continue
        for line_num, line in block.lines:
            for phrase, replacement in replacements.items():
                for match in re.finditer(
                    rf"\b{re.escape(phrase)}\b", line, re.IGNORECASE
                ):
                    issues.append(
                        Issue(
                            rule_id=rule.id,
                            message=f"{rule.name.capitalize()}: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=rule.severity,
                            confidence=rule.default_confidence,
                            suggestion=replacement,
                        )
                    )

    return sorted(issues, key=lambda issue: (issue.line, issue.column))


class AIVocabularyRule(Rule):
    """V001: Detect overused and clichéd vocabulary."""

    id = "V001"
    name = "Overused Vocabulary"
    description = "Detects overused and clichéd words"
    severity = Severity.WARNING

    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    # Patterns for words that need suffix matching (verbs, etc.)
    _WORD_PATTERNS: ClassVar[dict[str, str]] = {
        "delve": r"delv(?:e|es|ed|ing)",
        "embark": r"embark(?:s|ed|ing)?",
        "foster": r"foster(?:s|ed|ing)?",
        "garner": r"garner(?:s|ed|ing)?",
        "harness": r"harness(?:es|ed|ing)?",
        "leverage": r"leverag(?:e|es|ed)",
        "navigate": r"navigat(?:e|es|ed|ing)",
        "showcase": r"showcas(?:e|es|ed|ing)",
        "spearhead": r"spearhead(?:s|ed|ing)?",
        "streamline": r"streamlin(?:e|es|ed|ing)",
        "underscore": r"underscor(?:e|es|ed|ing)",
        "unravel": r"unravel(?:s|ed|ing)?",
        # Academic jargon (academic tropes)
        "problematize": r"problemati[zs](?:e|es|ed|ing)",
        "destabilize": r"destabili[zs](?:e|es|ed|ing)",
        "foreground": r"foreground(?:s|ed|ing)?",
        "situate": r"situate[sd]?|situating",
        "operationalize": r"operationali[zs](?:e|es|ed|ing)",
        "instantiate": r"instantiat(?:e|es|ed|ing)",
        "reconceptualize": r"reconceptuali[zs](?:e|es|ed|ing)",
        "facilitate": r"facilitat(?:e|es|ed|ing)",
        "demonstrate": r"demonstrat(?:e|es|ed|ing)",
        "implement": r"implement(?:s|ed|ing)?",
        # Narrow: only academic usage ("interrogate the assumptions"), not police/legal
        "interrogate": r"interrogat(?:e|es|ed|ing)\s+(?:the\s+)?(?:dominant|underlying|prevailing|assumed|notion|concept|assumption|premise|idea)s?",
        # Business jargon (business writing tropes)
        "incentivize": r"incentivi[zs](?:e|es|ed|ing)",
        "ideate": r"ideat(?:e|es|ed|ing)",
        "socialize": r"sociali[zs](?:e|es|ed|ing)\s+(?:the\s+)?(?:plan|idea|proposal|concept|strategy|approach|document|initiative|change|update|roadmap)",
        "best-in-class": r"best[- ]in[- ]class",
        "architect": r"architect(?:s|ed|ing)\s+(?:a|an|the|our|this|that|new|scalable|robust|modern|flexible)\s+\w+",
    }

    def __init__(
        self,
        allowed: set[str] | None = None,
        additional: set[str] | None = None,
        allowed_phrases: set[str] | None = None,
    ) -> None:
        super().__init__()
        self._allowed = {w.lower() for w in (allowed or set())}
        self._additional = {w.lower() for w in (additional or set())} - self._allowed
        self._vocabulary = AI_VOCABULARY | self._additional
        self._allowed_phrases = {p.lower() for p in (allowed_phrases or set())}

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for overused vocabulary words."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            line_lower = line.lower()

            # Skip entire line if it contains an allowed phrase
            if any(phrase in line_lower for phrase in self._allowed_phrases):
                continue

            for word in sorted(self._vocabulary):
                if word in self._allowed:
                    continue
                # Use custom pattern if available, otherwise exact match
                if word in self._WORD_PATTERNS:
                    pattern = rf"\b{self._WORD_PATTERNS[word]}\b"
                else:
                    pattern = rf"\b{re.escape(word)}\b"

                for match in re.finditer(pattern, line_lower):
                    suggestion = VOCABULARY_SUGGESTIONS.get(word)
                    matched_word = match.group()
                    message = f"Overused word: '{matched_word}'"
                    if suggestion:
                        message += f" → consider '{suggestion}'"

                    confidence = self._word_confidence(word)
                    if is_example_line(content, filename, line_num):
                        confidence = Confidence.LOW

                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=message,
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                            confidence=confidence,
                            suggestion=suggestion,
                        )
                    )

        return issues

    @staticmethod
    def _word_confidence(word: str) -> Confidence:
        """Return confidence level based on vocabulary tier."""
        if word in AI_VOCABULARY_TIER1:
            return Confidence.HIGH
        if word in AI_VOCABULARY_TIER2:
            return Confidence.MEDIUM
        if word in AI_VOCABULARY_TIER3:
            return Confidence.LOW
        # Additional user-supplied words default to MEDIUM
        return Confidence.MEDIUM


class CollaborativePhrasesRule(Rule):
    """V002: Detect collaborative/chat-like phrases."""

    id = "V002"
    name = "Collaborative Phrases"
    description = "Detects chat-like communication patterns"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for collaborative phrases."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
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
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for knowledge cutoff patterns."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
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
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for promotional language."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
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
            for phrase in INFLAMMATORY_CLICHE_PHRASES:
                if phrase.lower() in line_lower:
                    col = line_lower.find(phrase.lower())
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Inflammatory cliché: '{phrase}'",
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
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for weasel words."""
        issues: list[Issue] = []
        sentences = iter_prose_sentences(content, filename)
        for index, sentence in enumerate(sentences):
            for pattern in WEASEL_PHRASES:
                match = re.search(pattern, sentence.text, re.IGNORECASE)
                if match:
                    line, column = sentence.source_position(match.start())
                    end_line, end_column = sentence.source_position(match.end())
                    assert line == end_line
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Weasel phrase: '{match.group()}'",
                            line=line,
                            column=column,
                            end_column=end_column,
                            severity=self.severity,
                            confidence=(
                                Confidence.LOW
                                if _has_sentence_evidence(content, sentences, index)
                                else self.default_confidence
                            ),
                        )
                    )

        return issues


# ---------- Phase 10: V006-V007 ----------


class GrandioseStakesRule(Rule):
    """V006: Detect inflated importance claims."""

    id = "V006"
    name = "Grandiose Stakes"
    description = (
        "Detects inflated stakes ('fundamentally reshape', 'define the next era')"
    )
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect inflated importance claims."""
        """Check content for detect inflated importance claims."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in GRANDIOSE_STAKES_PHRASES:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Grandiose stakes: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class InventedConceptLabelsRule(Rule):
    """V007: Detect compound analytical labels used as established terms."""

    id = "V007"
    name = "Invented Concept Labels"
    description = "Detects '[noun] paradox/trap/creep' pseudo-analytical labels"
    severity = Severity.INFO
    config_key = "thresholds.invented_concept_labels"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _suffixes: ClassVar[list[str]] = [
        "paradox",
        "trap",
        "creep",
        "divide",
        "vacuum",
        "inversion",
        "deficit",
        "gap",
        "spiral",
        "dilemma",
    ]
    _LITERAL_REFERENCE_HEADS: ClassVar[frozenset[str]] = frozenset(
        {
            "a",
            "an",
            "another",
            "any",
            "each",
            "either",
            "every",
            "her",
            "his",
            "its",
            "my",
            "neither",
            "no",
            "one",
            "other",
            "our",
            "some",
            "that",
            "the",
            "their",
            "these",
            "this",
            "those",
            "what",
            "which",
            "whose",
            "your",
        }
    )
    _LITERAL_REFERENCE_SUFFIXES: ClassVar[frozenset[str]] = frozenset(
        {"gap", "dilemma"}
    )

    def __init__(self, threshold: int = 2) -> None:
        super().__init__()
        self._threshold = threshold
        suffix_group = "|".join(self._suffixes)
        self._pattern = re.compile(rf"\b(\w+)\s+({suffix_group})\b", re.IGNORECASE)

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for rule violations."""
        issues: list[Issue] = []
        matches: list[tuple[int, int, int, str]] = []

        for line_num, line in self.iter_lines(content, filename):
            for match in self._pattern.finditer(line):
                head = match.group(1).casefold()
                if (
                    head == "s"
                    and match.start(1) > 0
                    and line[match.start(1) - 1] in {"'", "\u2019"}
                ):
                    continue
                suffix = match.group(2).casefold()
                if (
                    head in self._LITERAL_REFERENCE_HEADS
                    and suffix in self._LITERAL_REFERENCE_SUFFIXES
                ):
                    continue
                matches.append(
                    (line_num, match.start() + 1, match.end() + 1, match.group())
                )

        if len(matches) >= self._threshold:
            for line_num, col, end_col, text in matches:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Invented concept label: '{text}'",
                        line=line_num,
                        column=col,
                        end_column=end_col,
                        severity=self.severity,
                    )
                )

        return issues


# ---------- Phase 1 (Journalism Tropes): V008 ----------


class TrendOverclaimRule(Rule):
    """V008: Detect unsubstantiated trend claims."""

    id = "V008"
    name = "Trend Overclaim"
    description = "Detects 'more and more people', 'a growing number of' trend claims"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect unsubstantiated trend claims."""
        issues: list[Issue] = []
        sentences = iter_prose_sentences(content, filename)
        for index, sentence in enumerate(sentences):
            for pattern in TREND_OVERCLAIM_PHRASES:
                match = re.search(pattern, sentence.text, re.IGNORECASE)
                if match:
                    line, column = sentence.source_position(match.start())
                    end_line, end_column = sentence.source_position(match.end())
                    assert line == end_line
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Trend overclaim: '{match.group()}'",
                            line=line,
                            column=column,
                            end_column=end_column,
                            severity=self.severity,
                            confidence=(
                                Confidence.LOW
                                if _has_sentence_evidence(content, sentences, index)
                                else self.default_confidence
                            ),
                        )
                    )
        return issues


class WordyPhraseRule(Rule):
    """V009: Detect wordy phrases with direct replacements."""

    id = "V009"
    name = "Wordy Phrase"
    description = "Detects wordy phrases with concise replacements"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose for wordy phrases."""
        return _replacement_phrase_issues(
            self, content, filename, WORDY_PHRASE_REPLACEMENTS
        )


class RedundantPairRule(Rule):
    """V010: Detect fixed redundant word pairs."""

    id = "V010"
    name = "Redundant Pair"
    description = "Detects fixed phrases containing redundant words"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose for fixed redundant pairs."""
        return _replacement_phrase_issues(
            self, content, filename, REDUNDANT_PAIR_REPLACEMENTS
        )


class VerboseVerbPhraseRule(Rule):
    """V011: Detect verbose verb phrases with direct replacements."""

    id = "V011"
    name = "Verbose Verb Phrase"
    description = "Detects verbose verb phrases with direct replacements"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _DECISION_REPLACEMENTS: ClassVar[frozenset[str]] = frozenset(
        {"decide", "decided", "decides", "deciding"}
    )
    _DECISION_COMPOUND: ClassVar[re.Pattern[str]] = re.compile(
        r"\s+(?:boundary|matrix|model|rule|table|tree)\b", re.IGNORECASE
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose for verbose verb phrases."""
        issues = _replacement_phrase_issues(
            self, content, filename, VERBOSE_VERB_PHRASE_REPLACEMENTS
        )
        lines = content.split("\n")
        return [
            issue
            for issue in issues
            if issue.suggestion not in self._DECISION_REPLACEMENTS
            or not self._DECISION_COMPOUND.match(
                lines[issue.line - 1][(issue.end_column or 1) - 1 :]
            )
        ]


class RedundantModifierRule(Rule):
    """V013: Detect strongly redundant modifier combinations."""

    id = "V013"
    name = "Redundant Modifier"
    description = "Detects modifiers redundant with the words they modify"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose for redundant modifier combinations."""
        return _replacement_phrase_issues(
            self, content, filename, REDUNDANT_MODIFIER_REPLACEMENTS
        )


class ImpreciseQuantityRule(Rule):
    """V014: Detect narrow vague-quantity phrases without local evidence."""

    id = "V014"
    name = "Imprecise Quantity"
    description = "Detects vague quantity phrases lacking measured context"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _QUANTITY: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:a\s+(?:considerable|large|small)\s+number\s+of"
        r"|a\s+handful\s+of)\b",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose for imprecise quantity phrases."""
        issues: list[Issue] = []
        sentences = iter_prose_sentences(content, filename)
        for index, sentence in enumerate(sentences):
            if sentence.context == "heading" or is_example_line(
                content, filename, sentence.start_line
            ):
                continue

            confidence = (
                Confidence.LOW
                if _has_quantity_evidence(content, sentences, index)
                else self.default_confidence
            )
            for match in self._QUANTITY.finditer(sentence.text):
                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(match.end())
                quantity = " ".join(match.group().split())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Imprecise quantity: '{quantity}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=confidence,
                        suggestion="Use a measured quantity or cite the source",
                    )
                )

        return issues


class UnboundedSuperlativeRule(Rule):
    """V015: Detect narrow superlative claims without a comparison set."""

    id = "V015"
    name = "Unbounded Superlative"
    description = "Detects curated superlative claims lacking local comparison"
    severity = Severity.INFO
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _CLAIM: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:is|are|was|were|remains?)\s+"
        r"(?P<claim>(?:the\s+)?(?:best(?![- ]in[- ]class\b)|worst|fastest|"
        r"slowest|largest|smallest|highest|lowest|"
        r"(?:most|least)\s+(?:accurate|efficient|reliable|scalable|secure)))\b",
        re.IGNORECASE,
    )
    _COMPARISON_SET: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:among|between|compared\s+(?:to|with)|out\s+of|within)\b"
        r"|\bof\s+(?:all|our|the|these|those|\d+|one|two|three|four|five|"
        r"six|seven|eight|nine|ten)\b"
        r"|\bin\s+(?:our|the|this)\s+"
        r"(?:benchmark|comparison|evaluation|test)s?\b",
        re.IGNORECASE,
    )
    _LITERAL_CONTEXT: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:avoid|do not|don't)\s+"
        r"(?:claim(?:ing)?|say(?:ing)?|writ(?:e|ing))\b"
        r"|\bthe (?:label|phrase|wording)\b",
        re.IGNORECASE,
    )
    _HYPOTHETICAL: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:if|whether)\b", re.IGNORECASE
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose for curated superlatives without a local comparison."""
        issues: list[Issue] = []
        sentences = iter_prose_sentences(content, filename)
        for index, sentence in enumerate(sentences):
            window = _sentence_window_source(content, sentences, index)
            if (
                sentence.context == "heading"
                or is_example_line(content, filename, sentence.start_line)
                or sentence.text.rstrip().endswith("?")
                or self._LITERAL_CONTEXT.search(sentence.text)
                or self._COMPARISON_SET.search(window)
                or _has_quantity_evidence(content, sentences, index)
            ):
                continue

            for match in self._CLAIM.finditer(sentence.text):
                if self._HYPOTHETICAL.search(sentence.text[: match.start()]):
                    continue
                claim_match = match.span("claim")
                line, column = sentence.source_position(claim_match[0])
                end_line, end_column = sentence.source_position(claim_match[1])
                claim = " ".join(match.group("claim").split())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Unbounded superlative: '{claim}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion="Name the comparison set and supporting evidence",
                    )
                )

        return issues


class AbsoluteReliabilityClaimRule(Rule):
    """V016: Detect narrow absolute reliability claims without tested bounds."""

    id = "V016"
    name = "Absolute Reliability Claim"
    description = "Detects absolute reliability and security claims"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _CLAIM: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:never\s+fails|always\s+succeeds|eliminates\s+all\s+errors)\b"
        r"|(?<!\w)100%\s+secure\b",
        re.IGNORECASE,
    )
    _LITERAL_CONTEXT: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:avoid|do not|don't)\s+"
        r"(?:claim(?:ing)?|say(?:ing)?|writ(?:e|ing))\b"
        r"|\bthe (?:phrase|wording)\b",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose for unbounded absolute reliability claims."""
        issues: list[Issue] = []
        sentences = iter_prose_sentences(content, filename)
        for index, sentence in enumerate(sentences):
            if (
                is_example_line(content, filename, sentence.start_line)
                or self._LITERAL_CONTEXT.search(sentence.text)
                or _has_tested_bound(content, sentences, index)
            ):
                continue

            for match in self._CLAIM.finditer(sentence.text):
                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(match.end())
                claim = " ".join(match.group().split())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Absolute reliability claim: '{claim}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion="State the tested scope and observed result",
                    )
                )

        return issues


class NeedlessIntensifierRule(Rule):
    """V017: Detect a narrow set of debatable intensifier combinations."""

    id = "V017"
    name = "Needless Intensifier"
    description = "Detects curated intensifier combinations with direct edits"
    severity = Severity.INFO
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose for curated needless intensifiers."""
        return _replacement_phrase_issues(
            self, content, filename, NEEDLESS_INTENSIFIER_REPLACEMENTS
        )
