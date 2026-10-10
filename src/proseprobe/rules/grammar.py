"""Grammar rules (G001-G017, G019, G022, G024-G025, G029, G031, G037-G038)."""

import re
from itertools import pairwise
from typing import ClassVar

from proseprobe.data.patterns import (
    COPULA_AVOIDANCE_PATTERNS,
    HEDGING_PATTERNS,
    NOMINALIZATION_PATTERNS,
    PASSIVE_VOICE_PATTERNS,
)
from proseprobe.data.phrases import (
    ASSERTED_SIMPLICITY_PHRASES,
    DOUBLE_NEGATIVE_REPLACEMENTS,
    FALSE_BALANCE_PHRASES,
    FALSE_SUSPENSE_PHRASES,
    FALSE_VULNERABILITY_PHRASES,
    FUTURIST_INVITATION_PHRASES,
    GAP_RITUAL_PHRASES,
    IMPERSONAL_CORPORATE_PASSIVE_PHRASES,
    PATRONIZING_ANALOGY_PHRASES,
    PEDAGOGICAL_VOICE_PHRASES,
)
from proseprobe.parsers.markdown import is_example_line, is_markdown_file
from proseprobe.parsers.prose import (
    ProseSentence,
    iter_prose_scopes,
    iter_prose_sentences,
)
from proseprobe.rules._phrases import (
    _FINITE_CLAUSE,
    _claim_scope,
    iter_prose_regex_matches,
    longest_literal_phrase_issues,
    original_prose_slice,
)
from proseprobe.rules.base import Confidence, Issue, Rule, Severity


class CopulaAvoidanceRule(Rule):
    """G001: Detect copula avoidance."""

    id = "G001"
    name = "Copula Avoidance"
    description = "Detects 'serves as' instead of 'is'"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for copula avoidance."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            source = sentence.source_text(content)
            for pattern in COPULA_AVOIDANCE_PATTERNS:
                for match in iter_prose_regex_matches(
                    sentence, source, filename, re.compile(pattern, re.IGNORECASE)
                ):
                    line, column = sentence.source_position(match.start())
                    end_line, end_column = sentence.source_position(match.end())
                    phrase = " ".join(match.group().split())
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Copula avoidance: '{phrase}' → consider 'is'",
                            line=line,
                            column=column,
                            end_line=end_line if end_line != line else None,
                            end_column=end_column,
                            severity=self.severity,
                        )
                    )

        return issues


