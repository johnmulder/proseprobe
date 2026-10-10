"""Source-mapped matching and bounded clause evidence for phrase rules."""

import re
from collections.abc import Iterator, Sequence

from proseprobe.parsers.prose import ProseSentence, iter_prose_sentences
from proseprobe.rules.base import Issue, Rule

_CLAUSE_BOUNDARY = re.compile(
    r";|(?<!\d),|,(?!\d)|\b(?:and|or|but|yet|whereas|while)\b", re.IGNORECASE
)
_FINITE_CLAUSE = re.compile(
    r"\b(?:is|are|was|were|has|have|had|remains?|never|always|eliminates?)\b"
    r"|\b(?:we|they|I)\s+(?:tested|observed|compared|processed|reported|measured)\b",
    re.IGNORECASE,
)


def _claim_scope(text: str, start: int, end: int) -> tuple[int, int]:
    """Keep a claim's clause and its leading modifiers together."""
    left = 0
    right = len(text)
    previous = 0
    for boundary in _CLAUSE_BOUNDARY.finditer(text):
        if boundary.group().casefold() in {",", "and", "or"} and not (
            _FINITE_CLAUSE.search(text[previous : boundary.start()])
        ):
            continue
        previous = boundary.end()
        if boundary.end() <= start:
            left = boundary.end()
        elif boundary.start() >= end:
            right = boundary.start()
            break
    return left, right


def original_prose_slice(
    sentence: ProseSentence,
    source: str,
    filename: str,
    start: int,
    end: int,
) -> str:
    """Return literal source, removing only supported continuation prefixes."""
    original = source[start:end]
    if filename.lower().endswith(".py"):
        return re.sub(r"(?m)^[ \t]*#[ \t]?", "", original)
    if sentence.context == "blockquote":
        return re.sub(r"(?m)^(?: {0,3}>[ \t]?)+", "", original)
    return original


def iter_prose_regex_matches(
    sentence: ProseSentence,
    source: str,
    filename: str,
    pattern: re.Pattern[str],
) -> Iterator[re.Match[str]]:
    """Yield sentence matches whose original source also satisfies the pattern."""
    for match in pattern.finditer(sentence.text):
        original = original_prose_slice(
            sentence, source, filename, match.start(), match.end()
        )
        candidate = pattern.match(
            original_prose_slice(sentence, source, filename, match.start(), len(source))
        )
        if candidate is not None and candidate.end() == len(original):
            yield match


def longest_literal_phrase_issues(
    rule: Rule,
    content: str,
    filename: str,
    phrases: Sequence[str],
    message_label: str,
) -> list[Issue]:
    """Report the longest nonoverlapping literal phrases within each sentence."""
    patterns = [
        (
            phrase,
            re.compile(
                r"(?<!\w)"
                + r"\s+".join(re.escape(word) for word in phrase.split())
                + r"(?!\w)",
                re.IGNORECASE,
            ),
        )
        for phrase in phrases
    ]
    issues: list[Issue] = []
    for sentence in iter_prose_sentences(content, filename):
        source = sentence.source_text(content)
        candidates: list[tuple[re.Match[str], str]] = []
        for phrase, pattern in patterns:
            for match in pattern.finditer(sentence.text):
                original = source[match.start() : match.end()]
                if filename.lower().endswith(".py"):
                    original = re.sub(r"(?m)^[ \t]*#[ \t]?", "", original)
                elif sentence.context == "blockquote":
                    original = re.sub(r"(?m)^(?: {0,3}>[ \t]?)+", "", original)
                if pattern.fullmatch(original):
                    candidates.append((match, phrase))
        selected: list[tuple[re.Match[str], str]] = []
        for match, phrase in sorted(
            candidates,
            key=lambda item: (-len(item[1]), item[0].start(), item[1].casefold()),
        ):
            if any(
                match.start() < other.end() and other.start() < match.end()
                for other, _ in selected
            ):
                continue
            selected.append((match, phrase))
        for match, phrase in sorted(selected, key=lambda item: item[0].start()):
            line, column = sentence.source_position(match.start())
            end_line, end_column = sentence.source_position(match.end())
            issues.append(
                Issue(
                    rule_id=rule.id,
                    message=f"{message_label}: '{phrase}'",
                    line=line,
                    column=column,
                    end_line=end_line if end_line != line else None,
                    end_column=end_column,
                    severity=rule.severity,
                    confidence=rule.default_confidence,
                )
            )
    return issues
