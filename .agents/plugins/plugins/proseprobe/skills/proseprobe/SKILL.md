---
name: proseprobe
description: Use when an agent generates, edits, or reviews prose in Markdown or Python docstrings and comments in a project that uses proseprobe.
license: MIT
---

# ProseProbe

Use `proseprobe` as a deterministic review step for Markdown prose and
source-mapped Python docstrings and comments.
ProseProbe reports findings; it does not rewrite files.

## Check

Run from the project root so configuration discovery matches normal project use.
For files already in the checkout, request JSON Lines:

```bash
proseprobe check --format jsonl README.md docs/
```

For one generated document, use standard input with a virtual filename:

```bash
generate-draft | proseprobe check - --filename docs/draft.md --format jsonl
```

If the repository installs the published pre-commit hook, run:

```bash
pre-commit run proseprobe
```

Respect the project's selected rules, profile, severities, confidence policy,
per-file ignores, suppressions, and baseline.
Do not add or switch to an `agent` profile.

## Interpret

Read each complete JSON Lines record and its surrounding prose before deciding
whether to edit the reported source span. A missing end position means the
finding summarizes multiple matches or a wider
threshold.
Handle high-confidence findings first, then medium, then low.

Markdown blockquotes remain linted: a blockquote can be a draft callout rather
than a literal quotation. Preserve exact quotations and named technical concepts
even when findings have medium or high confidence. Suggestions are review prompts,
not replacements that necessarily fit the sentence. Treat overlapping findings
on one source span as one editing decision while retaining the rule IDs.

Inspect unfamiliar or intentional findings through canonical rule metadata:

```bash
proseprobe rules --format json
proseprobe explain V001 --format json
```

| Code | Meaning |
|------|---------|
| `0` | No warning or error findings; info findings may still be present. |
| `1` | At least one warning or error finding was reported. |
| `2` | Command usage or project configuration is invalid. |
| `3` | An input could not be read. |

On exit `2` or `3`, fix the invocation, configuration, or input access before
editing prose.

## Repair and verify

1. Preserve the author's meaning, quotations, and intentional terminology.
2. Address warning and error findings before advisory info findings.
3. Use an existing narrow suppression only when project policy permits it. Do
   not add blanket ignores, accept baseline entries, or lower thresholds merely
   to make the scan pass.
4. Rerun the same command after every edit.
5. Run the repository's normal formatting, test, and documentation checks before
   handoff.

Keep rewriting in the calling agent. Do not add model credentials, provider
SDKs, network access, prompt scoring, or rewrite behavior to `proseprobe`.
