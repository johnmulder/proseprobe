# Bounded context execution

The user requested P32D.5b. Separate agents inspected signature and Markdown
context APIs; a fresh design reviewer accepted D001 with two requirements:
wrapped chunks retain reversible original columns, and an impossible mandatory
page envelope must fail explicitly. Design inputs were committed as `5cce78e`.
These are exposed engineering judgments, not independent human labels.

R01: The first draft preceded the new Python tests. Its initial 21 cases passed
as characterization checks; no initial RED is claimed. The agent then found a
real decorator-line ownership defect, and a second test exposed missing visible
rule IDs on the linked pages. Both failed before their fixes. The final focused
suite passed 52 tests, including all 28 existing v1 renderer tests. Exact logs
and runtime identity are in `tdd-python.json`.

The benchmark-only builder selects raw lexical class/function headers, including
decorators, multiline signatures, ancestors and async declarations. AST and
tokens supply ownership; reviewed code is never imported or run. Module scope
is explicit. Malformed syntax and line separators incompatible with parser
coordinates are refused rather than rendered as an empty owner list.

The shared chunk renderer retains original source coordinates and endings.
Every new page has its direct absolute link, role, ordinal/total, context hash,
adjacent links, rule IDs and caller scope/questions. Required context paginates
without truncation; oversized mandatory content fails before a bundle returns.
Canonical context and bundle hashes bind exact pages and their ordered index.
The builder returns text; callers persist every linked reading.

The complete gate passed 3710 tests, package typing and both curated regression
policies, retaining all six all-rules and four production known mismatches.
Targeted strict typing also passed for the two reading helpers with dependency
imports silent. Markdown/native context remains the next stage.
