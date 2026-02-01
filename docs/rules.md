# Rule Reference

This document describes all detection rules available in humanize.

---

## Vocabulary Rules (V)

### V001: AI Vocabulary

Detects overused AI-specific words that rarely appear in natural human writing.

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

Detects chat-like communication patterns from AI assistants.

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

Detects over-qualification phrases.

**Severity:** Info  
**Fixable:** No

**Detected patterns:**
- "It is important to note that..."
- "It's worth mentioning that..."
- "It should be noted that..."

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

Detects AI vocabulary in Python docstrings.

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

### C004: AI Placeholders

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

Detects AI-related tracking parameters in URLs.

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

Detects invalid citation formats from AI.

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
