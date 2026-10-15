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

K03: Eight marker-span tests failed before the source highlight changed. Bare
context-free TODO/FIXME/XXX findings now select the marker token alone, without
the hash, colon or whitespace. Case, inline comments, tabs, malformed Python and
Unicode before the comment retain original code-point positions. Other formulaic
comment phrases and code-attached hints keep their existing spans.

The exact G038/V015 example spans are now pinned alongside existing wrapped and
Unicode source-mapping tests. The C009 example pins the identifier-only span
while asserting that its diagnostic names `**extras` and both parameter kinds.
These three contracts were retained; their wider historical expected spans are
annotation-contract differences, not evidence requiring wider code highlights.
The published rule documentation now distinguishes recognition/ownership
evidence from the highlighted unit and makes all four outcomes explicit.

The focused code, grammar, vocabulary and source-predicate suite passed 1414
tests. `tdd-highlights.json` retains the red/green output and exact runtime hash.
A fresh engineering agent, `/root/contract_change_review`, reviewed the accepted
criteria, code diff, docs and changed tests without finding an actionable issue.
It ran no tests and opened no source manifests, prior labels or holdout.

The first complete highlight gate exposed three maintained curated expectations
that still selected the comment hash at column 5. The accepted marker starts at
column 7. This created three artificial FP/FN pairs without changing detection.
The failing gate is preserved in `tdd-highlights.json`; it was not allowlisted.

The agent reviewed a separate linked 32-line reading, K005, and approved each
coordinate under the accepted contract. Only the three current curated C004
starts at `python-docs.py` lines 38–40 changed to column 7. The two current gate
manifest hashes were rebound to that amended maintained manifest. All other
entries, semantic labels, source hashes, policies, counts and known-mismatch
lists remain identical. `curated-migration.json` preserves before/after values,
hashes and the prior Git commit. Frozen external labels and historical report
artifacts were not amended.

The final complete gate passed all 3686 tests, package typing across 31 files,
generated rule-doc checks, documentation checks and both bound regression
policies. Curated counts remain 366 TP/6 FP/0 FN for all-rules and 106 TP/4 FP/0 FN
for production. All existing known mismatches remain visible. The exact log and
runtime identity are bound in `tdd-highlights.json`.
