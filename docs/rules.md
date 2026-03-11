# Rule Reference

This document describes all detection rules available in slop-lint.

---

## Vocabulary Rules (V)

### V001: Overused Vocabulary

Detects overused and clichéd words that weaken writing.

**Severity:** Warning  
**Fixable:** Yes

**Detected words:**
- delve, tapestry, multifaceted, intricate, underscore
- showcase, foster, garner, pivotal, testament
- interplay, vibrant, nuanced, embark, realm
- unveil, streamline, landscape, paradigm, synergy
- leverage, elevate, spearhead

**Example (bad):**
```markdown
This article delves into the intricate tapestry of modern software architecture.
```

**Example (good):**
```markdown
This article explores the complex structure of modern software architecture.
```

---

### V002: Collaborative Phrases

Detects chat-like communication patterns that don't belong in documentation.

**Severity:** Warning  
**Fixable:** No

**Detected patterns:**
- "I hope this helps!"
- "Let me know if..."
- "Certainly!"
- "Absolutely!"
- "Great question!"
- "Feel free to..."

**Example (bad):**
```markdown
Here's the code you requested. I hope this helps! Let me know if you need anything else.
```

**Example (good):**
```markdown
Here's the code for the requested feature.
```

---

### V003: Knowledge Cutoff

Detects temporal disclaimers about training data.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "As of my last update..."
- "Based on available information..."
- "At the time of writing..."
- "As of [date]..."

**Example (bad):**
```markdown
As of my last update, Python 3.12 was the latest version.
```

**Example (good):**
```markdown
Python 3.12 is the latest version (as of January 2024).
```

---

### V004: Promotional Language

Detects puffery and marketing speak.

**Severity:** Warning  
**Fixable:** No

**Detected patterns:**
- "world-class", "cutting-edge", "groundbreaking"
- "boasts a", "nestled in", "in the heart of"
- "renowned", "prestigious", "unparalleled"

**Example (bad):**
```markdown
Our groundbreaking solution boasts world-class performance.
```

**Example (good):**
```markdown
Our solution provides high performance for typical workloads.
```

---

### V005: Weasel Words

Detects vague attributions without sources.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "Experts say...", "Studies show..."
- "It is widely believed...", "Many argue..."
- "Industry reports suggest..."

**Example (bad):**
```markdown
Experts argue that this approach is best.
```

**Example (good):**
```markdown
Martin Fowler recommends this approach in "Refactoring" (2018).
```

---

## Structural Rules (S)

### S001: Rule of Three

Detects excessive triadic patterns ("X, Y, and Z").

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
This provides speed, efficiency, and reliability.
It offers flexibility, scalability, and maintainability.
The system ensures security, stability, and performance.
```

**Example (good):**
```markdown
This provides fast and reliable performance.
The system is designed for security and horizontal scaling.
```

---

### S002: Negative Parallelism

Detects "Not only... but also..." constructions.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
It's not just about the code, it's about the people.
Not only does it improve speed, but it also enhances reliability.
```

**Example (good):**
```markdown
Both the code and the team matter.
It improves both speed and reliability.
```

---

### S003: Challenge Conclusions

Detects formulaic "despite X, faces challenges" patterns.

**Severity:** Warning  
**Fixable:** No

**Example (bad):**
```markdown
Despite its popularity, the framework faces several challenges.
```

**Example (good):**
```markdown
The framework has some known limitations: performance degrades with large datasets.
```

---

### S004: Inline-Header Lists

Detects "- **Header:** Description" bullet patterns.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
- **Performance:** Very fast execution
- **Scalability:** Handles millions of requests
- **Security:** Enterprise-grade protection
```

**Example (good):**
```markdown
## Performance
Very fast execution under typical loads.

