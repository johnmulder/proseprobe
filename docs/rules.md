# Rule Reference

This document describes all detection rules available in ProseProbe.

Most prose-scoped `V`, `S`, `T`, and `G` rules inspect Markdown prose and
source-mapped Python docstrings and comments; `G015` examines only Markdown
document openers. `C` rules handle Python-specific documentation issues.
`M001` checks Markdown syntax in Python comments, while `M002`-`M008` and
`M010` are Markdown-only.

Wrapped Markdown and Python prose is segmented into cached, source-mapped
sentences. Records retain exact start and end positions while conservative
standard-library handling preserves common abbreviations, decimals, URLs,
trailing quotes, and hard prose-block boundaries without an NLP dependency.

## Rule Inventory

This inventory is generated from rule classes and the registry. Update the
implementation metadata, then run `make rule-docs`; do not edit the marked
block by hand. The examples and guidance below remain hand-maintained.

<!-- rule-docs:inventory:start -->

| ID | Name | Category | Severity | Confidence | Context | Configuration |
|----|------|----------|----------|------------|---------|---------------|
| `V001` | Overused Vocabulary | Vocabulary | warning | medium | markdown, python / prose | — |
| `V002` | Collaborative Phrases | Vocabulary | warning | medium | markdown, python / prose | — |
| `V003` | Knowledge Cutoff | Vocabulary | info | medium | markdown, python / prose | — |
| `V004` | Promotional Language | Vocabulary | warning | medium | markdown, python / prose | — |
| `V005` | Weasel Words | Vocabulary | info | medium | markdown, python / prose | — |
| `V006` | Grandiose Stakes | Vocabulary | warning | medium | markdown, python / prose | — |
| `V007` | Invented Concept Labels | Vocabulary | info | medium | markdown, python / prose | `thresholds.invented_concept_labels` |
| `V008` | Trend Overclaim | Vocabulary | info | medium | markdown, python / prose | — |
| `S001` | Rule of Three | Structure | info | medium | markdown, python / prose | `thresholds.rule_of_three` |
| `S002` | Negative Parallelism | Structure | info | medium | markdown, python / prose | — |
| `S003` | Challenge Conclusions | Structure | warning | medium | markdown, python / prose | — |
| `S004` | Inline-Header Lists | Structure | info | medium | markdown / non_code | `thresholds.inline_header_lists` |
| `S005` | Significance Emphasis | Structure | warning | medium | markdown, python / prose | — |
| `S006` | Superficial Analysis | Structure | warning | medium | markdown, python / prose | — |
| `S007` | False Ranges | Structure | info | medium | markdown, python / prose | — |
| `S008` | Dramatic Countdown | Structure | info | medium | markdown, python / prose | — |
| `S009` | Rhetorical Self-Answer | Structure | info | medium | markdown, python / prose | — |
| `S010` | Anaphora Abuse | Structure | warning | medium | markdown, python / prose | `thresholds.anaphora_abuse` |
| `S011` | Gerund Fragment Litany | Structure | info | medium | markdown, python / prose | `thresholds.gerund_fragment_litany` |
| `S012` | Listicle in Prose | Structure | info | medium | markdown, python / prose | — |
| `S013` | Historical Analogy Stacking | Structure | info | medium | markdown, python / prose | `thresholds.historical_analogy_stacking` |
| `S014` | Signposted Conclusion | Structure | info | medium | markdown, python / prose | — |
| `S015` | Fractal Summary | Structure | info | medium | markdown, python / prose | — |
| `S016` | Content Duplication | Structure | warning | medium | markdown / raw | — |
| `S017` | Anecdote As Evidence | Structure | info | medium | markdown, python / prose | — |
| `S018` | Citation Name-Dropping | Structure | info | medium | markdown, python / prose | `thresholds.citation_name_drop` |
| `S019` | Corporate Euphemism | Structure | info | medium | markdown, python / prose | — |
| `S020` | Alignment Ritual | Structure | info | medium | markdown, python / prose | — |
| `S021` | Slide Deck Fragment | Structure | info | low | markdown, python / prose | — |
| `T001` | Title Case Headings | Style | info | medium | markdown / raw | — |
| `T002` | Bold Overuse | Style | info | medium | markdown / raw | `thresholds.bold_overuse` |
| `T003` | Em Dash Overuse | Style | info | medium | markdown, python / prose | `thresholds.em_dash_overuse` |
| `T004` | Quote Inconsistency | Style | info | medium | markdown, python / prose | — |
| `T005` | Emoji in Prose | Style | info | medium | markdown, python / prose | — |
| `T006` | Elegant Variation | Style | info | medium | markdown, python / prose | — |
| `T007` | Short Punchy Fragments | Style | info | medium | markdown, python / prose | `thresholds.short_punchy_fragments` |
| `T008` | Sentence Length | Style | info | medium | markdown, python / prose | `thresholds.sentence_length_max` |
| `G001` | Copula Avoidance | Grammar | info | medium | markdown, python / prose | — |
| `G002` | Excessive Hedging | Grammar | info | medium | markdown, python / prose | — |
| `G003` | Participle Chains | Grammar | warning | medium | markdown, python / prose | — |
| `G004` | False Suspense Transition | Grammar | info | medium | markdown, python / prose | — |
| `G005` | Patronizing Analogy | Grammar | info | medium | markdown, python / prose | — |
| `G006` | Futurist Invitation | Grammar | info | medium | markdown, python / prose | — |
| `G007` | False Vulnerability | Grammar | info | medium | markdown, python / prose | — |
| `G008` | Asserted Simplicity | Grammar | info | medium | markdown, python / prose | — |
| `G009` | Pedagogical Voice | Grammar | info | medium | markdown, python / prose | — |
| `G010` | False Balance | Grammar | info | medium | markdown, python / prose | — |
| `G011` | Nominalization Overload | Grammar | info | medium | markdown, python / prose | `thresholds.nominalization_overload` |
| `G012` | Passive Voice Overuse | Grammar | info | medium | markdown, python / prose | `thresholds.passive_voice_overuse` |
| `G013` | Gap Ritual | Grammar | info | medium | markdown, python / prose | — |
| `G014` | Impersonal Corporate Passive | Grammar | info | medium | markdown, python / prose | — |
| `G015` | Generic Scene-Setting Opener | Grammar | info | medium | markdown / prose | — |
| `C001` | Docstring-Only Vocabulary | Code | warning | medium | python / raw | — |
| `C002` | Verbose Comments | Code | info | medium | python / raw | — |
| `C003` | Collaborative Comments | Code | warning | medium | python / raw | — |
| `C004` | Formulaic Placeholders | Code | info | medium | python / raw | — |
| `M001` | Wrong Markup | Markup | warning | low | python / raw | — |
| `M002` | ChatGPT Markers | Markup | error | medium | markdown / prose | — |
| `M003` | UTM Parameters | Markup | warning | medium | markdown / raw | — |
| `M004` | Broken References | Markup | error | medium | markdown / prose | — |
| `M005` | Unresolved Markdown References | Markup | error | high | markdown / non_code | — |
| `M006` | Template Residue | Markup | warning | high | markdown / prose | — |
| `M007` | Unclosed Code Fence | Markup | error | high | markdown / raw | — |
| `M008` | Skipped Heading Level | Markup | warning | high | markdown / raw | — |
| `M010` | Non-Descriptive Link Text | Markup | warning | high | markdown / non_code | — |