class ExcessiveHedgingRule(Rule):
    """G002: Detect excessive hedging."""

    id = "G002"
    name = "Excessive Hedging"
    description = "Detects metadiscourse, redundant modals, and hedge stacking"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    # Individual hedge words for per-sentence stacking detection
    _HEDGE_WORDS = re.compile(
        r"\b(?:may|might|potentially|arguably|possibly|perhaps)\b"
        r"|(?:appears?\s+to|suggests?\s+that|could\s+be(?:\s+interpreted\s+as)?)",
        re.IGNORECASE,
    )
    _REDUNDANT_MODAL = re.compile(
        r"\b(?P<modal>may|might|could)\s+(?:possibly|potentially|perhaps)\b",
        re.IGNORECASE,
    )
    _QUALIFIED_SUBJECT = (
        r"(?:(?:the|a|an|this|that|these|those|our|your|their|its)\s+"
        r"[\w'-]+(?:\s+[\w'-]+){0,3}|it|they|we|you|he|she)\s+"
        r"(?:may|might|could|appears?\s+to|suggests?\s+that)\b"
    )
    _CLAUSE_BOUNDARY = re.compile(
        r";\s*|(?:,\s*(?:(?:and|or|but|while|whereas|although)\s+)?"
        r"|\s+(?:and|or|but|while|whereas|although)\s+)"
        rf"(?={_QUALIFIED_SUBJECT})",
        re.IGNORECASE,
    )

    @staticmethod
    def _remove_prose_prefixes(source: str, filename: str, context: str) -> str:
        if filename.lower().endswith(".py"):
            return re.sub(r"(?m)^[ \t]*#[ \t]?", "", source)
        if context == "blockquote":
            return re.sub(r"(?m)^(?: {0,3}>[ \t]?)+", "", source)
        return source

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for excessive hedging."""
        issues: list[Issue] = []
        sentences = iter_prose_sentences(content, filename)
        for sentence in sentences:
            source = sentence.source_text(content)
            for pattern in HEDGING_PATTERNS:
                for match in iter_prose_regex_matches(
                    sentence, source, filename, re.compile(pattern, re.IGNORECASE)
                ):
                    line, column = sentence.source_position(match.start())
                    end_line, end_column = sentence.source_position(match.end())
                    phrase = " ".join(match.group().split())
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Hedging phrase: '{phrase}'",
                            line=line,
                            column=column,
                            end_line=end_line if end_line != line else None,
                            end_column=end_column,
                            severity=self.severity,
                        )
                    )

        redundant_issues: list[Issue] = []
        redundant_ranges: list[tuple[tuple[int, int], tuple[int, int]]] = []
        stacking_issues: list[Issue] = []
        for sentence in sentences:
            source = sentence.source_text(content)
            redundant_matches = [
                match
                for match in self._REDUNDANT_MODAL.finditer(sentence.text)
                if self._REDUNDANT_MODAL.fullmatch(
                    self._remove_prose_prefixes(
                        source[match.start() : match.end()], filename, sentence.context
                    )
                )
            ]
            for match in redundant_matches:
                start = sentence.source_position(match.start())
                end = sentence.source_position(match.end())
                redundant_ranges.append((start, end))
                phrase = " ".join(match.group().split())
                redundant_issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Redundant modal hedge: '{phrase}'",
                        line=start[0],
                        column=start[1],
                        end_line=end[0],
                        end_column=end[1],
                        severity=self.severity,
                        confidence=Confidence.HIGH,
                        suggestion=match.group("modal").casefold(),
                    )
                )
            hedge_matches = [
                match
                for match in iter_prose_regex_matches(
                    sentence, source, filename, self._HEDGE_WORDS
                )
                if not any(
                    redundant.start() <= match.start()
                    and match.end() <= redundant.end()
                    for redundant in redundant_matches
                )
            ]
            boundaries = [
                0,
                *(
                    match.end()
                    for match in self._CLAUSE_BOUNDARY.finditer(sentence.text)
                ),
                len(sentence.text),
            ]
            for clause_start, clause_end in pairwise(boundaries):
                clause_matches = [
                    match
                    for match in hedge_matches
                    if clause_start <= match.start() and match.end() <= clause_end
                ]
                if len(clause_matches) < 2:
                    continue
                adjacent = any(
                    not self._remove_prose_prefixes(
                        source[first.end() : second.start()], filename, sentence.context
                    ).strip()
                    for first, second in pairwise(clause_matches)
                )
                while (
                    clause_start < clause_end and sentence.text[clause_start].isspace()
                ):
                    clause_start += 1
                clause_line, clause_column = sentence.source_position(clause_start)
                stacking_issues.append(
                    Issue(
                        rule_id=self.id,
                        message=(
                            f"Hedge stacking: {len(clause_matches)} hedges in one clause"
                        ),
                        line=clause_line,
                        column=clause_column,
                        severity=self.severity,
                        confidence=Confidence.HIGH if adjacent else Confidence.MEDIUM,
                    )
                )

        issues.extend(stacking_issues)
        issues = [
            issue
            for issue in issues
            if not any(
                start <= (issue.line, issue.column)
                and (
                    issue.end_line or issue.line,
                    issue.end_column or issue.column,
                )
                <= end
                for start, end in redundant_ranges
            )
        ]
        issues.extend(redundant_issues)
        return sorted(
            {(issue.line, issue.column): issue for issue in issues}.values(),
            key=lambda issue: (issue.line, issue.column),
        )


class ParticipleChainsRule(Rule):
    """G003: Detect dangling participle chains."""

    id = "G003"
    name = "Participle Chains"
    description = "Detects 'highlighting..., emphasizing..., fostering...' chains"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _pattern = re.compile(
        r"(?:^|,\s*)"
        r"(?P<first>(?<!-)\b[a-z]+ing\b)"
        r"[^.!?]*?(?:,\s*|\s+(?:and|while)\s+)"
        r"(?P<second>(?<!-)\b[a-z]+ing\b)(?=\s+[a-z])"
        r"(?:[^.!?]*?(?:,\s*|\s+(?:and|while)\s+)"
        r"(?P<third>(?<!-)\b[a-z]+ing\b)(?=\s+[a-z]))?",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for participle chains."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            match = self._pattern.search(line)
            if match:
                words = [match.group("first"), match.group("second")]
                if third := match.group("third"):
                    words.append(third)
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Participle chain: '{', '.join(words)}'",
                        line=line_num,
                        column=match.start("first") + 1,
                        end_column=match.end() + 1,
                        severity=self.severity,
                    )
                )

        return issues


# ---------- Phase 10: G004-G009 ----------


class FalseSuspenseTransitionRule(Rule):
    """G004: Detect 'here's the kicker' false suspense transitions."""

    id = "G004"
    name = "False Suspense Transition"
    description = "Detects 'here's the kicker/thing' false suspense"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for false-suspense transitions."""
        return longest_literal_phrase_issues(
            self, content, filename, FALSE_SUSPENSE_PHRASES, "False suspense"
        )


class PatronizingAnalogyRule(Rule):
    """G005: Detect 'Think of it as...' patronizing analogies."""

    id = "G005"
    name = "Patronizing Analogy"
    description = "Detects 'think of it as/like' patronizing analogies"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for patronizing analogies."""
        return longest_literal_phrase_issues(
            self, content, filename, PATRONIZING_ANALOGY_PHRASES, "Patronizing analogy"
        )


