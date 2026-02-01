"""Data files for vocabulary and patterns."""

from humanize.data.patterns import STRUCTURAL_PATTERNS
from humanize.data.phrases import (
    COLLABORATIVE_PHRASES,
    KNOWLEDGE_CUTOFF_PATTERNS,
    PROMOTIONAL_PHRASES,
    WEASEL_PHRASES,
)
from humanize.data.vocabulary import AI_VOCABULARY, VOCABULARY_SUGGESTIONS

__all__ = [
    "AI_VOCABULARY",
    "VOCABULARY_SUGGESTIONS",
    "COLLABORATIVE_PHRASES",
    "KNOWLEDGE_CUTOFF_PATTERNS",
    "PROMOTIONAL_PHRASES",
    "WEASEL_PHRASES",
    "STRUCTURAL_PATTERNS",
]
