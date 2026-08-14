"""Code-related detection patterns for Python files."""

from typing import Final

# Verbose comment patterns (C002)
# Format: (regex_pattern, reason_description)
VERBOSE_COMMENT_PATTERNS: Final[list[tuple[str, str]]] = [
    (r"#\s*This (?:function|method|class|variable|code)", "explains obvious"),
    (r"#\s*The following (?:code|section)", "announces code"),
    (r"#\s*As (?:you can see|mentioned)", "conversational"),
    (r"#\s*In order to\b", "wordy (use 'to')"),
    (r"#\s*It is (?:important|worth|necessary) to note", "hedging"),
    (r"#\s*Basically,?\s", "filler word"),
    (r"#\s*Essentially,?\s", "filler word"),
]

# Chat-like phrases in comments (C003)
# Format: (regex_pattern, display_phrase)
COLLABORATIVE_COMMENT_PATTERNS: Final[list[tuple[str, str]]] = [
    (r"#\s*I hope this helps", "I hope this helps"),
    (r"#\s*Let me know if", "Let me know if"),
    (r"#\s*Feel free to", "Feel free to"),
    (r"#\s*Happy coding", "Happy coding"),
    (r"#\s*Hope this (?:helps|works)", "Hope this"),
    (r"#\s*Here's (?:a|an|the)", "Here's..."),
    (r"#\s*I've (?:added|created|implemented)", "I've..."),
    (r"#\s*As requested", "As requested"),
    (r"#\s*As per your", "As per your"),
]

# Formulaic placeholder patterns (C004)
# Comment-only patterns: (regex_pattern, kind_description)
AI_PLACEHOLDER_COMMENT_PATTERNS: Final[list[tuple[str, str]]] = [
    (r"#\s*(?:TODO|FIXME|XXX)(?:\s*:)?(?=\s*$)", "marker without context"),
    (r"#\s*TODO:\s*Implement\s*$", "bare 'Implement'"),
    (r"#\s*TODO:\s*Add (?:logic|code) here", "generic placeholder"),
    (r"#\s*TODO:\s*Fill in", "generic placeholder"),
    (r"#\s*TODO:\s*Replace with actual", "generic placeholder"),
    (r"#\s*TODO:\s*Complete this", "generic placeholder"),
]

# Code-only placeholder patterns
AI_PLACEHOLDER_CODE_PATTERNS: Final[list[tuple[str, str]]] = [
    (r"raise NotImplementedError\([\"'].*[\"']\)", "template error"),
]

# Inline code + comment placeholder patterns
# Format: (code_pattern, comment_pattern, kind_description)
AI_PLACEHOLDER_INLINE_PATTERNS: Final[list[tuple[str, str, str]]] = [
    (r"\bpass\b", r"(?:TODO|placeholder)", "pass with placeholder"),
    (r"\.\.\.", r"(?:TODO|your code)", "ellipsis placeholder"),
]
