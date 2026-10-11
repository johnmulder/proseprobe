Read it as an editor: identify claims that need clarification, then check
whether the displayed passage supplies that clarification. You do not need
to know the linter’s implementation.

For this first pass, check only these three things:

1. **G038: comparison without a clear target**
   Does “better,” “faster,” or “easier” leave you wondering “than what?”

   Invented examples:
   - “This version is faster.” — the comparison target is missing.
   - “This version is faster than version 2 on this workload.” — clear target.

2. **V015: ranking without a clear scope**
   Does “best” or “fastest” leave the set of alternatives unclear?

   Invented examples:
   - “This is the best parser.” — best among which parsers?
   - “This was the fastest of the three parsers we tested.” — defined scope.

3. **V016: an unconditional reliability or security guarantee**
   Look for claims such as “never fails,” “always works,” or “100% secure.”
   Check whether the statement is limited to a stated test or condition.

   Invented examples:
   - “The system never fails.” — an unrestricted guarantee.
   - “It completed all 500 requests in this test.” — a bounded observation.

Read nearby headings and sentences for context. Ordinary capability statements
are not automatically guarantees. Template syntax and awkward formatting are
outside this particular review.

For each rule, choose:

- **No issue:** you checked the passage and found no relevant violation.
- **Issue:** quote the wording and explain what clarification is missing.
- **Context needed:** explain what you would need to judge it.
- **Not reviewed:** you have not checked that rule yet.

You can reply using this template:

```text
G038: ...
V015: ...
V016: ...
```

If all three checks find no issue, “No issues for all three rules in this
region” is sufficient. Your judgment applies only to the displayed passage.