class FuturistInvitationRule(Rule):
    """G006: Detect 'Imagine a world where...' futurist invitations."""

    id = "G006"
    name = "Futurist Invitation"
    description = "Detects 'imagine a world where' futurist framing"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for futurist invitations."""
        return longest_literal_phrase_issues(
            self, content, filename, FUTURIST_INVITATION_PHRASES, "Futurist invitation"
        )


class FalseVulnerabilityRule(Rule):
    """G007: Detect 'I'll be honest' false vulnerability."""

    id = "G007"
    name = "False Vulnerability"
    description = "Detects performative self-awareness phrases"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for performative vulnerability."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in FALSE_VULNERABILITY_PHRASES:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"False vulnerability: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class AssertedSimplicityRule(Rule):
    """G008: Detect 'The reality is simpler' asserted simplicity."""

    id = "G008"
    name = "Asserted Simplicity"
    description = "Detects 'the truth is/reality is simpler' assertions"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for asserted simplicity."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in ASSERTED_SIMPLICITY_PHRASES:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Asserted simplicity: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class PedagogicalVoiceRule(Rule):
    """G009: Detect 'Let's break this down' pedagogical voice."""

    id = "G009"
    name = "Pedagogical Voice"
    description = "Detects 'let's break this down/unpack/explore' teaching tone"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for pedagogical voice."""
        return longest_literal_phrase_issues(
            self, content, filename, PEDAGOGICAL_VOICE_PHRASES, "Pedagogical voice"
        )


# ---------- Phase 1 (Journalism Tropes): G010 ----------


class FalseBalanceRule(Rule):
    """G010: Detect false-balance framing."""

    id = "G010"
    name = "False Balance"
    description = "Detects 'supporters say X, critics say Y' false balance"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for false-balance framing."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in FALSE_BALANCE_PHRASES:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"False balance: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class NominalizationOverloadRule(Rule):
    """G011: Detect overuse of nominalization constructions."""

    id = "G011"
    name = "Nominalization Overload"
    description = "Detects 'the [noun] of' nominalization patterns"
    severity = Severity.INFO
    config_key = "thresholds.nominalization_overload"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def __init__(self, threshold: int = 3) -> None:
        super().__init__()
        self.threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for overused nominalization constructions."""
        issues: list[Issue] = []
        for block in iter_prose_scopes(content, filename):
            matches: list[tuple[int, re.Match[str]]] = []
            for line_num, line in block.lines:
                for pattern in NOMINALIZATION_PATTERNS:
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        matches.append((line_num, match))
            if len(matches) >= self.threshold:
                for line_num, match in matches:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Nominalization: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class PassiveVoiceOveruseRule(Rule):
    """G012: Detect overuse of formulaic academic passive voice."""

    id = "G012"
    name = "Passive Voice Overuse"
    description = "Detects formulaic academic passive constructions"
    severity = Severity.INFO
    config_key = "thresholds.passive_voice_overuse"
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def __init__(self, threshold: int = 5) -> None:
        super().__init__()
        self.threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for overused formulaic academic passives."""
        issues: list[Issue] = []
        for block in iter_prose_scopes(content, filename):
            matches: list[tuple[int, re.Match[str]]] = []
            for line_num, line in block.lines:
                for pattern in PASSIVE_VOICE_PATTERNS:
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        matches.append((line_num, match))
            if len(matches) >= self.threshold:
                for line_num, match in matches:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Academic passive: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class GapRitualRule(Rule):
    """G013: Detect 'gap in the literature' ritual phrases."""

    id = "G013"
    name = "Gap Ritual"
    description = "Detects formulaic 'gap in the literature' phrases"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for gap-ritual phrases."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in GAP_RITUAL_PHRASES:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Gap ritual phrase: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


# ---------- Business Writing Tropes: G014 ----------


class ImpersonalCorporatePassiveRule(Rule):
    """G014: Detect impersonal passive constructions that hide responsibility."""

    id = "G014"
    name = "Impersonal Corporate Passive"
    description = "Detects 'it has been determined' constructions that hide who acted"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for impersonal passives that hide responsibility."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            for pattern in IMPERSONAL_CORPORATE_PASSIVE_PHRASES:
                for match in re.finditer(pattern, line):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Impersonal corporate passive: '{match.group()}' \u2014 consider naming who decided or acted",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class GenericSceneSettingOpenerRule(Rule):
    """G015: Detect generic scene-setting clauses in Markdown openers."""

    id = "G015"
    name = "Generic Scene-Setting Opener"
    description = "Detects generic scene-setting clauses in Markdown openers"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown"}
    content_scope = "prose"

    _patterns: ClassVar[tuple[re.Pattern[str], ...]] = (
        re.compile(
            r"^In\s+today['\u2019]s\s+(?:rapidly\s+evolving\s+)?"
            r"(?:digital\s+)?(?:world|landscape)(?=\s*[,:\u2013\u2014-])",
            re.IGNORECASE,
        ),
        re.compile(
            r"^In\s+the\s+modern\s+(?:digital\s+)?"
            r"(?:world|era|landscape)(?=\s*[,:\u2013\u2014-])",
            re.IGNORECASE,
        ),
        re.compile(
            r"^In\s+an?\s+rapidly\s+evolving\s+(?:digital\s+)?"
            r"(?:world|era|landscape)(?=\s*[,:\u2013\u2014-])",
            re.IGNORECASE,
        ),
        re.compile(
            r"^In\s+an\s+era\s+(?:defined|marked|characterized)\s+by\s+"
            r"(?:constant|rapid|unprecedented)\s+change"
            r"(?=\s*[,:\u2013\u2014-])",
            re.IGNORECASE,
        ),
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check the first substantive Markdown body sentence."""
        if not is_markdown_file(filename):
            return []

        sentence = next(
            (
                candidate
                for candidate in iter_prose_sentences(content, filename)
                if candidate.context == "body"
                and not is_example_line(content, filename, candidate.start_line)
            ),
            None,
        )
        if sentence is None:
            return []

        for pattern in self._patterns:
            match = pattern.match(sentence.text)
            if match is None:
                continue
            line, column = sentence.source_position(match.start())
            end_line, end_column = sentence.source_position(match.end())
            opener = " ".join(match.group().split())
            return [
                Issue(
                    rule_id=self.id,
                    message=f"Generic scene-setting opener: '{opener}'",
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion=(
                        "Replace the generic opener with the concrete subject or change"
                    ),
                )
            ]
        return []


