# Rule Reference

This document describes all detection rules available in humanize.

## Vocabulary Rules (V)

### V001: AI Vocabulary

Detects overused AI-specific words that rarely appear in natural human writing.

**Severity:** Warning (configurable)  
**Fixable:** Yes

**Examples:**
- "delve" → "explore"
- "tapestry" → "collection"
- "multifaceted" → "complex"
- "leveraging" → "using"

### V002: Collaborative Phrases

Detects chat-like communication patterns that appear in AI responses.

**Severity:** Warning  
**Fixable:** No

**Examples:**
- "I hope this helps!"
- "Let me know if you need more information."
- "Certainly!"

### V003: Knowledge Cutoff

Detects temporal disclaimers about training data.

**Severity:** Info  
**Fixable:** No

**Examples:**
- "As of my last update..."
- "Based on available information..."

### V004: Promotional Language

Detects puffery and marketing speak.

**Severity:** Warning  
**Fixable:** No

**Examples:**
- "world-class"
- "cutting-edge"
- "groundbreaking"

### V005: Weasel Words

Detects vague attributions.

**Severity:** Info  
**Fixable:** No

**Examples:**
- "Experts say..."
- "Studies show..."

---

## Structural Rules (S)

### S001: Rule of Three

Detects excessive triadic patterns.

### S002: Negative Parallelism

Detects "Not only... but also..." constructions.

### S003: Challenge Conclusions

Detects formulaic challenge endings.

### S004: Inline-Header Lists

Detects bold headers in bullet lists.

### S005: Significance Emphasis

Detects undue importance claims.

### S006: Superficial Analysis

Detects present participle chains.

### S007: False Ranges

Detects incoherent scales.

---

## Style Rules (T)

### T001: Title Case Headings

Detects improper capitalization.

### T002: Bold Overuse

Detects excessive emphasis.

### T003: Em Dash Overuse

Detects excessive em dashes.

### T004: Quote Inconsistency

Detects mixed quote styles.

### T005: Emoji in Prose

Detects non-technical emoji.

### T006: Elegant Variation

Detects unnatural synonyms.

---

## Grammar Rules (G)

### G001: Copula Avoidance

Detects "serves as" instead of "is".

### G002: Excessive Hedging

Detects over-qualification.

### G003: Participle Chains

Detects dangling modifiers.

---

## Code Rules (C)

### C001: Docstring Vocabulary

Detects AI vocabulary in docstrings.

### C002: Verbose Comments

Detects over-explained comments.

### C003: Collaborative Comments

Detects chat phrases in comments.

### C004: AI Placeholders

Detects formulaic TODOs.

---

## Markup Rules (M)

### M001: Wrong Markup

Detects Markdown in wrong context.

### M002: ChatGPT Markers

Detects reference artifacts.

### M003: UTM Parameters

Detects AI tracking parameters.

### M004: Broken References

Detects invalid citations.