<!-- rule-docs:inventory:end -->

---

## Vocabulary Rules (V)

### V001: Overused Vocabulary

Detects overused and clichéd words that weaken writing.

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

Detects model-qualified temporal disclaimers about training data or access.
Ordinary dated release and publication statements do not count.

**Detected patterns:**
- "As of my last update/training/cutoff…"
- "Based on my/available information…"
- "My training data only goes/extends/covers…"
- Statements that model knowledge is limited or real-time/web access is unavailable

**Example (bad):**
```markdown
As of my last update, Python 3.12 was the latest version.
```

**Example (good):**
```markdown
As of August 2026, version 1.4.0 is the supported release.
```

---

### V004: Promotional Language

Detects puffery and marketing speak.

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

A match becomes low confidence when its sentence or one adjacent sentence in
the same prose block supplies a named source, date, link, percentage, or
comparative figures.

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

**Example (bad):**
```markdown
This provides speed, efficiency, and reliability.
It offers flexibility, scalability, and maintainability.
The system ensures security, stability, and performance.
The API supports retries, timeouts, and cancellation.
```

**Example (good):**
```markdown
This provides fast and reliable performance.
The system is designed for security and horizontal scaling.
```

---

### S002: Negative Parallelism

Detects "Not only... but also..." constructions.

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

Detects "- **Header**: Description" bullet patterns.

