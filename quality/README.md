# Rule-quality corpus

This directory contains reviewed document-like inputs for measuring rule
precision and recall. It complements unit tests: unit tests prove that a pattern
can fire, while this corpus records whether findings are correct in surrounding
technical, academic, business, journalistic, changelog, and Python content.

## Evaluation policy

`make rule-quality` retains the historical all-rules measurement with
informational findings and low minimum confidence. It uses explicit defaults
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
manifest and source checksums, counts, and mismatch details. They retain the
exact-start scoring definition. Rule/severity/file-policy exclusions are
reported separately from missed eligible findings.

`annotations.json` also references selected files under `tests/fixtures/` so
existing examples remain the single source for those cases.

## Annotation rules

- `expected` entries match findings by exact path, rule ID, line, and column.
- `negative_cases` identify lines on which a named rule must not fire.
- Any emitted finding without an expectation is a false positive.
- Any expectation without an emitted finding is a false negative.
- Do not turn a known false positive into an expectation to improve the score.

Every registered rule must have at least one expected finding and one explicit
negative case. The evaluator rejects unknown rules, duplicate locations,
out-of-range positions, missing files, and paths outside the repository.

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

At the default warning threshold, the sample retained all 10 intended findings
and reduced intentional-use alerts from 14 to 10. The full evaluator also
retained two intended informational findings. No pre-existing corpus findings
changed. These counts describe this sample, not a population precision estimate.
