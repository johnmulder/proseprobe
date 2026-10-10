# Rule-quality corpus

This directory contains reviewed document-like inputs for measuring rule
precision and recall. It complements unit tests: unit tests prove that a pattern
can fire, while this corpus records whether findings are correct in surrounding
technical, academic, business, journalistic, changelog, and Python content.

## Evaluation policy

`make rule-quality` retains the historical all-rules measurement with
informational findings and low minimum confidence. Optional M011 is explicitly
enabled with the reported GitHub anchor policy. It uses explicit defaults
without discovering repository or user configuration. Production-policy
measurements use the same construction and confidence filters as the CLI:

```bash
rtk proxy .venv/bin/python -m benchmarks.rule_quality --mode production --format json
rtk proxy .venv/bin/python -m benchmarks.rule_quality --profile technical-docs --format json
rtk proxy .venv/bin/python -m benchmarks.rule_quality --severity warning --min-confidence high --format json
```

Policy options imply production mode. Explicit all-rules mode rejects those
options so its name continues to describe the measured policy. Baselines are
excluded from effectiveness evaluation. Genuine eligible issues removed by a
confidence filter still count as missed detections.

JSON reports contain the effective policy, package version, Git revision,
manifest and source checksums, counts, and mismatch details. They retain
exact-start scores and report detection and complete-span accuracy separately.
Rule/severity/file-policy exclusions are reported separately from missed
eligible findings.

`annotations.json` also references selected files under `tests/fixtures/` so
existing examples remain the single source for those cases.

## Annotation rules

- `expected` entries match findings by exact path, rule ID, line, and column.
- `negative_cases` identify lines on which a named rule must not fire.
- Any emitted finding without an expectation is a false positive.
- Any expectation without an emitted finding is a false negative.
- Do not turn a known false positive into an expectation to improve the score.

The version 1 regression manifest requires every registered rule to have at
least one expected finding and one explicit negative case. The evaluator rejects
unknown rules, duplicate locations, invalid spans, missing files, and paths
outside its declared root. Supplied endpoints are exclusive character positions;
legacy expectations without endpoints remain start-only checks.

## Sparse external annotations

Version 2 manifests declare coverage rather than treating unseen material as
clean. Each file contains `expected`, `negative_cases`, and `reviewed_rules`;
optional `source_group` identifies a repository or other shared source. A rule
in `reviewed_rules` has exhaustive whole-file coverage. Optional `regions`
override that coverage for named rules and exact source spans, with status
`reviewed`, `unreviewed`, `unsupported`, or `context-dependent`. The last two
statuses require an explanatory `note`. Same-rule regions cannot overlap.

Regions require `rules`, `status`, `line`, `column`, and `end_column`, with
optional `end_line`. Expected issues may add exclusive endpoints. A narrow
negative uses `column` and `end_column`; omitted columns preserve a legacy
whole-line negative. Only the existing M004 empty-destination contract permits
a zero-width expected issue.

A separately reviewed semantic correspondence requires an expected issue's
globally unique `id` and explicit `match_region`. That region must contain the
expected span and stay within reviewed coverage. Matching remains one-to-one
and rule-specific. Arbitrary overlap, duplicates, and findings crossing a
review boundary receive no detection credit. Exact-start and complete-span
checks remain available even when semantic detection receives credit.

An unmatched finding is a false positive only within exhaustive reviewed
coverage. Findings elsewhere remain unreviewed, unsupported, or unresolved.
Eligible positives removed by a confidence threshold remain false negatives.
Raw confidence-band precision is available; band recall is unavailable because
missed issues have no detector-assigned confidence.

```bash
rtk proxy .venv/bin/python -m benchmarks.rule_quality --manifest /path/to/reviewed.json --root /path/to/originals --mode production --format json
```

The evaluation JSON schema version is 3. Reports include rule, policy, severity, confidence,
format, Python-documentation context, and source-group counts, alongside exact
locations and annotation statuses. False-warning density counts eligible
extracted prose words in reviewed regions; masked code and unreviewed text do
not enter its denominator. Empty coverage produces an unavailable density.
Wilson intervals describe reviewed samples, with source-group variation shown
separately; correlated findings are not independent population evidence.
`reviewed_coverage` counts eligible extracted prose words, files and review
regions even when a reviewed source is clean. `reviewed_source_group_count`
counts identified groups with such coverage; unidentified coverage remains
visible as `unspecified`. Disabled, file-ignored and inapplicable rules cannot
supply coverage credit. `metric_source_group_counts` separately records groups
contributing to precision, recall and density. A clean group supplies density
coverage without inventing detection observations or a precision denominator.
No source-correlated interval is inferred from the number of coverage groups.

Macro averages include supported rules with defined denominators. Span accuracy
uses matched expectations that actually supplied endpoints.

The [external pilot guide](external/README.md) records frozen sources and the
blind human-review workflow. Native revisions are supplementary evidence,
not automatically assigned writing-quality labels.

## Source-bound review artifacts

