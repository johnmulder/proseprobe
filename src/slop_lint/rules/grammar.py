"""Grammar pattern detection rules (G001-G003)."""

import re

from slop_lint.data.patterns import COPULA_AVOIDANCE_PATTERNS, HEDGING_PATTERNS
from slop_lint.rules.base import Issue, Rule, Severity


class CopulaAvoidanceRule(Rule):
    """G001: Detect copula avoidance."""

    id = "G001"
    name = "Copula Avoidance"
    description = "Detects 'serves as' instead of 'is'"
    severity = Severity.INFO
    fixable = False
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
    fixable = False
    applies_to = {"markdown"}
    content_scope = "prose"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for excessive hedging."""
        issues: list[Issue] = []
        for line_num, line in self.iter_lines(content, filename):
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

        return issues


class ParticipleChainsRule(Rule):
    """G003: Detect dangling participle chains."""

    id = "G003"
    name = "Participle Chains"
    description = "Detects 'highlighting..., emphasizing..., fostering...' chains"
    severity = Severity.WARNING
    fixable = False
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
