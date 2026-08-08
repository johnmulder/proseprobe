"""Bad phrase patterns."""

# Wordy phrases with direct replacements (V009)
WORDY_PHRASE_REPLACEMENTS = {
    "at this point in time": "now",
    "due to the fact that": "because",
    "during the course of": "during",
    "enable the ability to": "allow",
    "enables the ability to": "allows",
    "has the ability to": "can",
    "have the ability to": "can",
    "in close proximity to": "near",
    "in order to": "to",
    "in the event that": "if",
    "on the basis of": "based on",
    "with regard to": "about",
}

# Fixed redundant pairs with unambiguous deletions (V010)
REDUNDANT_PAIR_REPLACEMENTS = {
    "each and every": "each",
    "merge together": "merge",
    "merged together": "merged",
    "merges together": "merges",
    "merging together": "merging",
    "past history": "history",
    "repeat again": "repeat",
    "repeated again": "repeated",
    "repeating again": "repeating",
    "repeats again": "repeats",
    "revert back": "revert",
    "reverted back": "reverted",
    "reverting back": "reverting",
    "reverts back": "reverts",
}

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
    # Pedagogical/dive-in phrases (tropes.fyi)
    "Let's break this down",
    "Let's unpack this",
    "Let's explore this",
    "Let's dive in",
    "Let's dive into",
    # Business politeness fog (business writing tropes)
    "just circling back",
    "circling back on",
    "wanted to touch base",
    "just wanted to check in",
    "per our last conversation",
    "as per our discussion",
    "in case you had any thoughts",
    "just following up",
    "just a gentle reminder",
    "just a friendly reminder",
]

# Knowledge cutoff patterns (V003)
KNOWLEDGE_CUTOFF_PATTERNS = [
    r"as of my (last |knowledge )?(?:update|cutoff|training)",
    r"based on (my |available )?information",
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
    # Grandiose stakes (tropes.fyi)
    "fundamentally reshape",
    "define the next era",
    "something entirely new",
    "entirely new paradigm",
    "will reshape how we",
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
    # Anonymous source patterns
    r"sources close to",
    r"a person familiar with the matter",
    r"officials speaking on condition of anonymity",
    r"people briefed on the matter",
    # Strategic vagueness (business writing tropes)
    r"explore opportunities to",
    r"enhance (?:operational |)efficiency",
    r"at the end of the day",
    r"\bgoing forward\b",
    r"\bmoving forward\b",
]

# Patronizing analogy phrases (G005/G006)
PATRONIZING_ANALOGY_PHRASES = [
    "think of it as",
    "think of it like",
    "imagine a world where",
    "imagine a future where",
    "imagine a scenario where",
]

# Signposted conclusion phrases (S014)
SIGNPOSTED_CONCLUSION_PHRASES = [
    "in conclusion",
    "to sum up",
    "as we've seen",
    "as we have seen",
    "in closing",
]

# False suspense transition phrases (G004)
FALSE_SUSPENSE_PHRASES = [
    "here's the kicker",
    "here's the thing",
    "here's where it gets interesting",
    "here's what most people miss",
    "here's the catch",
    "here's the twist",
]

# False vulnerability phrases (G007)
FALSE_VULNERABILITY_PHRASES = [
    r"and yes,? since we're being honest",
    r"this is not a rant",
    r"i'll be (the first to admit|honest)",
    r"if i'm being honest",
    r"let me be (frank|honest|candid|real)",
]

# Asserted simplicity phrases (G008)
ASSERTED_SIMPLICITY_PHRASES = [
    r"the (reality|truth|answer) is (simpler|simple|clear|obvious)",
    r"history is (clear|unambiguous)",
    r"the (metrics|evidence|examples|data) (are|is) clear",
    r"\bthe truth is\b",
    r"put simply",
    r"it('s| is) (really )?that simple",
]

# Futurist invitation phrases (G006)
FUTURIST_INVITATION_PHRASES = [
    "imagine a world where",
    "imagine a future where",
    "in that world,",
    "picture a world where",
]