## Scalability
Handles millions of requests per second.
```

---

### S005: Significance Emphasis

Detects undue importance claims.

**Severity:** Warning  
**Fixable:** No

**Detected patterns:**
- "pivotal moment", "key turning point"
- "marks a significant", "reflects broader trends"

**Example (bad):**
```markdown
This release marks a pivotal moment in the project's history.
```

**Example (good):**
```markdown
This release adds async support and improves memory usage by 40%.
```

---

### S006: Superficial Analysis

Detects present participle chains suggesting filler text.

**Severity:** Warning  
**Fixable:** No

**Detected patterns:**
- "highlighting its importance"
- "underscoring the significance"
- "fostering growth and development"

**Example (bad):**
```markdown
The update improves performance, highlighting its importance to users.
```

**Example (good):**
```markdown
The update reduces API latency by 30%.
```

---

### S007: False Ranges

Detects "from X to Y" with incoherent extremes.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
Used by everyone from beginners to seasoned professionals.
```

**Example (good):**
```markdown
Suitable for both new and experienced developers.
```

---

## Style Rules (T)

### T001: Title Case Headings

Detects improper capitalization in Markdown headings.

**Severity:** Info  
**Fixable:** Yes

**Example (bad):**
```markdown
## Getting Started With The Project
```

**Example (good):**
```markdown
## Getting started with the project
```

---

### T002: Bold Overuse

Detects excessive **bold** usage per paragraph.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
The **quick** brown **fox** jumps over the **lazy** dog.
```

**Example (good):**
```markdown
The quick brown fox jumps over the lazy dog.
```

---

### T003: Em Dash Overuse

Detects excessive em dashes (—) for dramatic effect.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
The solution—which took months to develop—was finally ready—and it worked.
```

**Example (good):**
```markdown
The solution, which took months to develop, was finally ready and worked.
```

---

### T004: Quote Inconsistency

Detects mixed curly and straight quote styles.

**Severity:** Info  
**Fixable:** Yes

**Example (bad):**
```markdown
He said "hello" and she replied "goodbye".
```

**Example (good):**
```markdown
He said "hello" and she replied "goodbye".
```

---

### T005: Emoji in Prose

Detects non-technical emoji in documentation.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
## Getting Started 🚀

This guide will help you ✨ build amazing things! 📌
```

**Example (good):**
```markdown
## Getting Started

This guide covers installation and basic usage.
```

---

### T006: Elegant Variation

Detects unnatural synonyms to avoid repetition.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
The function returns a value. The method yields a result.
The procedure produces an output.
```

**Example (good):**
```markdown
The function returns a value. See the function reference for details.
```

---

## Grammar Rules (G)

### G001: Copula Avoidance

Detects "serves as" instead of simpler "is".

**Severity:** Info  
**Fixable:** Yes

**Detected patterns:**
- "serves as", "stands as", "acts as"
- "functions as", "operates as"

**Example (bad):**
```markdown
This module serves as the main entry point.
```

**Example (good):**
```markdown
This module is the main entry point.
```

---

### G002: Excessive Hedging

Detects over-qualification phrases and hedge stacking (multiple hedges in one sentence).

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "It is important to note that..."
- "It's worth mentioning that..."
- "It should be noted that..."
- Hedge stacking: 2+ hedges (may, might, potentially, arguably, possibly, perhaps, appears to, suggests that, could be) in one sentence

**Example (bad):**
```markdown
It is important to note that the function may throw an exception.
```

**Example (good):**
```markdown
The function may throw an exception.
```

---

### G003: Participle Chains

Detects dangling modifier chains.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
Leveraging modern techniques, enhancing performance, the system delivers results.
```

**Example (good):**
```markdown
The system uses modern techniques to deliver fast results.
```

---

## Code Rules (C)

### C001: Docstring Vocabulary

Detects overused vocabulary in Python docstrings.

**Severity:** Warning  
**Fixable:** Yes

**Example (bad):**
```python
def process(data):
    """Delve into the data and leverage its intricate structure."""
    pass
```

**Example (good):**
```python
def process(data):
    """Parse the data and extract structured fields."""
    pass
```

---

### C002: Verbose Comments

Detects over-explained code comments.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```python
# This function is designed to calculate the sum of two numbers,
# which is a fundamental operation in mathematics that adds
# the first number to the second number
def add(a, b):
    return a + b
```

**Example (good):**
```python
def add(a, b):
    """Return the sum of a and b."""
    return a + b
