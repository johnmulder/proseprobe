P32D.5b packet design review D001
Reading link: [D001](/private/tmp/proseprobe-D001.txt)
Exposed engineering design; no independent human effectiveness claim.

Keep build_reading v1 behavior and frozen prior packets unchanged.
Add a benchmark-only builder that returns a finite linked reading bundle.
Inputs: eligible Source/cache, full-line focus region, rule IDs, caller
instructions/questions, short reading ID and absolute output-link directory.
The builder returns texts and bindings; callers persist the linked files.

Python context is static raw source, not normalized parameter metadata.
Select every lexical function/class header intersecting the focus region,
including enclosing owners, decorators, async and complete multiline headers.
Use AST ownership and tokens to find the suite colon. Never execute source.
Module scope is explicit. Malformed/unsupported source fails rather than
pretending no signature exists. Reject line separators incompatible with
AST/token physical lines; preserve LF/CRLF bytes and original coordinates.

For M011/M012, require explicit supported GitHub renderer context.
Parse the complete bound source. Supply ordered heading metadata and the
computed complete supported anchor-ID set, labeled structural/derived.
Also include complete original Markdown in companion readings. This lets
reviewers inspect explicit HTML anchors, examples and inventory provenance
without adding production parser APIs or inventing anchor attribute columns.
Duplicate heading rows remain; the anchor-ID set is membership, not an
occurrence list. Generated/unsupported markup cannot yield an empty inventory.

For M012 require the existing VerifiedReferenceContext from offline validation.
Match source ID/bytes, renderer and complete declared references. Include all
referenced targets: exact full bytes + hash + heading/anchor inventory, or
pinned absence tied to native revision/manifest/inventory hashes. Unknown
or unbound targets fail. Never resolve new filesystem paths or fetch URLs.
This internal API trusts validator-produced immutable context; arbitrary
caller-constructed proof objects are outside that precondition.

Paginate exact mapped chunks and derived inventory records, never truncate.
Each page includes its own direct link, context digest, role, ordinal/total,
previous/next links, caller instructions/questions and source-coordinate key.
Every page stays at most 80 physical lines of 80 Unicode code points.
The finite ordered index binds source IDs/hashes, roles, source row maps,
page hashes and links. A canonical bundle digest binds index/context/pages.
No expected findings, clean scopes or reviewer coverage is manufactured.

Questions: is the required evidence accessible within these readings?
Does full source/target context avoid unsupported anchor-position guesses?
Identify missing provenance, unsafe scope expansion, or needless machinery.
Suggest the smallest correction and essential failing tests before coding.
