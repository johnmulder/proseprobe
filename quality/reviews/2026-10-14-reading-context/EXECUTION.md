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
imports silent.

R02: The agent's Markdown/native tests produced 27 failures and one pass before
the new branch. After implementation all 28 passed, including the real offline
validator integration. Four further boundary tests failed before corrections:
Unicode line separators in link directories and silently ignored Markdown
context on Python. Those cases then passed.

The builder now includes complete original Markdown companions, ordered
headings and sorted anchor-ID membership under the explicit GitHub renderer.
M012 consumes the existing validator's immutable native context. All selected
source references bind complete target bytes or pinned absence, including
references outside the focus. Empty targets remain present. No target paths
are reopened, new references resolved or network calls made by the builder.
The trusted internal validator-object precondition is documented explicitly.

The final engineering reviewer found trailing suite comments losing ownership,
URI-sensitive directory names producing different destinations, and long
backtick metadata overflowing its fence. Eight new cases failed before their
fixes; two negative ownership cases already passed. Follow-up review exposed
mixed indentation, an entity-spelling path and a leading double slash. Each
received its own failing test before correction. Final static review accepts
the fixes; both original and follow-up judgments remain intact.

The final focused suite passes 169 tests. The full repository gate passes 3755
tests, package typing and the same six all-rules/four production curated
mismatches. Strict typing also passes for both reading helpers with dependency
imports silent. Exact RED/GREEN logs and final runtime identity are retained
in `tdd-markdown.json`; historical logs are not rebound to the final runtime.
No production rule, default, baseline, frozen label or source split changed.
