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
