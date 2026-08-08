# Agent integration guide

Use `proseprobe` as a deterministic review step for Markdown prose and
source-mapped Python docstrings and comments. It reports source locations,
severity, confidence, and optional suggestions.
ProseProbe reports findings; it does not rewrite files.

## When to run

Run it after changing prose, before handing work back, and again after every
repair.
Run from the project root so configuration discovery matches normal project use.
Respect the repository's selected rules, profile, severity and confidence
policy, per-file ignores, suppressions, and baseline.

Do not add or switch to an `agent` profile. If a project needs different policy,
change its normal configuration only when the project owner authorizes that
change.

## Choose an input and output

For files already in the checkout, pass their paths and request JSON Lines:

```bash
proseprobe check --format jsonl README.md docs/
```

JSON Lines writes one diagnostic object per line, preserves deterministic
ordering, and writes no wrapper. A clean scan with no findings writes no stdout.
Use grouped JSON instead when the caller needs file grouping and run totals.

For one generated document, send it through standard input and supply a virtual
filename:

```bash
generate-draft | proseprobe check - --filename docs/draft.md --format jsonl
```

The filename selects file-type rules and per-file policy. Standard input cannot
be mixed with filesystem paths or baseline operations.

When the repository has installed its published pre-commit hook, this checks the
staged files without adding Git-specific behavior to proseprobe:

```bash
pre-commit run proseprobe
```

Otherwise, pass the exact files changed by the current task. Avoid shell command
substitutions that split filenames on spaces or newlines.

## Interpret diagnostics

Each JSON Lines record includes `rule_id`, `message`, `path`, 1-based start
coordinates, nullable exclusive end coordinates, `severity`, `confidence`, and
an optional `suggestion`. Use the reported source span when editing; a missing
end means the finding summarizes multiple matches or a wider threshold.

Handle high-confidence findings first, then medium, then low. Severity controls
whether the scan fails: errors and warnings are failing findings, while info
findings are advisory. Confidence estimates how likely the rule is to be useful;
it does not replace repository policy.

Inspect canonical rule metadata instead of hard-coding the rule catalog:

```bash
proseprobe rules --format json
proseprobe explain V001 --format json
```

`explain` is the first step when terminology may be intentional or a diagnostic
is unclear.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | No warning or error findings; info findings may still be present. |
| `1` | At least one warning or error finding was reported. |
| `2` | Command usage or project configuration is invalid. |
| `3` | An input could not be read. |

Do not treat every JSON Lines record as exit `1`. Also do not treat exit `0` as
proof that stdout is empty, because info findings may still be present. On exit
`2` or `3`, fix the invocation, configuration, or input access before editing
prose.

## Repair loop

1. Run `check --format jsonl` on the task's files from the project root.
2. Read the complete record and, when needed, inspect the rule with `explain`.
3. Address high-confidence errors and warnings before lower-confidence or info
   findings. Keep edits limited to the requested work and preserve the author's
   meaning.
4. When a term or construction is intentional, leave it unchanged unless the
   project permits a narrow inline suppression. Markdown suppressions target the
   following physical line; Python suppressions target the same physical line.
5. Rerun the same command after every edit. Review any remaining info records
   even when the command exits `0`.
6. Run the repository's normal formatter, tests, and documentation checks before
   handoff.

Use the narrowest approved suppression. Do not create blanket ignores, accept
new baseline entries, or lower project thresholds merely to make a scan pass.
The exact syntax and validation rules are in the
[configuration guide](configuration.md#inline-suppressions).

## Boundaries

Keep generation and rewriting in the calling agent. `proseprobe` needs no model
credentials, provider SDK, network access, prompt scoring, or embedded rewrite
mode. Its structured diagnostics and rule metadata are the integration API.