class ExistentialOpenerRule(Rule):
    """G016: Detect existential openers with enough following text."""

    id = "G016"
    name = "Existential Opener"
    description = "Detects 'There is/are/was/were' followed by five or more words"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"^There\s+(?:is|are|was|were)\b", re.IGNORECASE
    )
    _word: ClassVar[re.Pattern[str]] = re.compile(r"\b\w+(?:[-'\u2019]\w+)*\b")
    _MIN_REMAINDER_WORDS = 5

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose sentences for supported existential openers."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            if is_example_line(content, filename, sentence.start_line):
                continue
            match = next(
                iter_prose_regex_matches(
                    sentence, sentence.source_text(content), filename, self._pattern
                ),
                None,
            )
            if (
                match is None
                or len(self._word.findall(sentence.text[match.end() :]))
                < self._MIN_REMAINDER_WORDS
            ):
                continue
            line, column = sentence.source_position(match.start())
            end_line, end_column = sentence.source_position(match.end())
            opener = " ".join(match.group().split())
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Existential opener: '{opener}'",
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Start with the sentence's subject",
                )
            )
        return issues


class EmptyItOpenerRule(Rule):
    """G017: Detect narrow empty 'It' sentence openers."""

    id = "G017"
    name = 'Empty "It" Opener'
    description = "Detects empty 'It is clear/obvious/evident that' sentence openers"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"^It\s+is\s+(?:clear|obvious|evident)\s+that\b",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose sentences for the approved empty openers."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            if is_example_line(content, filename, sentence.start_line):
                continue
            match = next(
                iter_prose_regex_matches(
                    sentence, sentence.source_text(content), filename, self._pattern
                ),
                None,
            )
            if match is None:
                continue
            line, column = sentence.source_position(match.start())
            end_line, end_column = sentence.source_position(match.end())
            opener = " ".join(match.group().split())
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Empty 'It' opener: '{opener}'",
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="State the evidence or conclusion directly",
                )
            )
        return issues


