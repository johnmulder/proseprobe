"""Grammar pattern detection rules (G001-G013)."""

import re

from slop_lint.data.patterns import (
    COPULA_AVOIDANCE_PATTERNS,
    HEDGING_PATTERNS,
    NOMINALIZATION_PATTERNS,
    PASSIVE_VOICE_PATTERNS,
)
from slop_lint.data.phrases import (
    ASSERTED_SIMPLICITY_PHRASES,
    FALSE_BALANCE_PHRASES,
    FALSE_SUSPENSE_PHRASES,
    FALSE_VULNERABILITY_PHRASES,
    FUTURIST_INVITATION_PHRASES,
    GAP_RITUAL_PHRASES,
    PATRONIZING_ANALOGY_PHRASES,
    PEDAGOGICAL_VOICE_PHRASES,
)
from slop_lint.rules.base import Confidence, Issue, Rule, Severity


class CopulaAvoidanceRule(Rule):
    """G001: Detect copula avoidance."""

    id = "G001"
    name = "Copula Avoidance"
    description = "Detects 'serves as' instead of 'is'"
    severity = Severity.INFO
    applies_to = {"markdown"}
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
    applies_to = {"markdown"}
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

            # Per-sentence hedge stacking detection
            sentences = re.split(r"(?<=[.!?])\s+", line)
            for sentence in sentences:
                hedge_matches = list(self._HEDGE_WORDS.finditer(sentence))
                if len(hedge_matches) >= 2:
                    col = line.find(sentence)
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Hedge stacking: {len(hedge_matches)} hedges in one sentence",
                            line=line_num,
                            column=max(1, col + 1),
                            severity=self.severity,
                            confidence=Confidence.HIGH,
                        )
                    )

        return issues


class ParticipleChainsRule(Rule):
    """G003: Detect dangling participle chains."""

    id = "G003"
    name = "Participle Chains"
    description = "Detects 'highlighting..., emphasizing..., fostering...' chains"
    severity = Severity.WARNING
    applies_to = {"markdown"}
    content_scope = "prose"

    # Pattern for multiple -ing words in a row (3+)
    _pattern = r"\b(\w+ing)\b[^.]*\b(\w+ing)\b[^.]*\b(\w+ing)\b"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for participle chains."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
            match = re.search(self._pattern, line, re.IGNORECASE)
            if match:
                # Extract the -ing words
                words = [match.group(1), match.group(2), match.group(3)]
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Participle chain: '{', '.join(words)}'",
                        line=line_num,
                        column=match.start() + 1,
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def __init__(self, threshold: int = 3) -> None:
        super().__init__()
        self.threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        issues: list[Issue] = []
        matches: list[tuple[int, re.Match[str]]] = []
        for line_num, line in self.iter_lines(content, filename):
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def __init__(self, threshold: int = 5) -> None:
        super().__init__()
        self.threshold = threshold

    def check(self, content: str, filename: str) -> list[Issue]:
        issues: list[Issue] = []
        matches: list[tuple[int, re.Match[str]]] = []
        for line_num, line in self.iter_lines(content, filename):
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
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
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
