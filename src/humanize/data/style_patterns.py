"""Style-related detection patterns."""

from typing import Final

# Words that should not be capitalized in title case (T001)
TITLE_CASE_SMALL_WORDS: Final[set[str]] = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "in",
    "nor",
    "of",
    "on",
    "or",
    "so",
    "the",
    "to",
    "up",
    "yet",
}

# Pairs of simple/formal synonyms for elegant variation detection (T006)
# Format: (simple_word_pattern, formal_word_pattern)
ELEGANT_VARIATION_PAIRS: Final[list[tuple[str, str]]] = [
    (r"\bsaid\b", r"\bstated\b"),
    (r"\bsaid\b", r"\bremarked\b"),
    (r"\bsaid\b", r"\bnoted\b"),
    (r"\bsaid\b", r"\bopined\b"),
    (r"\buse\b", r"\butilize\b"),
    (r"\buse\b", r"\bemploy\b"),
    (r"\bshow\b", r"\bdemonstrate\b"),
    (r"\bget\b", r"\bobtain\b"),
    (r"\bget\b", r"\bacquire\b"),
]