**Example (bad):**
```markdown
- **Performance**: Very fast execution
- **Scalability**: Handles millions of requests
- **Security**: Enterprise-grade protection
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

**Detected patterns:**
- `highlighting ... underscoring/emphasizing/showcasing`
- `fostering/encouraging/promoting ... while [verb]-ing`

**Example (bad):**
```markdown
The update improves performance, highlighting its importance and underscoring its value.
```

**Example (good):**
```markdown
The update reduces API latency by 30%.
```

---

### S007: False Ranges

Detects "from X to Y" with incoherent extremes.

**Example (bad):**
```markdown
Used in settings from basic to advanced.
```

**Example (good):**
```markdown
Suitable for both new and experienced developers.
```

---

## Style Rules (T)

### T001: Title Case Headings

Detects improper capitalization in Markdown headings.

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

**Example (bad):**
```markdown
The **quick** brown **fox** jumps over the **lazy** dog **today**.
```

**Example (good):**
```markdown
The quick brown fox jumps over the lazy dog.
```

---

### T003: Em Dash Overuse

Detects excessive em dashes (—) for dramatic effect.

**Example (bad):**
```markdown
The solution—designed in January—tested in March—revised in April—shipped in May—and monitored in June—worked.
```

**Example (good):**
```markdown
The solution, which took months to develop, was finally ready and worked.
```

---

### T004: Quote Inconsistency

Detects mixed curly and straight quote styles.

**Example (bad):**
```markdown
He said “hello” and she replied "goodbye".
```

**Example (good):**
```markdown
He said "hello" and she replied "goodbye".
```

---

### T005: Emoji in Prose

Detects non-technical emoji in documentation.

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

Synonym pairs are compared only within one prose block, not across unrelated
paragraphs or skipped constructs.

**Example (bad):**
```markdown
Use the parser for CSV files. Employ the parser for TSV files.
```

**Example (good):**
```markdown
Use the parser for CSV and TSV files.
```

---

## Grammar Rules (G)

### G001: Copula Avoidance

Detects "serves as" instead of simpler "is".

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

Hedge stacking uses wrapped, source-mapped sentence boundaries rather than
physical source lines.

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

### C001: Docstring-Only Vocabulary

Detects Python docstring terms not covered by `V001`. Its built-in terms are
`utilize`, `bespoke`, `holistic`, and `paradigm`; configured vocabulary
additions belong to `V001` so the two rules do not report the same match.

**Example (bad):**
```python
def process(data):
    """Utilize a bespoke parser for the data."""
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

**Example (bad):**
```python
# TODO: Implement
# TODO: Add logic here
```

**Example (good):**
```python
# TODO: Add retry logic for network failures (issue #42)
```

---

## Markup Rules (M)

### M001: Wrong Markup

Detects Markdown syntax in wrong context.

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

Detects invalid model-specific references and unfinished Markdown link
destinations. Explicit replacement tokens (`URL_HERE`, `INSERT_URL`, `TODO`,
and `TBD`) are high confidence; empty and `#` destinations are low confidence.

**Detected patterns:**
- `[attached_file:1]`
- `grok_card`
- `[file_1]`
- `[example](URL_HERE)`
- `[reference]: INSERT_URL`
- `[empty]()` and `[top](#)`

**Example (bad):**
```markdown
See the attached document [attached_file:1] for details.
```

**Example (good):**
```markdown
See [the guide](/guide), [the section](#install), or [email](mailto:ops@example.com).
See [documentation](https://example.com/docs).
```

---

### M005: Unresolved Markdown References

Detects explicit Markdown reference uses without a matching definition and
duplicate definitions that assign different destinations to the same normalized
label. Undefined uses are high confidence; conflicting definitions are low
confidence.

**Example (bad):**
```markdown
See [the installation guide][install].

[api]: /api/v1
[API]: /api/v2
```

**Example (good):**
```markdown
See [the installation guide][install].

[install]: /installation
```

Bare bracketed text is not considered an unresolved shortcut because shortcut
references exist only when a matching definition is present. Footnotes and
references inside code examples are ignored.

---

### M006: Template Residue

Detects unfinished template content in Markdown. Explicit sample text and
replacement markers are high confidence; standalone TODO/TBD lines are low
confidence so planning documents can filter them out.

**Detected patterns:**
- `Lorem ipsum`
- `[insert example here]` and `[replace this section]`
- `<replace-me>` and `YOUR CONTENT HERE`
- Standalone `TODO` or `TBD: add details`

**Example (bad):**
```markdown
The introduction is [insert final copy here].
```

**Example (good):**
```markdown
The introduction explains how retries use exponential backoff.
```

Fenced code, inline code, HTML blocks, and content under example-style headings
such as `Example`, `Template`, and `Before` are ignored. Findings suggest
replacing the marker with final content but never rewrite the source.

---

### M007: Unclosed Code Fence

Detects fenced Markdown code blocks that reach end of file without a valid
closing delimiter. Findings are high-confidence errors reported across the
opening delimiter and suggest adding the matching fence.

**Detected patterns:**
- Opening fences of three or more backticks or tildes, indented by zero to
  three spaces, without a closer
- Closers that use the wrong fence character
- Closers that are shorter than the opening delimiter

**Example (bad):**
`````markdown
```python
print("This block never closes")
`````

**Example (good):**
``````markdown
````text
This block uses a longer valid closer.
`````
``````

Only the same fence character repeated at least as many times closes a block.
The swallowed body remains classified as code, preventing cascaded prose
findings after the syntax error.

---

### M008: Skipped Heading Level