Version 3 retains version 2 coverage and matching semantics and binds each file
to a source identity and SHA-256 of its exact UTF-8 bytes. A review header names
the packet index, declared rule-contract snapshot, protocol, policy and reviewers.
Both referenced artifacts have locally verified checksums. The snapshot covers
declared rule metadata; implementation identity is reported separately.
Initially unreviewed templates have no reviewer identifiers or clean judgments.

Runtime identity includes the imported package/evaluator source digest, package
version, source scope, and available Git revision and staged/unstaged/untracked
state. Relevant ignored Python files also enter the digest and untracked state;
caches and unrelated prose do not. Identical source bytes at another location
have the same digest. Unavailable Git fields are null. The retained `revision`
field is an alias for the available runtime revision, not proof of clean code.

Bound scans consume verified immutable bytes through the normal file policy.
A changed source, packet or declared contract requires review before reuse.
Legacy version 1/2 reports remain available and explicitly state that their
annotation-time source binding and review provenance are unavailable.
`--require-bound` rejects legacy annotations for independent evaluation.

The `quality/examples/source-bound/` packet is a minimal offline example with
agent-authored text and labels; it provides no independent human evidence:

```sh
rtk proxy .venv/bin/python -m benchmarks.rule_quality --manifest quality/examples/source-bound/annotations.json --root quality/examples/source-bound --require-bound --format json
```

Preserve source bytes during annotation. After a deliberate source or contract
change, review affected labels and issue a new versioned packet with its real
review provenance. Do not refresh checksums to make an old review appear current.

## Updating the corpus

1. Add or edit the smallest source excerpt that covers the behavior.
2. Run `python -m benchmarks.rule_quality`.
3. Review every new mismatch against `docs/rules.md`.
4. Add an expectation only for a genuine violation.
5. Add a negative case for a legitimate use or close near miss.
6. Run the evaluator again, followed by the project test suite.

Keep excerpts purpose-written or clearly licensed. Prefer a few realistic
paragraphs over long generated documents.

## Technical review sample

The `technical-review*.md` excerpts reproduce a workspace evaluation's technical
terms, draft prose, and literal quotations. The held-out file contains related
examples written before changing the rules; it is a regression set, not an
independent estimate of general precision. An agent reviewed the annotations
against the declared author intent. They have not received independent human
review.

Run `make rule-quality` to include this sample under the evaluator's default
configuration. It includes informational findings; the normal CLI reports
warnings and errors unless another severity is requested. Intentional technical
terms and exact quotations remain negative cases even when the linter reports
them. Blockquote syntax alone cannot distinguish a quotation from a draft
callout. The agent integration guide explains how callers preserve those uses.

The sample keeps generic quality claims and administrative verb choices as
positive cases. The rule now preserves the named statistical method while
retaining generic claims, and omits the base-form suggestion for inflected
forms of the administrative verb. These changes neither exclude all technical
writing nor establish factual or grammatical correctness.

The original assessment retained all 10 intended warning findings and reduced
intentional-use alerts from 14 to 10. P12 subsequently corrected six technical
V001 uses without changing their negative annotations. Four raw quotation
alerts and two low-confidence evidence-association alerts remain visible in
the regression report. The [disposition ledger](assessment-disposition.md)
records all twelve original cases and distinguishes caller handling from
raw detection. These counts describe the sample, not a population estimate.

## Benchmark comparisons

Benchmark JSON retains its list envelope; each result now declares schema
version 1. Workload SHA-256 covers exact selected UTF-8 bytes and relative names.
Runtime identity uses the same imported-source digest as quality reports. The
complete diagnostic digest preserves paths, rule IDs, severity, confidence,
exclusive spans, messages, suggestions and multiplicity. Digest computation
occurs outside timed scan intervals. Repeated source or diagnostic changes fail
the measurement rather than producing a comparison across different behavior.

New-process CLI runs record an untimed child import/policy probe and actual
module locations. Compare timing results only with equal workload, effective
policy and diagnostic identities under comparable environments and cache
states. An implementation change may alter the runtime digest; that identity
must be recorded for each side of the comparison. Ordinary CLI output is unchanged.

## Reviewed regression gate

`--gate /path/to/reviewed-regression.json` enables strict regression comparison;
ordinary invocations remain report-only. A version 1 gate ledger records each
known FP/FN by source path, exact full span or expected label identity, and
review reason. It binds the annotation snapshot, source bytes, declared rule
contracts and named effective policy. Creation-time runtime identity records
the reviewed snapshot; changed implementations can be evaluated against it.

Known mismatches remain raw FP/FN observations in the report. An exact known
mismatch passes; a corrected one is listed as resolved. A new mismatch fails
even if the total stays equal. Duplicate identities and occurrence changes
cannot use a count allowance. JSON adds a separate `gate` result; text keeps
raw metrics and prints the comparison outcome. Exit codes are 0 for passing
comparison, 1 for a new reviewed regression, and 2 for invalid/stale provenance
or insufficient eligible review coverage.

Strict independent gating requires source-bound version 3 annotations and
explicit complete reviewed coverage, even when no finding is emitted or a
source is empty. The legacy version 1 curated corpus has a separate exhaustive
regression contract and ledger-bound immutable scan bytes. That exception does
not create independent annotation-time provenance. Gate records need manual
review before source/contract migration or removal of a resolved mismatch;
there is no automatic acceptance or refresh option.