# Pedagogical voice phrases (G009)
PEDAGOGICAL_VOICE_PHRASES = [
    "let's break this down",
    "let's unpack this",
    "let's unpack what",
    "let's explore this",
    "let's explore what",
    "let's dive in",
    "let's dive into",
    "let's take a closer look",
    "let's step back",
]

# Fractal summary phrases (S015)
FRACTAL_SUMMARY_PHRASES = [
    r"in this section,? we('ll| will) (explore|examine|look at|discuss|cover)",
    r"as we('ve| have) seen in this section",
    r"as we('ve| have) discussed",
    r"and so we return to where we began",
    r"as (we )?noted (earlier|above|at the (start|beginning))",
]

# Grandiose stakes phrases (V006)
GRANDIOSE_STAKES_PHRASES = [
    r"fundamentally reshape",
    r"will (define|shape|determine) the next (era|decade|generation)",
    r"something entirely new",
    r"entirely new paradigm",
    r"will reshape how we",
    r"the most important.{1,30}(ever|in history|of our time)",
    r"will change everything",
]

# Inflammatory cliché phrases (V004 sub-category)
INFLAMMATORY_CLICHE_PHRASES = [
    "sparked a firestorm",
    "triggered widespread outrage",
    "storm of criticism",
    "sparked backlash",
]

# Gap ritual phrases (G013)
GAP_RITUAL_PHRASES = [
    r"the literature has overlooked",
    r"few scholars have (?:examined|explored|addressed|investigated)",
    r"this (?:study|paper|research|article) fills (?:that|the|a) gap",
    r"has received little (?:attention|scrutiny|scholarly attention)",
    r"remains (?:under-explored|underexplored|understudied|under-researched)",
    r"a gap in the (?:literature|research|scholarship|existing research)",
    r"no study has (?:yet )?(?:examined|explored|addressed|investigated)",
    r"(?:an|the) (?:under-explored|underexplored|understudied) (?:area|topic|field)",
    r"this gap in (?:the|our) (?:understanding|knowledge|literature)",
]

# Trend overclaim phrases (V008)
TREND_OVERCLAIM_PHRASES = [
    r"more and more people",
    r"a growing number of",
    r"the latest trend sweeping",
    r"increasingly popular",
    r"everyone is talking about",
]

# False balance phrases (G010)
FALSE_BALANCE_PHRASES = [
    r"supporters say .* critics say",
    r"the truth (likely )?lies somewhere in the middle",
    r"both sides of the debate",
    r"on the other hand, opponents argue",
]

# Corporate euphemism phrases (S019)
CORPORATE_EUPHEMISM_PHRASES = [
    "restructuring",
    "right-sizing",
    "rightsizing",
    "resource optimization",
    "streamlining operations",
    "workforce reduction",
    "headcount reduction",
    "exploring strategic alternatives",
    "transitioning out",
    "realignment",
    "sunsetting",
    "sunset the",
    "sunsetted",
]

# Alignment ritual phrases (S020)
ALIGNMENT_RITUAL_PHRASES = [
    r"fully aligned on",
    r"aligned on the (?:strategic |)direction",
    r"on the same page",
    r"in lockstep",
    r"moving in the same direction",
    r"aligned around",
    r"shared understanding",
    r"cross-functional alignment",
]

# Impersonal corporate passive patterns (G014)
IMPERSONAL_CORPORATE_PASSIVE_PHRASES = [
    r"\b[Ii]t has been (?:determined|decided|agreed|established|noted)\b",
    r"\b[Aa]djustments (?:will be|are being|have been) made\b",
    r"\b[Cc]hanges (?:will be|are being|have been) (?:implemented|made|introduced)\b",
    r"\b[Aa] decision (?:has been|was) (?:made|reached|taken)\b",
    r"\b[Ss]teps (?:will be|are being|have been) taken\b",
]