Detects visible Markdown headings that jump upward by more than one level. The
finding is a high-confidence warning on the later heading and suggests the next
missing intermediate level.

**Example (bad):**
```markdown
# Deployment
### Rollback
```

**Example (good):**
```markdown
# Deployment
## Recovery
### Rollback
```

The first visible heading may start at any level. Repeated levels, transitions
to shallower headings, and headings inside fenced code or HTML blocks are not
reported. ATX and Setext headings, including blockquoted headings, participate
in comparisons through the shared Markdown parser.

---

### M010: Non-Descriptive Link Text

Detects Markdown links whose visible label does not describe the destination.
Findings are high-confidence warnings on the label text and suggest replacing
it with destination-specific wording.

**Detected labels:**
- `here`
- `click here`
- `this link`
- `link`

**Example (bad):**
```markdown
Read [click here](/installation) before deploying.
```

**Example (good):**
```markdown
Read the [installation guide](/installation) before deploying.
```

Matching is case-insensitive and ignores whitespace differences, but the whole
visible label must match. Additional descriptive words are not reported.
Autolinks, images, reference definitions, undefined references, code, HTML
blocks, and demonstration sections are excluded. Inline and resolved reference
links are checked through the shared Markdown parser.

---

## Phase 10: AI Writing Tropes Rules

The following rules were added based on the
[AI Writing Tropes to Avoid](https://tropes.fyi) catalogue.

---

### V006: Grandiose Stakes

Detects inflated importance claims that overstate significance.

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

Determiner-led references such as "a gap", "that gap", or "the dilemma" do
not count toward the threshold and are not reported after other labels cross it.

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
intervene manually. This experiment addresses a gap in the available data.
```

---

### S008: Dramatic Countdown

Detects "Not X. Not Y. Just/But Z." dramatic negation patterns.

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

Runs stay within one body or block-quote paragraph; headings, lists, blank
paragraphs, and skipped Markdown constructs reset them. Wrapped source lines
remain part of the same sentence.

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

A run cannot cross a paragraph, heading, list, block quote, or skipped Markdown
construct. Wrapped source lines remain part of the same sentence.

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

Ordinal sequences are evaluated within one body or block-quote paragraph, not
across headings, lists, blank paragraphs, or skipped Markdown constructs.

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

Only body paragraphs count. Headings, lists, block quotes, code, HTML, tables,
front matter, and MDX/JSX barriers reset a run.

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

Checks apply to body text, list items, and block quotes. Headings and skipped
Markdown constructs are excluded. Word counts use wrapped, source-mapped
sentences rather than physical lines.

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

Trend language is downgraded to low confidence when a bounded neighboring
sentence in the same prose block provides attribution, a date, a link, a
percentage, or before-and-after figures.

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

The rule requires a generalization in the anecdote sentence or the next
sentence in the same prose block. Explicit examples, quoted-sentence
discussion, and dateline-format discussion are ignored.

**Detected patterns:**
- "For [Name] of [Location], the…"
- "Take [Name], a [descriptor]…"
- "Meet [Name]"

**Example (bad):**
```markdown
For Sarah of Ohio, the new policy meant losing her healthcare. Her case proves the policy harms every family.
```

**Example (good):**
```markdown
A 2024 Kaiser Family Foundation survey found that 12% of respondents in Ohio lost coverage after the policy change.
```

---

### S018: Citation Name-Dropping

Detects 3+ consecutive "Author (Year) verb" sentences that list citations
without synthesizing them.

Consecutive runs use wrapped, source-mapped sentences and reset when ordinary
prose or a hard prose-block boundary interrupts the citations.

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

The ambiguous terms "restructuring", "realignment", and "resource
optimization" require company, workforce, staffing, or organizational context.
Unambiguous phrases such as "right-sizing" and explicit headcount reductions
remain findings without that extra gate.

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
The database restructuring moves two indexes to the reporting tablespace.
```

---

### S020: Alignment Ritual

Detects phrases that signal performative consensus-seeking rather than
substantive agreement.

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

Lines with a finite auxiliary or an explicit pronoun-led predicate are complete
clauses, even when they contain two or more buzzwords.

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

---

### G015: Generic Scene-Setting Opener

At medium confidence, detects a generic scene-setting clause in the first
substantive Markdown body sentence. Headings, block quotes, lists, code, and
content under example-style headings do not become the document opener.

**Detected patterns:**
- `In today's rapidly evolving digital landscape…`
- `In the modern world…`
- `In a rapidly evolving landscape…`
- `In an era defined by constant change…`

Replace the generic opener with the concrete subject or change the document
actually addresses.

**Example (bad):**
```markdown
In today's rapidly evolving digital landscape, reliable payments matter more than ever.
```

**Example (good):**
```markdown
The payment API now retries one timed-out request after 200 milliseconds.
```