class AmbiguousThisRule(Rule):
    """G019: Detect a small allowlist of ambiguous 'This' openers."""

    id = "G019"
    name = 'Ambiguous "This"'
    description = "Detects sentence-opening 'This causes/means/shows'"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"^This\s+(?:causes|means|shows)(?![\w-])", re.IGNORECASE
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose sentences for approved ambiguous openers."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            if is_example_line(content, filename, sentence.start_line):
                continue
            match = next(
                iter_prose_regex_matches(
                    sentence, sentence.source_text(content), filename, self._pattern
                ),
                None,
            )
            if match is None:
                continue
            line, column = sentence.source_position(match.start())
            end_line, end_column = sentence.source_position(match.end())
            opener = " ".join(match.group().split())
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Ambiguous 'This' opener: '{opener}'",
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Name what 'This' refers to",
                )
            )
        return issues


class FormerLatterReferenceRule(Rule):
    """G022: Detect exact former/latter references."""

    id = "G022"
    name = "Former/Latter Reference"
    description = "Detects exact uses of 'the former' and 'the latter'"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"\bthe\s+(?:former|latter)\b", re.IGNORECASE
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose sentences for exact former/latter references."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            if is_example_line(content, filename, sentence.start_line):
                continue
            source = sentence.source_text(content)
            for match in iter_prose_regex_matches(
                sentence, source, filename, self._pattern
            ):
                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(match.end())
                reference = " ".join(match.group().split())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Former/latter reference: '{reference}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion="Name the referenced item directly",
                    )
                )
        return issues


class UnclearActorRequirementRule(Rule):
    """G024: Detect fixed impersonal requirement openers."""

    id = "G024"
    name = "Unclear Actor in Requirement"
    description = "Detects fixed impersonal requirement forms without a named actor"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?:It\s+must\s+be\s+ensured\s+that|Care\s+should\s+be\s+taken\s+to)\b",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose sentences for the approved impersonal requirements."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            if is_example_line(content, filename, sentence.start_line):
                continue
            match = next(
                iter_prose_regex_matches(
                    sentence, sentence.source_text(content), filename, self._pattern
                ),
                None,
            )
            if match is None:
                continue
            line, column = sentence.source_position(match.start())
            end_line, end_column = sentence.source_position(match.end())
            phrase = " ".join(match.group().split())
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Unclear actor in requirement: '{phrase}'",
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Name the actor responsible for the requirement",
                )
            )
        return issues


class WeakInstructionVerbRule(Rule):
    """G025: Detect exact weak procedural instruction phrases."""

    id = "G025"
    name = "Weak Instruction Verb"
    description = "Detects 'You will need to' and 'You can proceed to'"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"\bYou\s+(?:will\s+need|can\s+proceed)\s+to\b", re.IGNORECASE
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose sentences for the approved weak instruction phrases."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            if is_example_line(content, filename, sentence.start_line):
                continue
            source = sentence.source_text(content)
            for match in iter_prose_regex_matches(
                sentence, source, filename, self._pattern
            ):
                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(match.end())
                phrase = " ".join(match.group().split())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Weak instruction phrase: '{phrase}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion="Use a direct imperative",
                    )
                )
        return issues


