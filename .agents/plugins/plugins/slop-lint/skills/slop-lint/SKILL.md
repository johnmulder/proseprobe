---
name: slop-lint
description: Use when an agent generates, edits, or reviews prose in Markdown or Python docstrings and comments in a project that uses slop-lint.
license: MIT
compatibility: Requires the slop-lint executable on PATH.
---

# slop-lint

Use `slop-lint` as a deterministic review step for Markdown prose and
source-mapped Python docstrings and comments.
slop-lint reports findings; it does not rewrite files.

## Check

Run from the project root so configuration discovery matches normal project use.
For files already in the checkout, request JSON Lines:

```bash
slop-lint check --format jsonl README.md docs/
```

For one generated document, use standard input with a virtual filename:

```bash
generate-draft | slop-lint check - --filename docs/draft.md --format jsonl
```

If the repository installs the published pre-commit hook, run:

```bash
pre-commit run slop-lint
```

Respect the project's selected rules, profile, severities, confidence policy,
per-file ignores, suppressions, and baseline.
Do not add or switch to an `agent` profile.

## Interpret

Read each complete JSON Lines record and edit the reported source span. A
missing end position means the finding summarizes multiple matches or a wider
threshold.
Handle high-confidence findings first, then medium, then low.

Inspect unfamiliar or intentional findings through canonical rule metadata:

```bash
slop-lint rules --format json
slop-lint explain V001 --format json
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
SDKs, network access, prompt scoring, or rewrite behavior to `slop-lint`.
