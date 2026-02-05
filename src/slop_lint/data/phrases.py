"""Bad phrase patterns."""

# Collaborative/chat-like phrases (V002)
COLLABORATIVE_PHRASES = [
    "I hope this helps",
    "Let me know if",
    "Feel free to",
    "I'd be happy to",
    "Certainly!",
    "Absolutely!",
    "Great question",
    "That's a great",
    "Would you like me to",
    "Here's a",
    "Here is a",
    "I'll provide",
    "I can help you",
    "Allow me to",
    "Let me explain",
    "To summarize",
    "In summary",
    "To conclude",
    "As you can see",
    "As mentioned earlier",
    "As noted above",
    "As discussed",
    "As I mentioned",
]

# Knowledge cutoff patterns (V003)
KNOWLEDGE_CUTOFF_PATTERNS = [
    r"as of my (last |knowledge )?(?:update|cutoff|training)",
    r"based on (my |available )?information",
    r"as of \w+ \d{4}",
    r"my training (data )?(only )?(goes|extends|covers)",
    r"I don't have (access to )?real-time",
    r"I cannot (browse|access|search) the (internet|web)",
    r"my knowledge (is limited to|ends at|was last updated)",
]

# Promotional/puffery language (V004)
PROMOTIONAL_PHRASES = [
    "boasts",
    "nestled",
    "in the heart of",
    "renowned",
    "world-class",
    "state-of-the-art",
    "best-in-class",
    "industry-leading",
    "second to none",
    "unparalleled",
    "unprecedented",
    "game-changing",
    "revolutionary",
    "groundbreaking",
    "trailblazing",
    "next-generation",
    "bleeding-edge",
    "paradigm shift",
    "synergy",
    "holistic approach",
    "end-to-end",
    "turnkey solution",
    "one-stop shop",
    "best practices",
    "thought leader",
    "move the needle",
    "low-hanging fruit",
    "circle back",
]

# Weasel words and vague attributions (V005)
WEASEL_PHRASES = [
    r"experts (say|argue|believe|suggest|claim|note)",
    r"studies (show|suggest|indicate|have shown)",
    r"research (shows|suggests|indicates|has shown)",
    r"it is (widely )?(known|believed|thought|considered)",
    r"many (people|experts|researchers|scientists) (believe|think|argue)",
    r"some (people|experts|researchers|scientists) (say|argue|believe)",
    r"industry (experts|analysts|observers) (say|note|suggest)",
    r"(observers|analysts|critics) (have )?(noted|observed|pointed out)",
    r"according to (some|many|various|numerous) (sources|reports|studies)",
    r"(some|many) would argue",
    r"it('s| is) (often|generally|commonly|widely) (said|believed|thought)",
    r"there is (growing|increasing|mounting) (evidence|concern|interest)",
]