class DoubleNegativeRule(Rule):
    """G029: Detect fixed double-negative forms."""

    id = "G029"
    name = "Double Negative"
    description = "Detects fixed double-negative phrases"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose for fixed double-negative phrases."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context == "heading":
                continue
            source = sentence.source_text(content)
            for phrase in DOUBLE_NEGATIVE_REPLACEMENTS:
                pattern = re.compile(
                    r"\b"
                    + r"\s+".join(re.escape(word) for word in phrase.split())
                    + r"\b",
                    re.IGNORECASE,
                )
                for match in pattern.finditer(sentence.text):
                    original = source[match.start() : match.end()]
                    if filename.lower().endswith(".py"):
                        original = re.sub(r"(?m)^[ \t]*#[ \t]?", "", original)
                    elif sentence.context == "blockquote":
                        original = re.sub(r"(?m)^(?: {0,3}>[ \t]?)+", "", original)
                    if pattern.fullmatch(original) is None:
                        continue
                    line, column = sentence.source_position(match.start())
                    end_line, end_column = sentence.source_position(match.end())
                    normalized = " ".join(match.group().split())
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Double negative: '{normalized}'",
                            line=line,
                            column=column,
                            end_line=end_line if end_line != line else None,
                            end_column=end_column,
                            severity=self.severity,
                            confidence=self.default_confidence,
                            suggestion=DOUBLE_NEGATIVE_REPLACEMENTS[
                                normalized.casefold()
                            ],
                        )
                    )
        return sorted(issues, key=lambda issue: (issue.line, issue.column))


class ClauseCoordinationOverloadRule(Rule):
    """G031: Detect sentences with many explicit clause boundaries."""

    id = "G031"
    name = "Clause/Coordination Overload"
    description = "Detects four or more explicit clause boundaries in one sentence"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _boundary: ClassVar[re.Pattern[str]] = re.compile(
        r";(?!\s*(?:and|but|nor|or|so|yet)\b)"
        r"|\b(?:and|but|nor|or|so|yet)\b"
        r"|\b(?:although|because(?!\s+of\b)|even\s+(?:if|though)|if|unless|whereas|while)\b",
        re.IGNORECASE,
    )
    _MIN_BOUNDARIES = 4

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose sentences for clause/coordination overload."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            if is_example_line(content, filename, sentence.start_line):
                continue
            boundary_count = len(self._boundary.findall(sentence.text))
            if boundary_count < self._MIN_BOUNDARIES:
                continue
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=(
                        "Clause/coordination overload: "
                        f"{boundary_count} boundaries in one sentence"
                    ),
                    line=sentence.start_line,
                    column=sentence.start_column,
                    end_line=sentence.end_line,
                    end_column=sentence.end_column,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Split the sentence or simplify its clause structure",
                )
            )
        return issues


class HedgedRequirementRule(Rule):
    """G037: Detect exact contradictory normative combinations."""

    id = "G037"
    name = "Hedged Requirement"
    description = "Detects 'must normally' and 'should generally'"
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:must\s+normally|should\s+generally)\b", re.IGNORECASE
    )
    _definition_suffix: ClassVar[re.Pattern[str]] = re.compile(
        r"^[\"'\u2019\u201d)*_]*\s+"
        r"(?:means|refers\s+to|is\s+defined\s+as|denotes)\b",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check prose sentences for exact hedged requirements."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            if sentence.context not in {"body", "list_item", "blockquote"}:
                continue
            if is_example_line(content, filename, sentence.start_line):
                continue
            source = sentence.source_text(content)
            for match in iter_prose_regex_matches(
                sentence, source, filename, self._pattern
            ):
                definition = self._definition_suffix.match(sentence.text[match.end() :])
                if definition is not None and self._definition_suffix.fullmatch(
                    original_prose_slice(
                        sentence,
                        source,
                        filename,
                        match.end(),
                        match.end() + definition.end(),
                    )
                ):
                    continue
                line, column = sentence.source_position(match.start())
                end_line, end_column = sentence.source_position(match.end())
                phrase = " ".join(match.group().split())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Hedged requirement: '{phrase}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion="Choose one requirement strength",
                    )
                )
        return issues


