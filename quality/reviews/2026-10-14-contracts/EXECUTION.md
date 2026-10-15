# Contract resolution execution

K01: Declared four linked readings in commit `0b31b34`, before new decisions.
The largest has 46 lines; no line exceeds 77 characters. Fresh agents
`/root/contracts_reviewer_a` and `/root/contracts_reviewer_b` reviewed the same
packets separately, without detector code, tests, old annotation files or each
other's answers. This was exposed contract design, not blind effectiveness
measurement. Both original reviews remain intact.

Both reviewers require finite positive evidence for executable C004 placeholders,
classify the Requests rejection message outside that branch, select the TODO
marker without its comment introducer, and retain G038/V015 phrase highlights.
They disagree on C009: A keeps the identifier, while B proposes a deliberate
amendment to include stars. `/root/contracts_adjudicator` read both reviews and
retained the published identifier-only contract. The diagnostic states the kind
conflict; this review supplies no user evidence requiring a wider highlight.
`adjudication.json` binds the two raw decisions and explains all four spans.

The accepted C004 executable criterion requires a parsed simple-name
`NotImplementedError` call with exactly one positional literal string and no
keywords, outside the existing proven abstract/typing exemptions. Normalize
ASCII whitespace, casefold and remove at most one final period, in that order;
then match the entire message against the six accepted phrases. No second trim
or substring classifier is used. Unknown messages abstain; absence of a finding
does not establish complete code or infer author intent. The original raise/call
highlight remains intact, including original multiline/escaped literal spelling.

K02: Added negative examples before changing detection. The expanded unit/CLI
selection failed in 19 cases on specific rejection, ambiguous messages, extra
arguments and per-line selection. A separate normalization test caught an extra
trim after the final period; that test failed before the trim was removed.
The focused code-rule and CLI suite then passed all 471 tests.

Executable detection now uses the accepted six-message set and strict call
shape. Specific alternate-operation instructions and issue-specific future-work
descriptions no longer trigger the executable branch. Existing syntax, Unicode,
multiline and line-deduplication tests use accepted positive messages. Protected
abstract/typing fixtures also use positive messages, so exemption tests remain
meaningful; no binding, shadowing or mutation guard was removed. The CLI test
places the same positive message in concrete and abstract methods and requires
only the concrete diagnostic. The rejected Requests text is not imported or run.

The published C004 contract now documents the exact finite vocabulary,
normalization, call shapes and abstention limits. Rule severity, confidence,
defaults and profiles remain unchanged. Comment highlighting is a separate next
stage. Test commands and exact red/green logs are retained in `tdd-c004.json`.
The complete `make check dogfood rule-quality-regression` gate passed 3679 tests,
package typing across 31 files and both curated regression policies. All six
all-rules and four production known mismatches remain unchanged.