`make rule-quality-regression` checks the two reviewed default ledgers under
their explicit all-rules and production policies. The ledgers retain the six
all-rules and four production false positives documented in the
[disposition ledger](assessment-disposition.md), with no known false negatives.
The original inputs and negative judgments remain unchanged. CI runs this
target separately from the report-only measurement.

## Explicit project context

M012 stays off in default production and the historical all-rules track; its
purpose-written positives/negatives remain recorded as policy exclusions.
An explicit context enables the optional track without configuration discovery:

```sh
rtk proxy .venv/bin/python -m benchmarks.rule_quality --mode all-rules --project-root quality/corpus/local-links --format json
```

The report records the effective absolute root and enable flag; strict gate
policy identity uses a root-relative declared project path where possible.
Production uses the same explicit context construction and rule policy as the
CLI. Input-file policy, confidence filtering and baseline exclusion remain.
Keep target context under review as well as the linked document. Natural blind
packets use numbered filenames and incomplete repository context; mark local
link coverage unsupported until native paths and required targets are preserved
and bound. Their existing source-byte binding alone cannot establish cross-file
link truth or independent M012 effectiveness.

Enabled local-link reports explicitly declare target/native-context binding
unavailable. `--require-bound` and source-bound version 3 strict gates reject
that enabled context until a target/native-path binding contract is available,
even with zero cross-file findings. Curated report-only optional measurements
remain available; the default reviewed gates keep the feature off.

## Human suggestion usefulness

Version 3 files may add a `usefulness` list. Each row names its review ID and a
header-declared reviewer, preserves the complete Issue-shaped diagnostic and its
canonical `diagnostic_sha256`, and supplies an `answers` object. The four keys
are `finding_helpful`, `suggestion_fits_sentence`, `meaning_preserved`, and
`reviewer_accepts`. Values are `yes`, `no`, `context-dependent`, `unresolved`,
or `unreviewed`; omitted answers stay unreviewed. Absent suggestions cannot
receive binary suggestion answers. Rated rules must belong to the packet's
reviewed contract snapshot, including trigger-only judgments. Renaming a duplicate
reviewer/prompt row cannot add another vote; distinct reviewers remain visible.

Rows also declare `revision` and `automatic_rescan`, using null when absent.
Revision provenance requires path, source ID/hash, original source ID and the
original packet's declared pair group. Local bytes and scope are validated.
Recorded mechanical observations name targeted resolution, new-warning count,
policy hash and runtime source hash. They are observations, not a verified
current run or inferred semantic success.

The JSON `usefulness` result separates emitted findings, distinct full-record
prompts, linked prompts/ratings/reviewers and unlinked historical ratings. Every
question reports yes/no denominator, context-dependent/unresolved/unreviewed
counts and an unavailable rate when binary responses are absent. Raw duplicate
emissions remain in the quality score even when they share a review prompt.
Current source/prompt changes make old ratings unlinked; missing human ratings
never become successful suggestions. No real human judgments are supplied by
the repository's synthetic validation fixtures.

## Reviewed native revision pairs

`benchmarks.paired_quality.paired_report()` accepts two minimal source-bound
evaluation records, their exact original/revision UTF-8 bytes, and an optional
explicit correspondence review. Each source names path, ID/hash, source group
and pair group; the revision names its original source ID. Records retain the
complete effective policy, runtime provenance and Issue-shaped findings. Actual
runtime package version/source digest and policy must agree; location or Git-only
metadata differences remain visible without changing comparison identity.

Correspondence names a reviewer/review ID and binds both source records. Each
row references full diagnostic hashes on one or both sides with explicit
valid/incorrect/context-dependent/unresolved judgments and the four separate
human questions. Diagnostic identity is unique; duplicates, changed source bytes,
wrong groups, ambiguous alignment and malformed spans are rejected. Production
single-line spans retain their null `end_line` and supplied `end_column`; M004
alone retains its zero-width exception.

The report preserves all provenance, mechanical finding/warning counts and
deltas, reviewed transitions, human status denominators and unmatched diagnostic
IDs. Missing correspondence or meaning judgments remain unavailable. No native
edit type, eliminated warning or reference text automatically supplies a useful
finding or preserved meaning. The offline tests use synthetic review outcomes;
actual independent paired evidence remains deferred.

## Source-group uncertainty

JSON reports retain separate precision, recall and warning/error false-positive
density counts for each identified source group. Variants in one group remain
together. Whole groups are sampled uniformly with replacement; each replicate
uses the ratio of summed counts. The predeclared procedure uses seed 20261010,
2,000 replicates and interpolated 2.5/97.5 percentiles, with at least five
contributing identified groups for each metric.

Reports show contribution sizes, the dominant denominator share and the exact
reason an interval is unavailable. Clean reviewed groups can support density
without supplying precision or recall observations. Unknown groups, inadequate
support and missing denominators cannot produce an interval. These intervals
are conditional on observed pilot source groups; they provide no proof of a
representative population. They do not replace independent human annotation.