```

---

### C003: Collaborative Comments

Detects chat phrases in code comments.

**Severity:** Warning  
**Fixable:** No

**Example (bad):**
```python
# I hope this helps! Let me know if you need anything else.
def helper():
    pass
```

**Example (good):**
```python
def helper():
    """Helper function for data processing."""
    pass
```

---

### C004: Formulaic Placeholders

Detects formulaic TODO patterns.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```python
# TODO: Implement this function as per the requirements
# TODO: Add error handling as needed
```

**Example (good):**
```python
# TODO: Add retry logic for network failures (issue #42)
```

---

## Markup Rules (M)

### M001: Wrong Markup

Detects Markdown syntax in wrong context.

**Severity:** Warning  
**Fixable:** No

**Example (bad):**
```python
# **Important**: This is not how to use Markdown in Python
```

**Example (good):**
```python
# Important: This is a plain comment
```

---

### M002: ChatGPT Markers

Detects ChatGPT reference artifacts.

**Severity:** Error  
**Fixable:** Yes

**Detected patterns:**
- `turn0search0`, `turn1search2`
- `oai_citation`
- `contentReference`

**Example (bad):**
```markdown
According to recent studies [turn0search0], the approach works.
```

**Example (good):**
```markdown
According to Smith et al. (2023), the approach works.
```

---

### M003: UTM Parameters

Detects tracking parameters in URLs that should be stripped.

**Severity:** Warning  
**Fixable:** Yes

**Detected patterns:**
- `utm_source=chatgpt.com`
- `utm_source=openai`

**Example (bad):**
```markdown
See [documentation](https://example.com?utm_source=chatgpt.com)
```

**Example (good):**
```markdown
See [documentation](https://example.com)
```

---

### M004: Broken References

Detects invalid or broken citation formats.

**Severity:** Error  
**Fixable:** No

**Detected patterns:**
- `[attached_file:1]`
- `grok_card`
- `[source: ...]`

**Example (bad):**
```markdown
See the attached document [attached_file:1] for details.
```

**Example (good):**
```markdown
See `docs/architecture.md` for details.
```

---

## Phase 10: AI Writing Tropes Rules

The following rules were added based on the
[AI Writing Tropes to Avoid](https://tropes.fyi) catalogue.

---

### V006: Grandiose Stakes

Detects inflated importance claims that overstate significance.

**Severity:** Warning  
**Fixable:** No

**Detected patterns:**
- "fundamentally reshape", "define the next era"
- "entirely new paradigm", "change everything"
- "unprecedented opportunity", "reshape the future"

**Example (bad):**
```markdown
AI will fundamentally reshape how society functions.
```

**Example (good):**
```markdown
AI is changing several industries, particularly customer service and logistics.
```

---

### V007: Invented Concept Labels

Detects compound pseudo-analytical labels ("the X paradox", "the Y trap")
when 2+ appear in the same document.

**Severity:** Info  
**Fixable:** No

**Detected suffixes:** paradox, trap, creep, divide, vacuum, inversion,
deficit, gap, spiral, dilemma

**Example (bad):**
```markdown
This creates the automation paradox. Teams also face the innovation trap.
Meanwhile, the complexity creep threatens progress.
```

**Example (good):**
```markdown
Automating too aggressively can backfire when teams lose the skills to
intervene manually.
```

---

### S008: Dramatic Countdown

Detects "Not X. Not Y. Just/But Z." dramatic negation patterns.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
Not faster hardware. Not better algorithms. Just cleaner data.
```

**Example (good):**
```markdown
The improvement came from cleaning the data, not from hardware or algorithms.
```

---

### S009: Rhetorical Self-Answer

Detects "The X? A Y." patterns where a question is immediately answered
with a short fragment.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
The result? A complete transformation of the industry.
```

**Example (good):**
```markdown
The result was a measurable improvement in delivery times.
```

---

### S010: Anaphora Abuse

Detects 3+ consecutive sentences starting with the same word.

**Severity:** Warning  
**Fixable:** No  
**Configurable:** `threshold` (default: 3)

**Example (bad):**
```markdown
Every team needs this. Every manager should know this. Every company benefits.
```

**Example (good):**
```markdown
Teams, managers, and companies all benefit from this approach.
```

---

### S011: Gerund Fragment Litany

Detects 3+ consecutive gerund-phrase fragments used for rhythmic effect.

**Severity:** Info  
**Fixable:** No  
**Configurable:** `threshold` (default: 3)

**Example (bad):**
```markdown
Building faster. Shipping sooner. Iterating constantly.
```

**Example (good):**
```markdown
The team focused on faster builds, shorter ship cycles, and constant iteration.
```

---

### S012: Listicle in Prose

Detects ordinal progressions ("The first… The second… The third…")
disguised as continuous prose.

**Severity:** Info  
**Fixable:** No

**Example (bad):**
```markdown
The first reason is cost. The second reason is speed.
The third reason is reliability.
```

**Example (good):**
```markdown
The main reasons are cost, speed, and reliability.
```

---

### S013: Historical Analogy Stacking

Detects 3+ tech company/product name-drops in rapid succession.

**Severity:** Info  
**Fixable:** No  
**Configurable:** `threshold` (default: 3)

**Example (bad):**
```markdown
Like Google, Amazon, and Netflix before them, these companies
are following the path blazed by Apple and Microsoft.
```

**Example (good):**
```markdown
Several large tech companies have adopted this pattern.
```

---

### S014: Signposted Conclusion

Detects formulaic conclusion markers.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "In conclusion", "To sum up", "As we've seen"
- "The bottom line is", "At the end of the day"

**Example (bad):**
```markdown
In conclusion, the framework provides significant benefits.
```

**Example (good):**
```markdown
The framework reduces build times by 40% and eliminates flaky tests.
```

---

### S015: Fractal Summary

Detects "In this section, we'll explore" / "As we've seen in this
section" intro/outro framing.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "in this section, we'll explore"
- "as we've seen in this section"
- "this section will cover"
- "let's now turn to"

**Example (bad):**
```markdown
In this section, we'll explore how caching improves performance.
```

**Example (good):**
```markdown
Caching improves performance by reducing database round-trips.
```

---

### S016: Content Duplication

Detects repeated paragraphs within the same document using hash-based
comparison.

**Severity:** Warning  
**Fixable:** No

**Example (bad):**
```markdown
The system processes data in real time for immediate insights.

[several paragraphs later]

The system processes data in real time for immediate insights.
```

**Example (good):**
```markdown
State each idea once. Refer back with cross-references if needed.
```

---

### G004: False Suspense Transition

Detects manufactured dramatic tension in transitions.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "Here's the thing", "Here's the kicker"
- "Here's where it gets interesting"
- "Here's what most people miss"
- "But here's the catch"

**Example (bad):**
```markdown
Here's the thing: most teams don't need microservices.
```

**Example (good):**
```markdown
Most teams don't need microservices.
```

---

### G005: Patronizing Analogy

Detects condescending "think of it as" explanatory patterns.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "Think of it as", "Think of it like"
- "Imagine a world where", "Imagine a future where"
- "Picture this"

**Example (bad):**
```markdown
Think of it as a digital librarian that organizes your data.
```

**Example (good):**
```markdown
The service indexes and organizes data automatically.
```

---

### G006: Futurist Invitation

Detects speculative "imagine a world" framing.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "Imagine a world where"
- "In that world"
- "What if you could"
- "Imagine a future where"

**Example (bad):**
```markdown
Imagine a world where deployments never fail.
```

**Example (good):**
```markdown
Zero-downtime deployments are achievable with blue-green strategies.
```

---

### G007: False Vulnerability

Detects performative honesty or faux-candid phrasing.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "I'll be honest", "if I'm being honest"
- "since we're being honest", "this is not a rant"
- "can we be real for a moment"

**Example (bad):**
```markdown
I'll be honest: most startups fail because of bad hiring.
```

**Example (good):**
```markdown
Most startups fail because of bad hiring.
```

---

### G008: Asserted Simplicity

Detects claims of simplicity that mask complexity or assert authority.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "The reality is simpler", "The truth is"
- "History is clear", "The answer is simple"
- "It really comes down to"

**Example (bad):**
```markdown
The reality is simpler than you think.
```

**Example (good):**
```markdown
The main factor is cache hit rate, which accounts for 80% of latency reduction.
```

---

### G009: Pedagogical Voice

Detects overly instructional "let's explore" tone.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "Let's break this down", "Let's unpack this"
- "Let's explore this", "Let's dive in"
- "Let's take a closer look", "Let's examine"

**Example (bad):**
```markdown
Let's break this down. First, we need to understand the basics.
```

**Example (good):**
```markdown
The system has three components: ingestion, processing, and storage.
```

---

### T007: Short Punchy Fragments

Detects 3+ consecutive very short paragraphs (≤ 5 words each) used for
manufactured dramatic emphasis.

**Severity:** Info  
**Fixable:** No  
**Configurable:** `threshold` (default: 3)

**Example (bad):**
```markdown
It worked.

Every single time.

Without fail.

No exceptions.
```

**Example (good):**
```markdown
It worked every single time without exception.
```

---

### T008: Sentence Length

Detects excessively long sentences that exceed a word count threshold.

**Severity:** Info  
**Fixable:** No  
**Configurable:** `sentence_length_max` (default: 40)

**Example (bad):**
```markdown
In considering the implications of the findings which themselves arise from a complex interaction of factors that are not easily reducible to simple causal explanations we must also consider the broader context in which these results were obtained and the various methodological limitations that constrain our interpretations.
```

**Example (good):**
```markdown
The findings arise from a complex interaction of factors. We must also consider the broader context and the methodological limitations that constrain our interpretations.
```

---

## Phase 1: Low-Quality Journalism Tropes Rules

The following rules detect common low-quality journalism patterns.

---

### V008: Trend Overclaim

Detects unsubstantiated trend claims without evidence.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "more and more people", "a growing number of"
- "the latest trend sweeping", "increasingly popular"
- "everyone is talking about"

**Example (bad):**
```markdown
More and more people are switching to this framework.
```

**Example (good):**
```markdown
According to the 2025 Stack Overflow survey, 34% of respondents use this framework, up from 21% in 2024.
```

---

### G010: False Balance

Detects false-balance framing that presents opposing views as equally
valid without evidence.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "Supporters say X. Critics say Y."
- "the truth lies somewhere in the middle"
- "both sides of the debate"
- "on the other hand, opponents argue"

**Example (bad):**
```markdown
Supporters say it will create jobs, but critics say it will destroy them.
The truth likely lies somewhere in the middle.
```

**Example (good):**
```markdown
The Bureau of Labor Statistics projects a net gain of 12,000 jobs in the sector by 2028, though some roles will be displaced.
```

---

### G011: Nominalization Overload

Detects overuse of "the [nominalization] of" constructions that make prose
unnecessarily abstract.

**Severity:** Info  
**Fixable:** No  
**Configurable:** `nominalization_overload` (default: 3)

**Detected patterns:**
- "the implementation of", "the utilization of"
- "the identification of", "the examination of"
- "the establishment of", "the facilitation of"
- "the conceptualization of", "the operationalization of"

**Example (bad):**
```markdown
The implementation of the analysis led to the identification of patterns. The examination of the data confirmed the establishment of a baseline.
```

**Example (good):**
```markdown
We analyzed the data, identified patterns, and confirmed a baseline.
```

---

### G012: Passive Voice Overuse

Detects overuse of formulaic academic passive constructions.

**Severity:** Info  
**Fixable:** No  
**Configurable:** `passive_voice_overuse` (default: 5)

**Detected patterns:**
- "It is/was/has been suggested/argued/noted that..."
- "It can/could/may be argued/suggested that..."
- "is/are/was/were considered/regarded/viewed/seen as/to be"

**Example (bad):**
```markdown
It is suggested that the results indicate a trend. It was found that the method performs well. It has been shown that this approach works. It could be argued that alternatives exist. It should be noted that limitations apply.
```

**Example (good):**
```markdown
The results indicate a trend. The method performs well, and this approach works. However, alternatives exist and limitations apply.
```

---

### G013: Gap Ritual

Detects formulaic "gap in the literature" phrases common in academic writing.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "the literature has overlooked"
- "few scholars have examined/explored/addressed"
- "this study fills that/the gap"
- "has received little attention"
- "remains under-explored/understudied"
- "a gap in the literature/research"

**Example (bad):**
```markdown
Few scholars have examined this intersection. This study fills that gap by exploring the overlooked variables.
```

**Example (good):**
```markdown
Prior work by Smith (2020) and Jones (2021) examined related aspects, but did not address variable X. We extend their analysis to include X.
```

---

### S017: Anecdote As Evidence

Detects single-anecdote openings used as evidence for broad claims.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "For [Name] of [Location], the…"
- "Take [Name], a [descriptor]…"
- "Meet [Name]"

**Example (bad):**
```markdown
For Sarah of Ohio, the new policy meant losing her healthcare.
Meet David, a software engineer who quit his job to start a company.
```

**Example (good):**
```markdown
A 2024 Kaiser Family Foundation survey found that 12% of respondents in Ohio lost coverage after the policy change.
```

---

### S018: Citation Name-Dropping

Detects 3+ consecutive "Author (Year) verb" sentences that list citations
without synthesizing them.

**Severity:** Info  
**Fixable:** No  
**Configurable:** `citation_name_drop` (default: 3)

**Detected patterns:**
- "Smith (2012) argues that..."
- "Jones (2014) claims that..."
- "Patel (2018) suggests that..."

**Example (bad):**
```markdown
Smith (2012) argues that technology reshapes communities. Jones (2014) claims that digital tools empower users. Patel (2018) suggests that platforms mediate interactions. Lee (2020) finds that algorithms reinforce bias.
```

**Example (good):**
```markdown
Several scholars have examined the impact of technology on communities. Smith (2012) and Jones (2014) both argue that digital tools reshape and empower communities, while Patel (2018) emphasizes the mediating role of platforms.
```

---

### S019: Corporate Euphemism

Detects corporate euphemisms that obscure plain meaning — language designed
to soften layoffs, budget cuts, or organisational failure.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "restructuring", "right-sizing", "resource optimization"
- "headcount reduction", "workforce adjustment"
- "sunsetting", "deprioritizing"
- "strategic pivot", "rationalization"

**Example (bad):**
```markdown
The company is undergoing a strategic restructuring and right-sizing initiative.
```

**Example (good):**
```markdown
The company is laying off 300 employees and closing two offices.
```

---

### S020: Alignment Ritual

Detects phrases that signal performative consensus-seeking rather than
substantive agreement.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "fully aligned on", "on the same page"
- "cross-functional alignment", "align on next steps"
- "ensure alignment", "get buy-in"

**Example (bad):**
```markdown
We need to ensure cross-functional alignment and get buy-in from all stakeholders before we can move forward.
```

**Example (good):**
```markdown
We need the marketing and engineering teams to agree on the launch date before we proceed.
```

---

### S021: Slide Deck Fragment

Detects verbless, buzzword-heavy fragments that read like bullet points
from a slide deck rather than prose.

**Severity:** Info  
**Fixable:** No  
**Confidence:** Low

**Detected patterns:**
Lines that contain 2+ buzzwords (alignment, synergy, strategic, impact,
scalable, etc.) plus lack a conjugated main verb.

**Example (bad):**
```markdown
Driving alignment across strategic initiatives for scalable impact.
```

**Example (good):**
```markdown
The team will coordinate across three initiatives to improve scalability.
```

---

### G014: Impersonal Corporate Passive

Detects impersonal passive constructions that erase the actor, creating a
sense of corporate inevitability where no one is responsible.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "It has been determined that…"
- "A decision has been made…"
- "Steps will be taken…"
- "Changes will be implemented…"
- "Adjustments will be made…"

**Example (bad):**
```markdown
It has been determined that adjustments will be made to the compensation structure.
```

**Example (good):**
```markdown
The finance team decided to reduce bonuses by 10% starting in Q3.
```
