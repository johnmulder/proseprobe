"""Overused vocabulary word lists."""

from typing import Final

# Tier 1: High confidence markers (rarely used naturally)
AI_VOCABULARY_TIER1: Final[set[str]] = {
    "delve",
    "tapestry",
    "multifaceted",
    "intricately",
    "nuanced",
    "underscores",
    "testament",
    "interplay",
    "showcasing",
    "underscoring",
    "leveraging",
    "meticulous",
    "intricacies",
    "indelible",
    "embark",
    "poised",
    "unraveling",
    "navigating",
    "spearheading",
    "fostering",
}

# Tier 2: Medium confidence (context-dependent)
AI_VOCABULARY_TIER2 = {
    "crucial",
    "pivotal",
    "landscape",
    "vibrant",
    "enhance",
    "robust",
    "comprehensive",
    "innovative",
    "dynamic",
    "seamless",
    "groundbreaking",
    "transformative",
    "cutting-edge",
    "streamline",
    "optimize",
    "leverage",
    "harness",
    "empower",
    "endeavor",
    "paramount",
}

# Tier 3: Low confidence (common but frequently overused)
AI_VOCABULARY_TIER3 = {
    "key",
    "important",
    "significant",
    "notable",
    "essential",
    "fundamental",
    "critical",
    "major",
    "substantial",
    "remarkable",
}

# Combined vocabulary (all tiers)
AI_VOCABULARY = AI_VOCABULARY_TIER1 | AI_VOCABULARY_TIER2 | AI_VOCABULARY_TIER3

# Suggested replacements for fixable rules
VOCABULARY_SUGGESTIONS: dict[str, str] = {
    # Tier 1
    "delve": "explore",
    "tapestry": "collection",
    "multifaceted": "complex",
    "intricately": "closely",
    "nuanced": "subtle",
    "underscores": "shows",
    "testament": "proof",
    "interplay": "interaction",
    "showcasing": "showing",
    "underscoring": "showing",
    "leveraging": "using",
    "meticulous": "careful",
    "intricacies": "details",
    "indelible": "lasting",
    "embark": "start",
    "poised": "ready",
    "unraveling": "explaining",
    "navigating": "handling",
    "spearheading": "leading",
    "fostering": "encouraging",
    # Tier 2
    "crucial": "important",
    "pivotal": "key",
    "landscape": "field",
    "vibrant": "active",
    "enhance": "improve",
    "robust": "strong",
    "comprehensive": "complete",
    "innovative": "new",
    "dynamic": "changing",
    "seamless": "smooth",
    "groundbreaking": "new",
    "transformative": "major",
    "cutting-edge": "modern",
    "streamline": "simplify",
    "optimize": "improve",
    "leverage": "use",
    "harness": "use",
    "empower": "enable",
    "endeavor": "effort",
    "paramount": "important",
}

# Vocabulary specific to code/docstrings (used by C001)
# Format: (regex_pattern, display_word, replacement)
DOCSTRING_AI_VOCABULARY: Final[list[tuple[str, str, str]]] = [
    (r"\bdelve\b", "delve", "explore"),
    (r"\bleverage\b", "leverage", "use"),
    (r"\butilize\b", "utilize", "use"),
    (r"\bfacilitate\b", "facilitate", "help"),
    (r"\bseamless(?:ly)?\b", "seamless", "smooth"),
    (r"\brobust\b", "robust", "strong"),
    (r"\bcomprehensive\b", "comprehensive", "complete"),
    (r"\bbespoke\b", "bespoke", "custom"),
    (r"\bholistic\b", "holistic", "complete"),
    (r"\bfoster\b", "foster", "encourage"),
    (r"\bsynergy\b", "synergy", "cooperation"),
    (r"\bparadigm\b", "paradigm", "model"),
]
