"""Structural and grammatical patterns."""

# Rule of three patterns (S001)
RULE_OF_THREE_PATTERNS = [
    r"\b(\w+),\s+(\w+),\s+and\s+(\w+)\b",
    r"\b(\w+),\s+(\w+),\s+or\s+(\w+)\b",
]

# Negative parallelism (S002)
NEGATIVE_PARALLELISM_PATTERNS = [
    r"not only\s+.+\s+but also",
    r"it'?s not (just )?about\s+.+,?\s+(it'?s|but) (also )?about",
    r"(while|although|though)\s+.+,\s+.+\s+(also|still|nevertheless)",
]

# Challenge conclusions (S003)
CHALLENGE_CONCLUSION_PATTERNS = [
    r"despite (its|their|the)\s+.+,?\s+(still )?(faces?|remains?|continues?)",
    r"(while|although)\s+.+,?\s+(challenges?|obstacles?|hurdles?) (remain|persist|exist)",
    r"future (outlook|prospects|direction)",
    r"looking (ahead|forward)",
    r"moving forward",
    r"going forward",
]

# Inline header lists (S004)
INLINE_HEADER_LIST_PATTERN = r"^[-*]\s+\*\*[^*]+\*\*:\s+"

# Significance emphasis (S005)
SIGNIFICANCE_PATTERNS = [
    r"pivotal moment",
    r"key turning point",
    r"marks? a (significant|major|important)",
    r"marking the",
    r"reflects? broader",
    r"(significant|notable|important|major) (milestone|achievement|development)",
]

# Superficial analysis - participle chains (S006)
PARTICIPLE_CHAIN_PATTERNS = [
    r"\b\w+ing\s+(its|their|the)\s+\w+,?\s+\w+ing",
    r"highlighting\s+.+\s+(underscoring|emphasizing|showcasing)",
    r"(fostering|encouraging|promoting)\s+.+\s+(while|and)\s+\w+ing",
]

# Copula avoidance (G001)
COPULA_AVOIDANCE_PATTERNS = [
    r"\bserves as\b",
    r"\bstands as\b",
    r"\brepresents\b",
    r"\bconstitutes\b",
    r"\bfunctions as\b",
    r"\boperates as\b",
    r"\bacts as\b",
]

# Excessive hedging (G002)
HEDGING_PATTERNS = [
    r"it is (important|worth|interesting|notable) to note that",
    r"it('s| is) worth (noting|mentioning|pointing out)",
    r"it should be (noted|mentioned|pointed out)",
    r"one (might|could|may) (argue|say|note)",
    r"(arguably|perhaps|possibly|potentially)",
    r"to some (extent|degree)",
    r"in (some|many|most) (ways|respects|cases)",
]

# Dramatic countdown patterns (S008)
DRAMATIC_COUNTDOWN_PATTERN = r"(?:^|(?<=\n))\s*Not\s+[^.!?\n]+\.\s*Not\s+[^.!?\n]+\.\s*(?:Just|But|Only|Simply)\s+[^.!?\n]+\."

# Rhetorical self-answer patterns (S009)
RHETORICAL_SELF_ANSWER_PATTERN = r"(?:^|(?<=\n))([^\n?]*\?\s*)\n\s*([A-Z][^.!?\n]{0,50}[.!])"

# Listicle in prose patterns (S012)
LISTICLE_PROSE_PATTERNS = [
    r"\bthe first\b.+\bthe second\b.+\bthe third\b",
    r"\bfirst(?:ly)?,\b.+\bsecond(?:ly)?,\b.+\bthird(?:ly)?,\b",
    r"\bthe (first|1st) (takeaway|point|lesson|wall|reason)",
]

# Anecdote-as-evidence patterns (S017)
ANECDOTE_EVIDENCE_PATTERNS = [
    r"(?i)^For [A-Z][a-z]+ of [A-Z][a-z]+",
    r"(?i)^Take [A-Z][a-z]+, a \w+",
    r"(?i)^Meet [A-Z][a-z]+",
]

# All structural patterns for easy access
STRUCTURAL_PATTERNS = {
    "rule_of_three": RULE_OF_THREE_PATTERNS,
    "negative_parallelism": NEGATIVE_PARALLELISM_PATTERNS,
    "challenge_conclusions": CHALLENGE_CONCLUSION_PATTERNS,
    "inline_header_list": INLINE_HEADER_LIST_PATTERN,
    "significance": SIGNIFICANCE_PATTERNS,
    "participle_chains": PARTICIPLE_CHAIN_PATTERNS,
    "copula_avoidance": COPULA_AVOIDANCE_PATTERNS,
    "hedging": HEDGING_PATTERNS,
    "dramatic_countdown": DRAMATIC_COUNTDOWN_PATTERN,
    "rhetorical_self_answer": RHETORICAL_SELF_ANSWER_PATTERN,
    "listicle_prose": LISTICLE_PROSE_PATTERNS,
    "anecdote_evidence": ANECDOTE_EVIDENCE_PATTERNS,
}
