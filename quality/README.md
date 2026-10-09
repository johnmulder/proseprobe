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

The JSON schema version is 2. Reports include rule, policy, severity, confidence,
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
