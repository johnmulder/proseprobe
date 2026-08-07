# Rule-quality corpus

This directory contains reviewed document-like inputs for measuring rule
precision and recall. It complements unit tests: unit tests prove that a pattern
can fire, while this corpus records whether findings are correct in surrounding
technical, academic, business, journalistic, changelog, and Python content.

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