class UndefinedComparativeRule(Rule):
    """G038: Detect curated comparative claims without attached targets."""

    id = "G038"
    name = "Undefined Comparative"
    description = "Detects predicate comparatives without an attached comparison target"
    severity = Severity.INFO
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _CLAIM: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:is|are|was|were|remain(?:s|ed)?)\s+"
        r"(?P<claim>(?:(?:much|far|significantly|considerably|noticeably|"
        r"substantially)\s+)?(?:better|worse|faster|slower|easier|harder|"
        r"cheaper|safer|simpler|clearer|stronger|weaker|higher|lower|larger|"
        r"smaller|(?:more|less)\s+(?:accurate|complex|efficient|expensive|"
        r"maintainable|readable|reliable|scalable|secure|stable|verbose)))\b",
        re.IGNORECASE,
    )
    _TARGET: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:against|among|between|compared\s+(?:to|with)|relative\s+to|"
        r"than|versus|vs\.?)\s+[\"'\u201c]?\w+\b",
        re.IGNORECASE,
    )
    _SUBJECT: ClassVar[re.Pattern[str]] = re.compile(
        r"\s*(?:The\s+)?(?P<name>[^\W\d_]\w*)(?:\s+parser)?\s*"
    )
    _NAMED_PAIR: ClassVar[re.Pattern[str]] = re.compile(
        r"^We\s+compared\s+(?P<first>[^\W\d_]\w*)\s+and\s+"
        r"(?P<second>[^\W\d_]\w*)\b",
        re.IGNORECASE,
    )
    _HEADING_TARGET: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?:Comparison\s+target:|Compared\s+(?:to|with))\s+"
        r"(?P<name>[^\W\d_]\w*)(?:\s+parser)?$",
        re.IGNORECASE,
    )
    _PRONOUNS: ClassVar[frozenset[str]] = frozenset(
        {"he", "i", "it", "she", "that", "these", "they", "this", "those", "we"}
    )
    _LITERAL_CONTEXT: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:avoid|do not|don't)\s+(?:claim(?:ing)?|say(?:ing)?|writ(?:e|ing))\b"
        r"|\bthe (?:label|phrase|wording)\b",
        re.IGNORECASE,
    )
    _HYPOTHETICAL: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:if|whether)\b", re.IGNORECASE
    )

    @classmethod
    def _has_attached_target(
        cls, sentence: ProseSentence, source: str, filename: str, start: int, end: int
    ) -> bool:
        first, last = _claim_scope(source, start, end)
        for target in iter_prose_regex_matches(sentence, source, filename, cls._TARGET):
            if not first <= target.start() < target.end() <= last:
                continue
            if target.end() <= start and not _FINITE_CLAUSE.search(
                source[first : target.start()]
            ):
                return True
            if target.start() >= end and not _FINITE_CLAUSE.search(
                source[end : target.start()]
            ):
                return True
        return False

    @staticmethod
    def _only_prose_gap(
        lines: list[str], previous: ProseSentence, current: ProseSentence, filename: str
    ) -> bool:
        if previous.end_line == current.start_line:
            gap = lines[current.start_line - 1][
                previous.end_column - 1 : current.start_column - 1
            ]
        else:
            parts = lines[previous.end_line - 1 : current.start_line]
            parts[0] = parts[0][previous.end_column - 1 :]
            parts[-1] = parts[-1][: current.start_column - 1]
            gap = "\n".join(parts)
        if filename.lower().endswith(".py"):
            gap = re.sub(r"(?m)^[ \t]*#[ \t]?", "", gap)
        return not gap.strip()

    @classmethod
    def _has_named_context(
        cls,
        content: str,
        filename: str,
        lines: list[str],
        previous: ProseSentence | None,
        current: ProseSentence,
        start: int,
        end: int,
    ) -> bool:
        if previous is None or not cls._only_prose_gap(
            lines, previous, current, filename
        ):
            return False
        source = current.source_text(content)
        first, _ = _claim_scope(source, start, end)
        subject = cls._SUBJECT.fullmatch(
            original_prose_slice(current, source, filename, first, start)
        )
        if subject is None:
            return False
        name = subject.group("name")
        if not name[0].isupper() or name.casefold() in cls._PRONOUNS:
            return False
        previous_source = previous.source_text(content)
        if previous.context == "heading" and not filename.lower().endswith(".py"):
            target = cls._HEADING_TARGET.fullmatch(previous_source)
            return bool(
                target is not None
                and target.group("name")[0].isupper()
                and target.group("name").casefold() != name.casefold()
            )
        if previous.context != current.context or (
            current.context == "list_item" and previous.scope_id != current.scope_id
        ):
            return False
        for pair in iter_prose_regex_matches(
            previous, previous_source, filename, cls._NAMED_PAIR
        ):
            names = (pair.group("first"), pair.group("second"))
            if all(value[0].isupper() for value in names) and (
                names[0].casefold() != names[1].casefold()
                and name.casefold() in {value.casefold() for value in names}
            ):
                return True
        return False

    def check(self, content: str, filename: str) -> list[Issue]:
        """Report curated comparatives without supported target attachment."""
        issues: list[Issue] = []
        source_lines = content.split("\n")
        sentences = iter_prose_sentences(content, filename)
        for index, sentence in enumerate(sentences):
            if (
                sentence.context not in {"body", "list_item"}
                or is_example_line(content, filename, sentence.start_line)
                or sentence.text.rstrip().endswith("?")
            ):
                continue
            source = sentence.source_text(content)
            if any(
                iter_prose_regex_matches(
                    sentence, source, filename, self._LITERAL_CONTEXT
                )
            ):
                continue
            for match in iter_prose_regex_matches(
                sentence, source, filename, self._CLAIM
            ):
                if self._HYPOTHETICAL.search(sentence.text[: match.start()]):
                    continue
                if self._has_attached_target(
                    sentence, source, filename, match.start(), match.end()
                ) or self._has_named_context(
                    content,
                    filename,
                    source_lines,
                    sentences[index - 1] if index else None,
                    sentence,
                    match.start(),
                    match.end(),
                ):
                    continue
                start, end = match.span("claim")
                line, column = sentence.source_position(start)
                end_line, end_column = sentence.source_position(end)
                claim = " ".join(match.group("claim").split())
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Undefined comparative: '{claim}'",
                        line=line,
                        column=column,
                        end_line=end_line,
                        end_column=end_column,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion="Name the comparison target",
                    )
                )
        return issues


