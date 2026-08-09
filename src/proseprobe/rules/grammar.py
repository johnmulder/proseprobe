"""Grammar pattern detection rules (G001-G017, G019, G022, G024, G029)."""

import re
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
    iter_prose_blocks,
    iter_prose_scopes,
    iter_prose_sentences,
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
        for line_num, line in self.iter_lines(content, filename):
            for pattern in COPULA_AVOIDANCE_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Copula avoidance: '{match.group()}' → consider 'is'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        return issues


class ExcessiveHedgingRule(Rule):
    """G002: Detect excessive hedging."""

    id = "G002"
    name = "Excessive Hedging"
    description = "Detects 'It is important to note that...' patterns"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    # Individual hedge words for per-sentence stacking detection
    _HEDGE_WORDS = re.compile(
        r"\b(?:may|might|potentially|arguably|possibly|perhaps)\b"
        r"|(?:appears? to|suggests? that|could be(?: interpreted as)?)",
        re.IGNORECASE,
    )

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for excessive hedging."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            # Existing phrase-level detection
            for pattern in HEDGING_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Hedging phrase: '{match.group()}'",
                            line=line_num,
                            column=match.start() + 1,
                            end_column=match.end() + 1,
                            severity=self.severity,
                        )
                    )

        for sentence in iter_prose_sentences(content, filename):
            hedge_matches = list(self._HEDGE_WORDS.finditer(sentence.text))
            if len(hedge_matches) < 2:
                continue
            sentence_line, sentence_column = sentence.source_position()
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=(
                        f"Hedge stacking: {len(hedge_matches)} hedges in one sentence"
                    ),
                    line=sentence_line,
                    column=sentence_column,
                    severity=self.severity,
                    confidence=Confidence.HIGH,
                )
            )

        return list({(issue.line, issue.column): issue for issue in issues}.values())


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
        """Check content for detect 'here's the kicker' false suspense transitions."""
        """Check content for detect 'here's the kicker' false suspense transitions."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            line_lower = line.lower()
            for phrase in FALSE_SUSPENSE_PHRASES:
                if phrase in line_lower:
                    col = line_lower.find(phrase)
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"False suspense: '{phrase}'",
                            line=line_num,
                            column=col + 1,
                            end_column=col + len(phrase) + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class PatronizingAnalogyRule(Rule):
    """G005: Detect 'Think of it as...' patronizing analogies."""

    id = "G005"
    name = "Patronizing Analogy"
    description = "Detects 'think of it as/like' patronizing analogies"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 'Think of it as...' patronizing analogies."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            line_lower = line.lower()
            for phrase in PATRONIZING_ANALOGY_PHRASES:
                if phrase in line_lower:
                    col = line_lower.find(phrase)
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Patronizing analogy: '{phrase}'",
                            line=line_num,
                            column=col + 1,
                            end_column=col + len(phrase) + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class FuturistInvitationRule(Rule):
    """G006: Detect 'Imagine a world where...' futurist invitations."""

    id = "G006"
    name = "Futurist Invitation"
    description = "Detects 'imagine a world where' futurist framing"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 'Imagine a world where...' futurist invitations."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            line_lower = line.lower()
            for phrase in FUTURIST_INVITATION_PHRASES:
                if phrase in line_lower:
                    col = line_lower.find(phrase)
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Futurist invitation: '{phrase}'",
                            line=line_num,
                            column=col + 1,
                            end_column=col + len(phrase) + 1,
                            severity=self.severity,
                        )
                    )
        return issues


class FalseVulnerabilityRule(Rule):
    """G007: Detect 'I'll be honest' false vulnerability."""

    id = "G007"
    name = "False Vulnerability"
    description = "Detects performative self-awareness phrases"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"markdown", "python"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check content for detect 'I'll be honest' false vulnerability."""
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
        """Check content for detect 'The reality is simpler' asserted simplicity."""
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
        """Check content for detect 'Let's break this down' pedagogical voice."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            line_lower = line.lower()
            for phrase in PEDAGOGICAL_VOICE_PHRASES:
                if phrase in line_lower:
                    col = line_lower.find(phrase)
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Pedagogical voice: '{phrase}'",
                            line=line_num,
                            column=col + 1,
                            end_column=col + len(phrase) + 1,
                            severity=self.severity,
                        )
                    )
        return issues


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
        """Check content for detect false-balance framing."""
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
        """Check content for detect overuse of nominalization constructions."""
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
        """Check content for detect overuse of formulaic academic passive voice."""
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
        """Check content for detect 'gap in the literature' ritual phrases."""
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
        """Check content for detect impersonal passive constructions that hide responsibility."""
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
            match = self._pattern.match(sentence.text)
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
            match = self._pattern.match(sentence.text)
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
            match = self._pattern.match(sentence.text)
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
            for match in self._pattern.finditer(sentence.text):
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
            match = self._pattern.match(sentence.text)
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
        for block in iter_prose_blocks(content, filename):
            if block.context == "heading":
                continue
            for line_num, line in block.lines:
                for phrase, replacement in DOUBLE_NEGATIVE_REPLACEMENTS.items():
                    pattern = rf"\b{re.escape(phrase)}\b"
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message=f"Double negative: '{match.group()}'",
                                line=line_num,
                                column=match.start() + 1,
                                end_column=match.end() + 1,
                                severity=self.severity,
                                confidence=self.default_confidence,
                                suggestion=replacement,
                            )
                        )
        return sorted(issues, key=lambda issue: (issue.line, issue.column))