class RepeatedFunctionWordRule(Rule):
    """G039: Detect adjacent repetitions from a closed function-word list."""

    id = "G039"
    name = "Repeated Function Word"
    description = "Detects repeated adjacent function words"
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    _FUNCTION_WORDS: ClassVar[frozenset[str]] = frozenset(
        {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "for",
            "to",
            "of",
            "in",
            "on",
            "at",
            "by",
            "from",
            "with",
        }
    )
    _WORD = re.compile(r"\b[a-z]+\b", re.IGNORECASE)

    def check(self, content: str, filename: str) -> list[Issue]:
        """Report one duplicated tail for each accidental repetition run."""
        issues: list[Issue] = []
        for sentence in iter_prose_sentences(content, filename):
            source = sentence.source_text(content)
            previous: re.Match[str] | None = None
            run_issue: Issue | None = None
            for match in self._WORD.finditer(sentence.text):
                word = match.group().casefold()
                repeated = False
                if (
                    previous
                    and word in self._FUNCTION_WORDS
                    and word == previous.group().casefold()
                ):
                    gap = source[previous.end() : match.start()]
                    if filename.lower().endswith(".py"):
                        gap = re.sub(r"(?m)^[ \t]*#[ \t]?", "", gap)
                    elif sentence.context == "blockquote":
                        gap = re.sub(r"(?m)^(?: {0,3}>[ \t]?)+", "", gap)
                    repeated = (
                        not sentence.text[previous.end() : match.start()].strip()
                        and not gap.strip()
                    )
                if repeated:
                    end_line, end_column = sentence.source_position(match.end())
                    if run_issue is None:
                        line, column = sentence.source_position(match.start())
                        run_issue = Issue(
                            rule_id=self.id,
                            message=f"Repeated function word: '{word}'",
                            line=line,
                            column=column,
                            severity=self.severity,
                            confidence=self.default_confidence,
                            suggestion="Keep one occurrence",
                        )
                        issues.append(run_issue)
                    run_issue.end_line = (
                        end_line if end_line != run_issue.line else None
                    )
                    run_issue.end_column = end_column
                else:
                    run_issue = None
                previous = match
        return issues
