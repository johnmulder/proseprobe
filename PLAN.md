# ProseProbe improvement plan

Status: original engineering packages and their local verification complete.
Reassessment packages P18–P33 are in progress; their checks and records appear below.
Independent human evaluation and the listed external gates remain pending.
Assessment date: 2026-10-09.

Start new work at [Reassessment continuation](#reassessment-continuation).
P00–P17 and their execution records remain historical evidence. An existing
checked item does not complete a new regression or acceptance gate below.

This plan covers the discovery and parser defects, evaluation gaps, heuristic
refinements, new rules, and public datasets identified in the project assessment.
Each numbered task is a small unit of work that can be reviewed on its own.
Complete prerequisites before starting a dependent task.

## Working contract

- Write a failing regression test before changing behavior. Confirm that it
  fails for the intended reason, make the smallest correction, and rerun it.
- Reuse existing tests when they already establish a contract. Add assertions
  for missing behavior rather than duplicating tests that already pass.
- For extraction or policy refactors, characterize current behavior before
  moving code. Compare results before and after the move.
- Keep changes within each work package. Do not combine a parser correction,
  a new rule, and a measurement refactor in one patch.
- Preserve meanings, exact quotations, diagnostic ordering, source coordinates,
  exit codes, baseline durability, and documented configuration precedence.
- Use the existing standard-library parsing and rule interfaces. Add no runtime
  dependencies, model calls, rewrite mode, or network access to the linter.
- Keep rule IDs stable. Document deliberate changes to detection, confidence,
  severity, configuration, or baseline identity.
- Do not improve reported scores by accepting false positives, weakening tests,
  adding blanket ignores, or refreshing the baseline without review.
- Finish each behavior slice with its focused tests, `make check`, and the
  relevant documentation and corpus checks described in P17.

The examples below are test inputs. Preserve their exact wording when turning
them into fixtures. A rule addition starts with narrow behavior; wider coverage
requires new evidence and its own test-first slice.

## Assessment snapshot and scope

The assessment ran the local gate on Python 3.13: 1,990 tests passed, along with
linting, type checking, and generated-document verification. The documentation
scan passed with the existing baseline. These results do not replace the
Python 3.11–3.13 CI matrix or the release gates.

The existing corpus contained 58 files, 301 positive annotations, and 403
negative cases. Its all-rule report showed 301 true positives, 12 false
positives, and no missed expectations: 96.2% precision and 100% recall on that
corpus. Warning-only findings had 88 true positives and 10 false positives,
or 89.8% precision. Thirty-five rules had one positive example; forty-five
had one explicit negative example.

Keep these figures as an assessment snapshot. Record fresh results and the
commit identifier before implementation rather than treating these counts as
permanent test expectations.

The benchmark currently calls rules directly. Some rule calls already share
parser caches, so direct calls do not establish repeated parsing as a
bottleneck. P07 measures cache behavior and the full scan path before proposing
performance changes.

## Order and dependencies

| Package | Work | Prerequisites |
| --- | --- | --- |
| P00 | Record baseline evidence | None |
| P01 | Relative paths and Git ignores | P00 |
| P02 | Unicode Python source coordinates | P00 |
| P03 | Markdown fence information strings | P00 |
| P04 | Shared effective scan policy | P00 |
| P05 | Evaluation scopes and source spans | P04 |
| P06 | Independent corpora and dataset adapters | P05; planning may begin at P00 |
| P07 | Full-scan performance measurements | P01–P04; corpus samples from P06 |
| P08 | Line-wrap-independent phrase detection | P02, P03; freeze holdout sources in P06 |
| P09 | Hedge stacking precision | P08 |
| P10 | Claim-local evidence | P05, P06, P08 |
| P11 | Overlapping phrase diagnostics | P05, P08 |
| P12 | Technical vocabulary and quotation handling | P05, P06, P08 |
| P13 | Repeated adjacent function words | P05, P06, P08 |
| P14 | Stale docstring parameter declarations | P02, P05, P06 |
| P15 | Optional same-document fragment checks | P03, P05, P06; renderer decision required |
| P16 | Effectiveness review and confidence calibration | P06 and each evaluated rule slice |
| P17 | Documentation, integration, and completion gates | Each package; final run after P16 |

P01–P04 can use separate patches in parallel. Dataset provenance and annotation
design can proceed alongside them. Reserve holdout sources before tuning rules;
never tune on examples later described as independent evaluation data.

## P00 — Record baseline evidence

Targets: existing test suite, `quality/annotations.json`, benchmark commands.

- [x] P00.1 Record the current commit, working-tree state, Python version, and
  effective default scan configuration.
- [x] P00.2 Run `make check`, `make dogfood`, and `make rule-quality`; retain the
  commands, counts, and any failures with the commit identifier.
- [x] P00.3 Reproduce the three infrastructure defects using disposable fixtures;
  retain exact inputs and outputs for P01–P03.
- [x] P00.4 Record rule-quality results by severity and confidence without changing
  the corpus annotations or the production scan policy.
- [x] P00.5 Inventory existing tests for each later package. Note which intentional
  behavior expectations require revision and why.

Acceptance: baseline evidence can be reproduced, and no implementation or
annotation changes have been mixed into the measurement.

## P01 — Make relative directory scans honor Git ignores

Targets: `src/proseprobe/core/linter.py`, `tests/test_linter.py`,
`tests/test_cli.py`.

- [x] P01.1 Add a failing discovery test in a temporary Git repository with
  `/docs/ignored.md` in `.gitignore`, invoking discovery with `Path("docs")`.
  Assert that the ignored file is absent and an ordinary sibling is present.
- [x] P01.2 Add a test comparing relative and absolute scans of the same directory.
  Compare selected file identities while retaining the documented output paths.
- [x] P01.3 Correct the coordinate system passed to `git check-ignore`: send
  absolute candidates or paths relative to its working directory, then map the
  results back to discovery candidates.
- [x] P01.4 Cover overlapping roots and a filename containing spaces. Preserve
  NUL-delimited input and output handling.
- [x] P01.5 Verify the existing explicit-file override: an explicitly named file
  retains its current Git-ignore behavior, and configured exclusions still apply.
- [x] P01.6 Preserve behavior outside Git repositories and when Git is unavailable.
  Reuse existing tests unless one of these branches lacks coverage.
- [x] P01.7 Add a CLI regression for `check docs` that asserts findings and
  `files_checked`, rather than testing only the discovery helper.
- [x] P01.8 Run the focused discovery and CLI tests, then the package gate.

Acceptance: relative and absolute directory scans select the same files without
changing explicit-file policy, path reporting, or failure handling.

## P02 — Use one coordinate system for Python source mapping

Targets: `src/proseprobe/parsers/python.py`, `tests/test_parsers/test_python.py`,
`tests/test_linter.py`, existing reporter tests.

- [x] P02.1 Add a failing extraction test for `def résumé(): """delve"""` and
  compare its extracted prose with the ASCII-name counterpart.
- [x] P02.2 Assert the V001 start and exclusive end columns against the original
  Unicode source, using character positions rather than UTF-8 byte positions.
- [x] P02.3 Add boundary cases with a non-ASCII parameter name, a multibyte string
  character, and adjacent literal tokens in a docstring.
- [x] P02.4 Add the smallest conversion from AST byte offsets to character
  offsets. Apply it to both start and end boundaries used for token selection.
- [x] P02.5 Audit other AST-coordinate consumers, including string-literal
  extraction. Add a regression and change a consumer only if it has the same
  mismatch or violates an existing source-position contract.
- [x] P02.6 Verify multiline docstrings, comments, async functions, and malformed
  Python using existing cases plus any missing Unicode assertion.
- [x] P02.7 Exercise the corrected finding through JSON Lines and SARIF; assert
  valid original-source spans and unchanged field semantics.
- [x] P02.8 Add a corpus positive and a nearby Unicode negative case, then run the
  parser, linter, reporter, and package checks.

Acceptance: valid Unicode Python documentation is extracted, and every reported
position points into the original source without shifting ASCII findings.

## P03 — Parse Markdown fence information strings

Targets: `src/proseprobe/parsers/markdown.py`,
`tests/test_parsers/test_markdown.py`, `tests/test_rules/test_markup.py`,
`tests/test_linter.py`.

The primary regression fixture is:

````text
```python title="example.py"
x = "delve"
```
````

- [x] P03.1 Add a failing parser test asserting one closed block, language
  `python`, and the correct opening and closing lines for this fixture.
- [x] P03.2 Add a failing linter test asserting no V001 finding inside the block
  and no M007 unclosed-fence error.
- [x] P03.3 Separate opening delimiter recognition from the information string.
  Retain the first information token as the language where the existing API
  requires it; accept remaining information without interpreting attributes.
- [x] P03.4 Test backtick and tilde fences, multiple information tokens, empty
  information, and attribute-only forms. Keep invalid backtick information
  strings distinct from valid tilde information strings.
- [x] P03.5 Preserve strict closing rules: matching delimiter character,
  sufficient delimiter length, and no trailing closing information.
- [x] P03.6 Verify indentation limits, blockquoted fences, shorter embedded
  delimiters, and source columns using the existing parser contracts.
- [x] P03.7 Retain a positive M007 test for a genuinely unclosed fence with
  attributes, reported at its opening delimiter.
- [x] P03.8 Add a quality-corpus negative for the valid fixture and run the parser,
  markup, linter, and package checks.

Acceptance: valid code remains masked from prose checks, while malformed or
unclosed fences still produce accurate diagnostics.

## P04 — Share effective scan policy with evaluation

Targets: `src/proseprobe/cli.py`, `src/proseprobe/core/`, `src/proseprobe/config.py`,
`benchmarks/rule_quality.py`, `tests/test_cli.py`, `tests/test_rule_quality.py`.

- [x] P04.1 Characterize policy precedence for configured profiles, CLI profiles,
  explicit selections, ignores, severity overrides, and confidence filtering.
  Reuse the existing CLI tests as the reference behavior.
- [x] P04.2 Add an evaluator-to-CLI parity test on one controlled Markdown file
  and one Python file. Compare complete issue records after normalizing only
  path presentation and output envelopes.
- [x] P04.3 Extract only reusable policy construction and result filtering into
  core. Keep argument parsing, configuration discovery, and operational output
  in their existing layers; do not create a new framework.
- [x] P04.4 Add evaluator options for profile, minimum severity, and minimum
  confidence, and test their parsing and invalid-value diagnostics.
- [x] P04.5 Preserve a named all-rules measurement mode for the existing corpus,
  including experimental rules. Label it separately from default CLI behavior.
- [x] P04.6 Add parity cases for every built-in profile, no-profile behavior,
  experimental-rule selection, per-file ignores, and inline suppressions.
- [x] P04.7 Keep baseline filtering out of raw effectiveness measurements.
  Test baselined adoption behavior separately so accepted debt cannot inflate
  reported precision or recall.
- [x] P04.8 Report effective policy, package version, corpus identity, and metric
  counts in a deterministic machine-readable evaluation result.
- [x] P04.8a Test that ambient repository or user configuration cannot change a
  frozen evaluation run. Use explicit isolated evaluation configuration, while
  preserving the CLI's ordinary configuration discovery.
- [x] P04.9 Verify that `check`, stdin, `watch`, and baseline maintenance retain
  their existing policy and exit-code contracts after extraction.
- [x] P04.10 Run CLI, configuration, profile, evaluator, and package checks.

Acceptance: production-policy evaluation matches the CLI, and all-rules results
remain available with an explicit label and unchanged legacy interpretation.

## P05 — Separate annotation scope, detection, and location scoring

Targets: `benchmarks/rule_quality.py`, `quality/annotations.json`,
`quality/README.md`, `tests/test_rule_quality.py`.

- [x] P05.1 Add failing tests proving that supplied `end_line` and `end_column`
  survive loading and finding collection. Preserve legacy annotations without
  endpoints as start-only checks.
- [x] P05.2 Validate endpoint order, nonempty concrete spans, and bounds. Keep
  explicitly permitted zero-width findings distinct from malformed spans.
- [x] P05.3 Add a scoring case with a correct start and an incorrect end. Require
  detection credit to remain separate from a failed span-accuracy check.
- [x] P05.4 Add cases for an incorrect start, a missing finding, and duplicate
  findings. Preserve strict exact-location scoring and one-to-one matching.
- [x] P05.5 Define separately reviewed semantic matches, using stable annotation
  identities or explicit span correspondence. Do not turn arbitrary overlapping
  findings into correct detections.
- [x] P05.6 Define annotation coverage for external corpora by file, rule family,
  and prose region. Introduce explicit unreviewed and unsupported outcomes for
  material outside that coverage.
- [x] P05.7 Test that an unmatched finding is a false positive only where
  annotations are exhaustive for the evaluated rule and region.
- [x] P05.8 Test recall denominators: exclude rules outside the declared policy
  or annotation scope; count eligible positives removed by confidence filtering
  as missed detections. Never derive eligibility from whether a rule fired.
- [x] P05.9 Preserve strict every-rule positive/negative coverage for the current
  regression corpus. Permit sparse external coverage through a documented
  manifest extension or separate loader, with tests for legacy compatibility.
- [x] P05.9a Support narrow negative regions in external annotations. Test a valid
  use and a genuine same-rule violation on one line so a line-wide negative
  cannot conceal the distinction. Preserve legacy line-wide negative cases.
- [x] P05.10 Keep context-dependent adjudications visible. Report how many cases
  are unresolved instead of omitting them from headline metrics.
- [x] P05.11 Add severity, confidence, file-type, and profile breakdowns with
  denominators. Test empty groups and deterministic ordering.
- [x] P05.12 Document the schema and scoring definitions; rerun legacy scores and
  explain any change before adopting the new report.

Acceptance: detection quality, source-location accuracy, policy coverage, and
annotation completeness can be assessed separately without hiding mismatches.

## P06 — Build an independent evaluation corpus

Targets: `quality/`, evaluation-only adapters under `benchmarks/`,
`tests/test_rule_quality.py`, new adapter tests where needed.

### P06A — Provenance, sampling, and annotation

- [x] P06A.1 Define a source manifest with URL, revision, checksum, license,
  attribution, source identity, format, and evaluation split.
- [x] P06A.2 Test rejection of missing provenance, duplicate sample identities,
  invalid splits, and paths escaping the permitted corpus location.
- [x] P06A.2a Test a corrupted cached sample and validate its checksum before
  conversion. Keep downloads outside unit tests and external datasets outside
  the published package unless their inclusion is deliberate and licensed.
- [x] P06A.3 Establish a few-hundred-sample pilot across complete Markdown
  documents, Python docstrings, and comments. Record format and genre counts;
  size alone does not establish representativeness.
- [x] P06A.4 Freeze development and holdout source identities before rule tuning.
  Split by repository, document, or author as appropriate; keep related revisions
  and before/after pairs in the same split.
- [x] P06A.5 Test split isolation, including duplicates and near-identical
  excerpts when their source identities are available.
- [x] P06A.5a Assign GitHub Docs to one split because it is one repository. Obtain
  additional verified, licensed documentation sources for the other splits;
  keep the GitHub Docs revision and its excerpts together.
- [x] P06A.6 Write annotation guidance for useful findings, false positives,
  context-dependent cases, missed issues, and correct source spans.
- [ ] P06A.7 Sample random prose as well as triggered findings. Fully annotate
  eligible regions when measuring recall; a warning-only review cannot supply
  a recall denominator.
- [ ] P06A.7a Complete the initial annotation of random prose before reviewers
  see detector predictions. Review triggered findings afterward in a separately
  identified pass, retaining independently found issues as ground truth.
- [ ] P06A.8 Obtain independent human review of the pilot. Double-annotate a
  subset, record disagreements, and retain the adjudication rationale.
- [ ] P06A.9 Add independently authored positive and near-miss cases for rules
  with sparse coverage. Label purpose-written cases separately from natural text.
- [x] P06A.10 Preserve the original 12 false-positive cases as honest regression
  evidence. Record whether each is corrected, explicitly handled by policy, or
  retained as a documented limitation.

### P06B — Technical Markdown and Python

- [x] P06B.1 Pin a [GitHub Docs](https://github.com/github/docs) revision and select
  full Markdown files with headings, links, frontmatter, tables, fences, and
  Liquid markup. Record its CC BY 4.0 content license and attribution.
- [x] P06B.2 Add a tiny offline fixture and a failing loader test that preserves
  source text and source identity. Load samples without running templates or
  treating repository content as instructions.
- [ ] P06B.3 Annotate the selected files. Treat published documentation as
  candidate negative material, never as guaranteed error-free ground truth.
- [x] P06B.4 Select the Python subset of
  [CodeSearchNet](https://github.com/github/CodeSearchNet). Record upstream
  repository and license metadata; its project MIT license does not replace
  the data's upstream licenses.
- [x] P06B.5 Test a tiny CodeSearchNet JSON Lines adapter for function source,
  docstring text, repository identity, and missing fields. Preserve source
  offsets where available and declare missing surrounding module context.
- [ ] P06B.6 Annotate writing quality independently. Keep code-search relevance
  annotations outside prose-quality scoring.

### P06C — Grammar and fluency

- [x] P06C.1 Select the development material from
  [W&I+LOCNESS / BEA-2019](https://www.cl.cam.ac.uk/research/nl/bea2019st/),
  recording its non-commercial restriction and archive checksum.
- [x] P06C.2 Test a tiny M2 reader for token spans, insertions, deletions, no-op
  annotations, and multiple annotators. Do not merge incompatible annotator edits.
- [ ] P06C.3 Map only supported error types to relevant rules. Record unsupported
  categories and automatically assigned ERRANT types separately.
- [x] P06C.4 Test token-to-source mapping and detokenization around punctuation
  and contractions. Report preprocessing artifacts separately from rule errors.
- [x] P06C.5 Load [JFLEG](https://github.com/keisks/jfleg) source sentences and all
  four human corrections. Record its CC BY-NC-SA 4.0 license.
- [x] P06C.6 Test pair identity, missing references, and split preservation on
  small offline files before loading the full selected subset.
- [ ] P06C.7 Review relevant warning changes across source and corrected variants.
  Use detection and actionability metrics; generated-text GLEU scores do not
  directly measure this linter.

### P06D — Simplification and software revisions

- [x] P06D.1 Load [ASSET](https://github.com/facebookresearch/asset) originals and
  ten human simplifications, recording its CC BY-NC 4.0 license.
- [x] P06D.2 Test pair identity and references on a tiny offline fixture. Restrict
  interpretation to sentence-level clarity and complexity rules.
- [ ] P06D.3 Review whether relevant warnings disappear after a human revision,
  remain useful, or appear incorrectly. Never treat fewer warnings as sufficient
  evidence of a better revision.
- [x] P06D.4 Recheck access and licensing for the replication package linked by
  the [GitHub README simplification study](https://arxiv.org/abs/2308.09940).
  Record an unresolved-access outcome if its package remains unavailable.
- [ ] P06D.5 If access and terms permit use, test a revision-pair adapter and
  manually verify sampled edits. Keep commit-keyword labels classified as weak
  evidence rather than confirmed clarity improvements.

Acceptance: datasets are reproducible, licensed for the intended evaluation,
and independently annotated where their native labels do not match the rules.
Corpus download and adaptation remain development activities; scans stay offline.

## P07 — Measure the full scan path before optimizing it

Targets: `benchmarks/bench_rules.py`, existing performance probes,
`tests/test_benchmarks.py`, `SPEC.md`.

- [x] P07.1 Retain the direct-rule benchmark and label what it measures.
- [x] P07.2 Characterize Markdown and Python parser construction counts in direct
  rule calls and in `Linter`. Distinguish warmed caches from cleared caches.
- [x] P07.3 Add a failing runner test that proves the full-scan measurement uses
  production policy, file discovery, reading, extraction, and result filtering.
- [x] P07.4 Add a small offline workspace with both file types, an ignored file,
  and known findings; assert selected files and result equivalence.
- [x] P07.5 Measure cold-process CLI startup separately from warmed scan timing.
  Include serialization when reporting whole-CLI timing; identify the output
  format and keep it fixed across comparisons.
- [x] P07.6 Add representative corpus samples, then report median timing,
  variation, bytes processed, files checked, active rule count, and environment.
- [x] P07.7 Test rate calculations with controlled durations. Use actual batch
  bytes and elapsed time rather than deriving throughput from an unweighted
  average across differently sized synthetic files.
- [x] P07.7a Test Unicode workloads and compute byte throughput from UTF-8 byte
  length. Include many distinct small files as well as repeated content, so cache
  pressure and cache-friendly measurements remain distinguishable.
- [x] P07.8 Keep wall-clock thresholds out of ordinary unit tests. Preserve the
  repository's existing startup and memory gates.
- [x] P07.9 Profile only measured slow paths. Propose a separate measured
  correction if the evidence warrants a cache, traversal, or concurrency change.

Acceptance: benchmark results describe the path measured and can support a
before/after comparison. No optimization is required merely to finish this plan.

## P08 — Make phrase detection independent of line wrapping

Targets: `src/proseprobe/rules/vocab.py`, `src/proseprobe/parsers/prose.py`,
`tests/test_rules/test_vocab.py`, `tests/test_linter.py`, baseline tests.

- [x] P08.1 Add a failing V009 pair for the same phrase on one line and wrapped:
  `due to the fact that` versus `due to the\nfact that`.
- [x] P08.2 Assert both source endpoints for the wrapped phrase in Markdown and
  Python documentation. Preserve the single-line diagnostic contract.
- [x] P08.3 Add negative cases crossing a paragraph, heading, list item, separate
  docstring, or comment/prose boundary.
- [x] P08.4 Add a masked-gap negative such as `in \`sorted\` order to`. Matching
  whitespace must not manufacture a phrase across hidden code or markup.
- [x] P08.5 Move the shared replacement-table matcher to source-mapped sentences.
  Accept layout whitespace only within one permitted prose region and verify
  the original source covered by a candidate match.
- [x] P08.6 Cover the other helper consumers separately: V010, V011, V013, and
  V017. Adapt V011's decision-compound exception to complete multiline spans.
- [x] P08.7 Inventory older literal phrase matchers. Migrate each affected matcher
  only after its own failing wrap-invariance test; do not rewrite unrelated rules.
- [x] P08.8 Characterize inline suppression and baseline behavior for multiline
  matches. Verify that distinct matches cannot share an accidental identity.
- [x] P08.9 If those tests expose a baseline defect, design the smallest correction
  with compatibility tests before changing stored identities. Preserve existing
  readable baseline versions and atomic writes.
- [x] P08.10 Add wrap variants to the corpus, compare all changed findings, and
  run focused rule, mapping, baseline, and package checks.

Acceptance: wrapping alone does not alter supported phrase detection, and spans
remain accurate without joining unrelated or masked content.

## P09 — Narrow hedge stacking

Targets: `src/proseprobe/rules/grammar.py`,
`tests/test_rules/test_grammar.py`, quality-corpus cases.

- [x] P09.1 Add a failing negative for `The cache may expire, or the server might
  restart.` Assert that separate alternatives do not receive a high-confidence
  stacking diagnostic.
- [x] P09.2 Retain a positive for `may possibly`, with exact span, high confidence,
  and the existing modal suggestion.
- [x] P09.3 Add coordinated independent clauses, distinct sentences, and a
  genuinely redundant stack, including wrapped variants.
- [x] P09.4 Add conservative clause guards for recognized separate propositions.
  Lower confidence where the sentence-wide count remains ambiguous rather than
  claiming certainty from the count alone.
- [x] P09.5 Preserve phrase-level metadiscourse checks and prevent duplicate
  diagnostics inside a confirmed redundant-modal span.
- [x] P09.6 Verify profile confidence filters and add corpus positives and
  negatives for the distinctions above.

Acceptance: redundant hedges remain detectable, while independently qualified
claims no longer receive unjustified high-confidence stacking alerts.

## P10 — Require evidence to qualify the matched claim

Targets: evidence helpers and V015/V016 in `src/proseprobe/rules/vocab.py`,
`tests/test_rules/test_vocab.py`, quality-corpus cases.

### P10A — Comparatives and superlatives

- [x] P10A.1 Add a failing positive for `Release 4 is the fastest parser.` An
  unrelated version number must not exempt the superlative.
- [x] P10A.2 Add negatives for a directly stated comparison with metric and scope,
  such as `In this benchmark, A was fastest among the three tested parsers.`
- [x] P10A.3 Test unrelated dates, ports, people, links, and numbers in adjacent
  sentences, including a different subject in the same paragraph.
- [x] P10A.4 Replace presence-only evidence checks with narrow claim-local
  qualification. For uncertain association, retain a lower-confidence review
  prompt instead of treating the claim as proven.
- [x] P10A.5 Keep V015 experimental until P16 supplies sufficient independent
  precision evidence. Preserve current profile membership unless deliberately
  changed after review.

### P10B — Reliability assertions

- [x] P10B.1 Add a failing positive for `The parser was tested over 100 runs.
  The parser never fails.` Finite testing must not exempt the universal assertion.
- [x] P10B.2 Add a negative for the bounded observation `The parser never failed
  during those 100 runs.` Assert that the bound qualifies the same observation.
- [x] P10B.3 Replace any current test that exempts an unbounded assertion merely
  because a neighboring sentence reports testing. Retain its old input as a
  positive regression with a documented expectation change.
- [x] P10B.4 Test tense changes, unrelated subjects, explicit tested conditions,
  and a sentence containing both a bounded observation and an unbounded claim.
- [x] P10B.5 Narrow the bound association without attempting general factual
  verification. Preserve findings where the qualification is unresolved.
- [x] P10B.6 Verify V016 profile behavior and source spans, then review all corpus
  mismatches introduced by the new evidence policy.

Acceptance: evidence of an observation cannot silently validate an unrelated
comparison or a universal claim. Detection still describes a prose issue rather
than asserting whether a claim is factually true.

## P11 — Remove redundant overlapping phrase alerts

Targets: `src/proseprobe/data/phrases.py`, V002/G009, corresponding rule tests,
metadata, output, and quality tests.

- [x] P11.1 Add a failing test for `Let's dive into the API.` asserting one
  longest phrase match per rule, rather than both prefix matches.
- [x] P11.2 Test repeated nonoverlapping occurrences so deduplication does not
  hide a second occurrence elsewhere in the sentence or document.
- [x] P11.3 Resolve contained matches locally within each affected rule. Preserve
  accurate spans, ordering, and independently meaningful overlapping rules.
- [x] P11.4 Inventory phrases owned by both V002 and G009. Define which rule
  owns each identical diagnosis and record the reason.
- [x] P11.5 Add tests for selecting V002 alone, G009 alone, and both rules before
  changing shared-pattern ownership. Preserve useful explicit-selection behavior.
- [x] P11.6 If ownership would break that contract, specify grouping that retains
  each rule ID and machine-output meaning before changing presentation. Do not
  add an undocumented JSON/SARIF shape or suppress findings globally.
- [x] P11.7 Verify inline suppression, baseline matching, metadata descriptions,
  and corpus expectations for the chosen ownership or grouping behavior.

Acceptance: one phrase does not produce repeated copies of the same diagnosis;
distinct diagnoses and explicit rule selections remain understandable.

## P12 — Preserve technical meanings and exact quotations

Targets: V001/V002/V004, vocabulary data, Python/Markdown context helpers,
`tests/test_rules/test_vocab.py`, technical-review corpus, agent guidance.

- [x] P12.1 Inventory all 12 existing false positives and classify their causes:
  technical sense, literal quotation, or evidence association.
- [x] P12.2 Add paired tests for technical constructions and generic uses of
  `key`, `significant`, `fundamental`, and `implement` inflections. Include cases
  where a valid technical term shares a sentence with a separate prose violation.
- [x] P12.3 Add narrowly scoped context exceptions for reviewed constructions,
  covering case, inflection, wrapping, and Markdown/Python parity.
- [x] P12.4 Preserve the existing `robust regression` exception and reject
  unrelated same-line exemptions. Do not silently change the documented
  whole-line `allowed_phrases` contract while adding built-in span checks.
- [x] P12.5 Deliberately revise tests that currently require warnings on recognized
  technical uses. Keep generic administrative uses as positives and document
  the changed policy rather than deleting inconvenient tests.
- [x] P12.6 Test that suggestions fit the source form and meaning. Omit a
  suggestion when the rule cannot provide a valid replacement.
- [x] P12.7 Retain linting of ordinary blockquotes: a draft callout and an exact
  quotation can use the same Markdown syntax.
- [x] P12.8 Verify the existing narrow suppression mechanism for an explicitly
  preserved quotation. Add only missing tests; do not infer quote intent from
  typography alone or add blanket quotation exemptions.
- [x] P12.9 Document residual raw-detector quotation findings and caller handling.
  Keep raw-corpus false positives visible; report policy-handled cases separately.
- [x] P12.10 Add journalism contrasts for a named source and a quantified trend.
  Inspect V005/V008 association with following context; retain low confidence
  when support cannot be safely associated with the matched claim.
- [ ] P12.11 Compare precision and retained generic positives on development
  samples, then evaluate once on reserved holdout material through P16.

Acceptance: technical exceptions preserve the intended meaning without masking
other findings. Exact quotation handling is explicit, and unresolved detector
limitations remain visible in evaluation.

## P13 — Add repeated adjacent function-word detection

Targets: grammar rules, registry, profiles, rule tests, metadata/docs, corpus.

- [x] P13.1 Define a small reviewed vocabulary of likely accidental function-word
  repetitions and choose a new unused rule ID from canonical metadata.
- [x] P13.2 Add a failing positive for `Read the the configuration.` Assert the
  repetition span and a conservative suggestion.
- [x] P13.3 Add a positive for `with with`, including a wrapped occurrence and
  Python docstring/comment cases.
- [x] P13.4 Add negatives for `had had`, `that that`, punctuation-separated words,
  proper names, inline code, fenced examples, and separate prose blocks.
- [x] P13.4a Define which word span a repeated run reports. Test case variation
  and a three-word run, requiring one finding for its duplicated tail.
- [x] P13.5 Detect only the declared vocabulary in source-mapped prose. Do not
  generalize to arbitrary repeated words or infer intentional quoted examples.
- [x] P13.6 Verify explicitly preserved quotations through the established
  suppression policy, with raw findings reported honestly where intent is absent.
- [x] P13.7 Register the rule as experimental first and specify initial severity
  and confidence. Test normal default scans as well as profiles: experimental
  classification alone does not exclude a rule from legacy all-category scans.
- [ ] P13.8 Complete the new-rule checklist in P17, then measure independent
  precision before proposing profile promotion.

Acceptance: the rule catches the stated typing errors and leaves legitimate
repetition and masked content alone, without making authorship claims.

## P14 — Add stale docstring parameter declarations

Targets: `src/proseprobe/parsers/python.py`, `src/proseprobe/rules/code.py`,
parser/code tests, registry, metadata/docs, corpus.

- [x] P14.1 Add a failing test for a function accepting `url` and `timeout` whose
  docstring declares `:param retries:`. Assert a span on the stale declaration.
- [x] P14.2 Characterize parser parameter metadata for positional-only,
  positional, keyword-only, variadic, and bound-method parameters.
- [x] P14.3 Preserve parameter kinds and `**kwargs` presence in the smallest
  metadata extension needed by the rule. Test a normal function parameter named
  `self` or `cls` separately from actual bound-method conventions. Leave C007's
  existing normalized parameter tuple unchanged.
- [x] P14.4 Add positives for a renamed parameter and a misspelled declared name;
  add negatives for valid declarations and absent documentation.
- [x] P14.5 Start with explicit Sphinx `:param` fields. Test typed forms,
  indentation, multiline descriptions, and source mapping; reject prose that
  merely mentions the same text without a supported field declaration.
- [x] P14.5a Mask recognized docstring examples before extracting declarations.
  Test literal field examples, escaped content, and concatenated source strings
  so diagnostic coordinates come from source-aligned documentation.
- [x] P14.6 Skip module/class documentation and unsupported runtime signatures.
  With delegated `**kwargs`, retain conservative behavior instead of declaring
  every extra documented keyword stale.
- [x] P14.7 Compare declared names against the owning function's signature.
  Keep this distinct from C007's opening-sentence/signature repetition check.
- [x] P14.8 Test nested functions, methods, async functions, and Unicode names.
  Assert that a declaration is paired with the correct owner.
- [x] P14.9 Add the rule as experimental with explicit defaults and complete P17.
- [x] P14.10 Defer Google/NumPy sections until each format has tested boundaries
  and independent samples. Treat each added format as a separate later slice.

Acceptance: explicit stale declarations are actionable; missing documentation,
delegated keywords, and unsupported formats do not become new violations.

## P15 — Add optional same-document fragment validation

Targets: Markdown parser/markup rules, configuration, registry, metadata/docs,
parser/configuration/markup tests.

- [x] P15.1 Choose and document one supported renderer's anchor policy using its
  primary specification. Record heading slug rules, duplicate headings, explicit
  anchors, URL encoding, and supported Markdown extensions.
- [x] P15.2 Keep fragment validation disabled by default through an explicit,
  validated renderer/anchor setting. Add a failing default-off test before
  registering the rule; experimental classification alone is insufficient.
- [x] P15.3 Add a failing enabled-rule positive for `[installation](#install)`
  without a matching heading or supported explicit anchor.
- [x] P15.4 Add negatives for a matching heading, supported explicit anchor,
  duplicate-heading suffix, and encoded destination under the declared policy.
- [x] P15.4a Establish direct-link destination extraction with titles and
  delimiters before comparing fragments. Test explicit HTML anchors in non-code
  source separately from heading extraction; do not infer them from heading text.
- [x] P15.5 Test that external URLs and cross-file fragments are outside this
  rule's scope. Skip empty fragments and images. Do not fetch pages or add
  cross-repository link checking.
- [x] P15.6 Handle reference-style links at their definition destination span.
  Test several uses of one broken definition and require one finding there.
- [x] P15.7 Preserve direct-link destination spans and mask code examples. Mark
  generated Liquid/MDX anchors as unsupported where the policy cannot resolve them.
- [x] P15.8 Test invalid configuration, explicit enablement, renderer configuration
  in metadata, profile interaction, and disabled-default behavior.
- [ ] P15.9 Complete P17 and evaluate against documents using the chosen renderer.
  Record unsupported dialects as such rather than as false positives.
- [x] P15.9a Add an explicitly enabled renderer policy to the all-rule corpus
  track and its provenance. Test corpus coverage for the optional rule without
  changing production defaults or pretending disabled rules emitted findings.

Acceptance: opted-in checks resolve only the declared anchor policy, produce
accurate destination spans, and leave default scans unchanged.

## P16 — Evaluate usefulness and calibrate confidence

Targets: evaluator reports, held-out corpus, annotation guidance, CI measurement.

- [x] P16.1 Add deterministic metric tests for precision, eligible-issue recall,
  false warnings per 1,000 prose words, and source-span accuracy.
- [x] P16.2 Define the prose-word denominator from eligible extracted prose.
  Exclude masked code and report separate Markdown, docstring, and comment totals.
- [x] P16.3 Add confidence intervals and sample sizes for per-rule precision.
  Test empty denominators and small samples; do not report certainty from one case.
- [x] P16.3a Account for findings grouped within source repositories. Use
  source-cluster-aware uncertainty where sufficient sources support it; otherwise
  state that simple intervals describe only the reviewed sample.
- [x] P16.4 Report both totals across findings and averages across supported rules,
  with rare rules and unsupported/unreviewed cases visible.
- [x] P16.4a Report source-level variation where sample sizes permit. Do not treat
  many sentences from one repository as independent evidence from many projects.
- [x] P16.5 Review default warning/error behavior separately from all-rule and
  informational results. Keep high-confidence failures visible even when the
  aggregate score improves.
- [ ] P16.6 Assess whether a warning leads to a useful, meaning-preserving edit.
  Use independent human judgments on held-out technical samples and retain
  disagreement records.
- [ ] P16.7 Evaluate JFLEG/ASSET before-and-after differences as supplementary
  evidence. Inspect new warnings on human corrections and retained valid warnings.
- [ ] P16.8 Choose confidence/default/profile changes using development evidence,
  then evaluate the chosen policy once on the reserved holdout set.
- [x] P16.9 Treat later tuning prompted by holdout errors as development work and
  reserve fresh independent sources before claiming another generalization result.
- [x] P16.10 Keep corpus metrics report-only until reviewed coverage supports a
  justified gate. Then specify a no-new-regressions check and any numeric
  thresholds with documented denominators and small-sample treatment.
- [ ] P16.10a Set quality targets from reviewed development data before consulting
  holdout results. Test the gate on controlled regressions and retain known
  mismatches explicitly instead of adopting a blanket pass threshold.
- [x] P16.11 Publish results with commit, policy, corpus version, sample sizes,
  uncertainty, known limitations, and the disposition of every assessed issue.

Acceptance: a measured improvement means more useful findings or fewer incorrect
ones without hiding eligible misses, changing the population, or losing meaning.

## P17 — Package completion and integration gates

Apply this checklist to each behavior slice. Run the final integration checklist
after all selected packages are complete. A deferred optional feature needs a
written decision and its unmet prerequisite; it must not appear as completed.

### New-rule checklist

- [x] P17A.1 Allocate an unused ID and declare class metadata, supported file
  types, content scope, severity, confidence, and any real configuration field.
- [x] P17A.2 Register the rule and test its selection, ignore handling, severity
  overrides, and experimental/profile classification.
- [x] P17A.3 Update metadata, profile, and rule-count assertions to reflect the
  declared rule catalog. Preserve registry consistency checks.
- [x] P17A.4 Add the handwritten rule-reference section and required executable
  positive/negative examples; generate canonical inventory and category counts
  with `make rule-docs`.
- [x] P17A.5 Add at least one genuine positive and one explicit negative corpus
  case. Add more independent coverage before using it to justify promotion.
- [x] P17A.6 Verify JSON Lines/SARIF span behavior, deterministic ordering, inline
  suppression, and baseline interaction where the rule introduces a new case.

### Checks for each slice

- [x] P17B.1 Run the smallest relevant test command until the new regression is
  green, then run related integration tests.
- [x] P17B.2 Review every changed corpus finding and expectation. Preserve false
  positives as mismatches until the behavior or annotation has a justified change.
- [x] P17B.3 Run `make rule-docs-check`, `make check`, `make dogfood`, and
  `make rule-quality`. Explain quality deltas; the current evaluator's successful
  exit does not mean it has no false positives.
- [x] P17B.4 Run the ProseProbe JSON Lines scan on edited prose with the project's
  existing policy and baseline. Review technical terms and exact examples before
  rewriting them.
- [x] P17B.5 Update `CHANGELOG.md` and affected specification/configuration docs
  for user-visible changes. Keep generated blocks generated.

### Final integration

- [x] P17C.1 Run `make check`, `make dogfood`, `make rule-quality`, and
  `make nfr-check` on the final implementation commit.
- [ ] P17C.2 Require the Python 3.11, 3.12, and 3.13 CI matrix for that commit.
  Report any unavailable remote check explicitly.
- [x] P17C.3 Verify representative filesystem and stdin scans in text, JSON,
  JSON Lines, and SARIF, including clean inputs and operational errors.
- [x] P17C.4 Verify `watch` and baseline maintenance after shared-policy changes.
  Preserve legacy readable baselines, deterministic identity, and atomic writes.
- [x] P17C.5 Compare the full-scan benchmark and memory/startup probes with P00/P07
  evidence. Investigate material regressions before closing the plan.
- [x] P17C.6 Review each package against its acceptance criteria and record
  completed, deferred, or unresolved status with supporting test and corpus results.
- [x] P17C.7 Keep publication separate. Follow `RELEASE_BLOCKERS.md` if a release
  is requested; completion of this plan does not authorize a tag or publication.

## Commands for execution

Run from the repository root. The local RTK instruction applies to shell commands.
Replace the focused test path with the package being worked on.

```bash
rtk git status --short
rtk git rev-parse HEAD
rtk proxy .venv/bin/python -m proseprobe check README.md --show-config --baseline .proseprobe-baseline.json
rtk proxy .venv/bin/pytest tests/test_parsers/test_python.py -q
rtk proxy make rule-docs
rtk proxy make check
rtk proxy make dogfood
rtk proxy make rule-quality
rtk proxy .venv/bin/python -m proseprobe check PLAN.md --format jsonl --baseline .proseprobe-baseline.json
rtk proxy make nfr-check
```

Do not run the modifying `make rule-docs` command when only verifying a prose edit;
use `make rule-docs-check` for that case. Reuse the same prose-scan command after
each repair. Broad checks need repetition only after changes, failures, or a new
unresolved concern.

## Execution record

### P00 — Baseline recorded

Starting commit: `58e6f64eafeefd0086a2a507d1917916d548539b`.
The worktree was clean before implementation; `PLAN.md` was locally ignored.
The plan is now tracked explicitly so progress can be included in each implementation
change commit without altering the ignore policy.

Python: 3.13.16. Default configuration: all category prefixes, warning minimum
severity, low minimum confidence, no ignores, and standard file exclusions.

`make check dogfood rule-quality` passed. The suite contained 1,990 tests.
All-rule corpus counts were 301 true positives, 12 false positives, and no
false negatives; explicit negative cases passed 391 of 403 checks.

| Group | True positives | False positives |
| --- | ---: | ---: |
| Error | 10 | 0 |
| Warning | 88 | 10 |
| Info | 203 | 2 |
| High confidence | 68 | 0 |
| Medium confidence | 193 | 7 |
| Low confidence | 40 | 5 |

All three infrastructure reproductions failed as assessed:

- Relative discovery included the ignored file.
- The Unicode function's docstring produced no diagnostic.
- An attributed fence exposed code and classified its closer as unclosed.

The test inventory confirms intentional expectations that need
review for evidence association and technical vocabulary. Later work packages
name the affected tests and retained contracts.

### P01 — Relative discovery corrected

Three discovery regressions failed before correction. Git now receives absolute
NUL-delimited paths and its results map back to the original caller paths.
Relative/absolute parity, overlapping roots, spaces, nested ignores, negation,
explicit overrides, and configured exclusions are covered. The CLI regression
checks its relative output path and one-file scan count.

Focused discovery and CLI checks passed. The integrated workspace gate passed
with 2,031 tests, documentation checks, and unchanged corpus counts. Existing
literal examples reported by prose review remain unchanged.

### P02 — Unicode Python coordinates corrected

Eight of twelve new Unicode parser cases failed before correction. AST byte
positions now convert to character positions for both docstring token bounds
and string-literal columns. The parser audit found no other affected coordinate
consumer requiring a change.

All parser cases and JSON Lines/SARIF integrations pass. The inline suppression
integration also passes. A corpus positive preserves the original source span,
with a clean Unicode-named counterpart. The gate passed with 2,034 tests;
corpus counts are 302 true positives, 12 false positives, and no missed cases.

### P03 — Fence information strings corrected

Eighteen attributed-fence regressions failed before correction. Opening
information strings now parse separately from delimiters; the language remains
its first token. Backtick-information restrictions and strict closers remain
covered alongside indentation, tilde fences, and blockquotes.

The CLI confirms code masking and retained surrounding prose. Valid and
unclosed attributed fences are recorded in the corpus. The gate passed with
2,035 tests; corpus counts are 303 true positives, 12 false positives, and no
missed cases. No baseline entries were accepted.

### P04 — Production-policy evaluation shared

Thirty-one new policy/evaluator cases failed before implementation. The CLI and
quality evaluator now share explicit scan construction and confidence filters.
Legacy all-rules/info/low results remain the default; policy options select
isolated production evaluation. Baselines are rejected, and confidence-filtered
eligible positives remain missed detections.

All 276 focused tests passed. JSON contains policy, version, revision, and
manifest/source checksums. Core checks passed with 2,143 tests and the evaluator
retained 303/12/0 corpus counts. Documentation checks exposed a previously
accepted duplicate paragraph after the pending multiline baseline correction;
its source explanation is updated with P08. Source-only type checking passes; an extended
benchmark type check found the same 18 existing errors as the prior commit.

Implementation commits include P01 `917973e`, P02 `38a20fb`, P03 `0f8bbed`,
P04 `55a4eb2`, P05 `dbfeb3f`, P06 `09e834c`, P07 `f2c2c73`, P08 `86aa453`,
and P09 `5e3588b`.


### P05 — Coverage and scoring separated

Endpoint, semantic correspondence, coverage, and metric regressions failed
before implementation. All 65 evaluator/scoring cases now pass. Version 1
remains exhaustive and exact-start compatible; version 2 accepts sparse reviewed
rules and regions. Invalid spans, duplicate assignments, and arbitrary overlap
cannot receive credit. Confidence-filtered eligible issues remain misses.

Detection, exact start, full span, reviewed negatives, and unknown coverage have
separate denominators. Reports include policy/context/source breakdowns, sample
uncertainty, and reviewed-prose warning density. Unreviewed material cannot
supply a clean-negative or density denominator. Both evaluator modules pass
strict type checking. The external pilot has not been scored or unblinded.


### P06 — Pilot frozen and blind review prepared

The manifest freezes 300 unreviewed units: 100 complete Markdown documents,
80 Python functions with docstrings and comments, and 120 grammar/simplification
originals with native references. Development contains 170 units; holdout
contains 130. GitHub Docs, Rust book, and upstream Python licenses are pinned;
restricted grammar datasets remain in the ignored local cache. The README
revision package is accessible but its reuse terms remain unresolved and it is
excluded. The primary CodeSearchNet archive returned 403; a bounded named mirror
was checked against pinned upstream modules without changing native text.

Forty-one offline adapter/provenance tests pass, including checksum-before-
conversion, path containment, exact text, native coordinates, and split/pair
isolation. The frozen manifest checksum is
`2dcadd8fb3bb278ee09a9ff2685b00c7a7c6efde3f0221ae69efcccc825d3ade`.
Blind originals and an empty-coverage annotation packet are ready. No detector
predictions or human labels were assigned to this pilot, and holdout prose has
not been read for tuning. Human annotation, double review, native error mapping,
and revision usefulness judgments remain pending. The reviewer request is open.

The integrated local gate passed with 2,361 tests and regression counts
308 true positives, 12 false positives, and no misses. These counts include
pending rule-wrap fixtures and describe the regression corpus, not the pilot.


### P08 — Wrapped replacement phrases and baseline spans corrected

Twelve wrap regressions failed before the source-mapped matcher correction.
V009/V010/V011/V013/V017 now accept layout whitespace within one prose region
and validate the covered original source. Code gaps and unrelated blocks remain
separate. V011's decision-compound guard reads the complete wrapped suffix.
JSON Lines, SARIF, suppression, comment prefixes, and blockquotes are covered.
Five reviewed wrapped positives and two nearby negatives were added; the corpus
changed from 303 to 308 true positives with the same 12 false positives and no
misses. Older literal matchers are being addressed individually in P11/P12.

Two failing baseline regressions exposed truncated multiline match identity.
Concrete multiline spans now participate fully in identity while single-line
identities and readable v1/v2 files remain compatible. Old first-token entries
are readable but stale and need explicit review. No baseline file was refreshed.
An exposed duplicate rule-document paragraph was replaced with the specific
V011 wrapping explanation. The local integrated gate passed with 2,361 tests,
including documentation and corpus checks; edited prose scans passed.


### P07 — Full scan path measured

Nineteen benchmark tests pass. Parser characterizations show shared prose rules
already reuse one parser per content; some structural rules construct their own
parser. No measured bottleneck justified an architectural optimization.
Production measurements include discovery, reads, extraction, filtering, and
cold-process JSON serialization as separately labeled paths. Rates use actual
UTF-8 bytes and file counts; controlled clocks test calculations without unit
wall-clock thresholds. Workloads include Unicode, distinct small files, repeated
content, masks, ignores, and both source formats.

A frozen development subset of ten GitHub Docs documents and ten Python
functions contains 70,869 bytes. Three-iteration technical-docs measurements
use the same 79-rule policy: warmed directory median 314.76 ms (313.54–314.92),
cleared-parser median 340.10 ms (339.63–340.18), and new-process JSON CLI median
452.71 ms (452.14–454.58). Python 3.13.16, macOS arm64, 16 logical CPUs;
workload checksum `523df0c0d0b99a349bceea94135dc215f6fa11f042c42881c3334834258b46b2`.
No holdout content was used. Synthetic distinct/repeated batches were measured
separately. Reports are local timing evidence, not throughput release gates.
The integrated gate passed with 2,361 tests before this documentation update.


### P09 — Hedge stacks qualified by clause

Fourteen regressions failed before correction. Recognized independent subjects
and semicolons separate clauses; ambiguous distant counts remain medium
confidence. Exact source-adjacent redundant modals and clear stacks remain high
confidence. Masked gaps cannot invent a pair, and a confirmed pair owns its span
without a duplicate broad-stack alert. Forty-two focused hedge cases passed,
including profile confidence filtering. Two reviewed corpus positives distinguish
wrapped exact pairs from ambiguous counts; an independent-alternative negative
is retained. The prior integrated gate passed; the updated corpus has 310 true
positives, the same 12 false positives, and no missed expectations.


### P13–P15 — Experimental rule implementation and integration

G039 has 44 focused cases for its closed function-word vocabulary, exact
single/multiline duplicated tails, case, masks, legitimate repetition, and
explicit preserved-name suppression. C009 has 52 field/signature cases, including
parameter kinds, owning function boundaries, Unicode normalization, variadics,
unknown decorators, masked examples, and conservative concatenated-literal
mapping. C007 retains its existing parameter tuple. Google/NumPy formats are
explicitly deferred pending their own evidence.

M011 has 60 cases under GitHub's documented static anchor policy: headings,
suffix collisions, explicit anchors, encoded fragments, balanced destinations,
titles, images, references, examples, and generated-content exclusions. The
renderer setting is validated and off by default; severity overrides cannot
reenable an off renderer. All-rules evaluation explicitly records GitHub policy;
production eligibility excludes labels when the renderer is off.

Sixteen integration cases failed before registry/policy wiring. Seventeen now
pass for JSON Lines/SARIF endpoints, selection, ignores, severity overrides,
baseline round trips, suppressions, metadata, profile classification, and renderer
eligibility. Registry and executable documentation tests pass with 100 rules.
New corpus positives/negatives include all three rules. Existing placeholder
corpus text also contains a missing Install target: its new M011 expectation
records a reviewed defect under enabled GitHub policy while retaining the M004
negative. Independent precision and renderer-corpus human review remain pending;
no profile promotion has been made.


### P10 — Evidence narrowed to the matched claim

Seventeen initial regressions plus four boundary refinements failed before the
claim-scope correction. All 71 focused cases pass. Unrelated releases, dates,
names, links, finite neighboring tests, and independent clauses cannot silently
qualify an assertion. Explicit comparison sets and observation bounds must
modify the matched claim. Unresolved testing scope keeps a low-confidence
finding; broad evidence helpers used by other rules remain unchanged.

The original adjacent-evidence inputs remain as reviewed positives under the
revised contract: V015 and V016 each gain one expectation and lose one obsolete
negative judgment. Additional corpus cases distinguish an unrelated Release 4,
a scoped comparison, a universal claim after finite testing, and directly bounded
observations. V015 stays experimental, with no profile promotion.

### P11 — Local phrase duplicates removed

Sixteen regressions failed before the mapped literal matcher. Fifty-one focused
cases pass for longest complete-word matches, repeated occurrences, wrapping,
source order, and masked gaps. Explicit V002/G009 selection now yields two
records instead of four on a shared phrase: one warning about chat language and
one informational teaching-tone diagnosis. Their catalog overlap contains five
phrases, documented in the reference. Normal warning scans retain one record.

Local catalog duplicates are removed without changing renderer counts or
machine schemas. Both distinct rule IDs remain selectable and independently
ignorable/suppressible; callers treat them as one editing decision. JSON
Lines/SARIF integrations and baseline identities preserve both requested IDs and
the same complete wrapped span. Two reviewed corpus positives and four negative
checks cover the distinction.

### P12 — Technical spans preserved, raw limitations retained

Seventy technical-context regressions failed before implementation. The matched
technical word alone is exempted in reviewed constructions; generic uses and
other occurrences still warn. Case, inflection, wrapping, source masks, and
Markdown/Python parity are covered. Whole-line configured allowed phrases and
inflection-safe suggestions retain their established contracts.

The original twelve false-positive inputs and negative annotations remain.
Six technical alerts are corrected. Four quotation alerts remain raw false
positives with explicit narrow caller handling; two following-evidence alerts
remain low-confidence association limitations. Ordinary blockquotes still lint.
The disposition ledger records each case. The development regression report at
this checkpoint contains 320 true positives, six false positives, no misses,
and 413/419 passed negative checks. This is not an independent population
estimate. Frozen external holdout review remains pending and unused for tuning.


### P16 — Measurement engineering completed; independent review pending

Deterministic tests cover precision/recall, full spans, macro averages, empty
coverage, confidence filtering, reviewed prose-word denominators, and Wilson
sample intervals. Reports separate Markdown, docstrings, and comments and
show source-group variation. No independent source groups are declared for the
legacy purpose-written corpus, so cluster intervals remain unavailable with an
explicit reason; simple intervals are limited to the reviewed sample.

Default warning/error policy and all-rule informational behavior are measured
separately. Six residual raw false positives remain visible; four have warning
severity and two informational severity. Metrics remain report-only. No arbitrary
numeric gate, profile promotion, or confidence recalibration was adopted before
human review. Future tuning prompted by holdout errors requires fresh independent
sources before another generalization claim.

Blind annotation, independent usefulness judgments, revision-pair review,
source-cluster sampling, and predeclared quality targets remain pending. Native
M2 types cannot substitute for supported issue annotations. Publication and tags
remain outside this task.

### P17 — Integration coverage expanded

The existing 205 CLI/reporter/baseline checks passed, including watch/check
policy parity, suppression, legacy baseline reading, maintenance, load-once,
and atomic save failures. Additional characterization covers clean stdin in
all four formats, warning stdin SARIF source positions, and operational read
errors in each output format. The Markdown parity fixture now uses the actual
next-line directive rather than an ordinary HTML comment. No operational behavior
or structured schema changed to satisfy these checks.

Python 3.11.15 and 3.12.15 are available locally. Isolated temporary environments
with matching pytest/Hypothesis dependencies are prepared for full compatibility
runs. Repository/runtime dependencies remain unchanged. Ubuntu remote CI on the
final commit remains a separate check; no push or publication was requested.


### P08.7 — Older literal catalogs migrated after individual regressions

Twenty-four wrapped-span tests and one masked-first/valid-later S019 test failed
before correction. Fifty-eight new cases and 1,047 related rule tests pass.
G004/G005/G006/V004/S014 use the narrow literal matcher; G029 retains its source
case, exact suggestions, and heading exclusion. S019 retains its organizational
context guard and first valid occurrence per catalog entry. Source prefixes,
masked gaps, unrelated blocks, single-line behavior, and exact endpoints remain
covered. Eight reviewed wrapped detections (one phrase has two existing rule
meanings) and seven fenced negatives are added to the corpus.

The inventory also confirms regex-family gaps: G001 copula patterns, G002
metadiscourse, V003 cutoff patterns, V005 attribution patterns, and V006 stakes
patterns. The second bounded slice corrects their explicit literal separators
without rewriting alternatives, character classes, bounds, or wildcard meaning.
No general regex wrap-invariance claim has been made.


### P08.7 — Confirmed regex-family gaps completed

Twenty-two wrap/confidence regressions and two first-match/source-line
compatibility checks failed before correction. Forty-eight added cases and
856 related grammar/vocabulary tests pass. G001/G002/V003/V005/V006 now map
supported phrase whitespace to original source, including full endpoints.
G002's multiword hedge count uses the same raw-source validation and preserves
clause guards, precise-pair ownership, and medium-confidence ambiguity.

V005 retains its evidence-confidence downgrade and first valid match per
pattern/sentence. V003/V006 retain first-pattern/start-line count policy.
Explicit fixed separators change; wildcard expressions keep their existing
non-DOTALL meaning. Masked gaps and separate prose regions cannot manufacture
fixed phrases. Eight reviewed corpus positives include the five primary rules
and three existing vocabulary/promotional diagnoses on the same deliberate
examples; eight fenced negatives preserve code masking.


### P07/P17 — Measured startup import delay corrected

An isolated archived `f8f8f52` import trace attributed about 25 ms to rule
catalog imports on the version command. Three subprocess regressions failed
before deferring those imports until registry construction. The smallest source
change moves the existing catalog import into `get_all_rules`; version/help
output, the 100-rule catalog, and production scanning remain covered.

All 215 focused lazy-import/metadata/CLI checks and static checks pass. A startup
probe after the change measured 54.4 ms, compared with the earlier 99.7 ms probe.
These are hardware-dependent single samples; the unchanged 100 ms gate remains.
The scan profile is reviewed separately from import latency.


### P07/P17 — Measured pattern construction hoisted

The archived scan profile showed repeated escaping and regex-cache lookups.
Warm scans performed no new regex compilation. Two operation-count regressions
failed before moving V001 pattern construction to each configured instance and
replacement-pattern construction to each call. Full issue records preserve
sorted-word order, case, suggestions, allowed/additional words, and current
replacement-table contents. All 1,781 related tests and static checks pass.

A controlled five-sample comparison uses archived `2de7cc2` before and that
archive plus only the vocabulary patch after. The frozen twenty development
files, 70,869 bytes, 79-rule policy, workload checksum, and 49 complete finding
records are identical. The record checksum is
`1aee145055e10ead60945b33204d6da991b4d1bd354767da78bfe1861f362018`.
Serial medians changed 264.16 to 212.46 ms; warmed discovery/read scans 270.88
to 217.43 ms; cleared parser caches 285.94 to 231.94 ms; new-process JSON CLI
365.53 to 312.22 ms. These paired measurements show roughly 19–20% scan reduction
and 14.6% cold-CLI reduction under those resource conditions.

Earlier P07 timings came from a mixed working tree, so they provide directional
history rather than reproducible commit attribution. The controlled comparison
records exact runtime-tree and patch hashes. No global cache, dependency,
parser/traversal redesign, wall-clock unit threshold, or holdout tuning was added.


### P17 — Final acceptance review

All engineering packages have passed their focused tests, static checks,
executable documentation checks, edited-prose review, and integrated corpus
review. No runtime dependencies or baseline entries were added. The registry
contains 100 rules; named profile promotion and independent effectiveness claims
remain deliberately pending. Additional baseline characterization proves that
different wrapped phrases with identical first lines retain separate identities.

| Package | Engineering status | Remaining prerequisite |
| --- | --- | --- |
| P00–P05 | Complete | None |
| P06 | Provenance, adapters, frozen pilot, blind packet complete | Human annotation, double review, native-error/revision judgments; README revision reuse terms unresolved |
| P07–P11 | Complete, including confirmed wrapping and measured performance fixes | None |
| P12 | Technical and explicit quotation policy complete | Independent development/holdout usefulness review |
| P13–P15 | Rules, renderer setting, metadata, docs, and integrations complete | Independent precision and renderer-corpus review before promotion |
| P16 | Metric/report engineering and legacy disposition complete | Human usefulness, paired revisions, calibration, and predeclared quality targets |
| P17 | Local acceptance checks complete | Remote Ubuntu CI remains unverified |

The human reviewer request remains unanswered. No agent supplied human labels,
read external holdout prose for tuning, or inferred correctness from native
revisions. The excluded README dataset can be reconsidered only after its reuse
terms become clear. No push, tag, package publication, or external message was
sent. Local three-version tests do not replace the remote Ubuntu matrix.

Regression results on runtime revision `802be72` use corpus version 1, all rules,
info/low confidence, and explicitly enabled GitHub anchors: 336 true positives,
six retained false positives, no misses, and 428/434 passed negative checks.
Detection precision is 98.25% (336/342); eligible recall is 100% (336/336).
All 34 expectations supplying full endpoints matched; the other expectations
remain start-only checks. Default production warning/low policy with renderer
off reports 106 true positives, four false positives, no misses, and 65/69
passed negative checks. Warning density is 0.681 per 1,000 reviewed prose words
(4/5,872). Wilson intervals are sample-only; identified independent source groups
are absent, so cluster intervals are unavailable. These figures describe the
purpose-written regression corpus, not the 300-unit natural-text pilot.


### Final local verification — 2026-10-09

Final implementation/test commit: `91eb4ea`; runtime code matches `802be72`.
`make check dogfood rule-quality nfr-check` passed in the final state. Python
3.13.16 passed 2,665 tests; isolated Python 3.11.15 and 3.12.15 each passed the
same 2,665-test suite. Generated documentation, Ruff, source mypy, and all edited
prose scans passed. Baseline contents, runtime dependency declarations, and the
existing CI workflow are unchanged from the starting commit.

Coverage: 96.01% against the unchanged 90% gate. Startup: 50.0 ms against
100 ms. Memory: 23.8 MB for 10,000 discovered/checked files against 100 MB.
The final reviewed-directory benchmark used 64 files, 39.1 KiB, 79 selected
technical-docs rules, and JSON for cold CLI output: cleared-cache median
234.01 ms (233.83–235.75); cold CLI 317.85 ms (313.19–329.82), five samples.
Workload checksum:
`9606166de20c4b172fa79b88eccdc2b5f79af3e9168467ff0d58081b21f48c4a`.
The controlled frozen-development comparison above is the supported performance
comparison; different corpus sizes and historical resource conditions are not
interchangeable timing baselines.

The regression manifest contains 69 files, 336 expected findings, and 434
negative checks. Its checksum is
`23f03d7ec7b3720ed683c63c4a244c18505e0d85c9bb13f1d58ac4ee2f05e972`.
All six remaining raw false positives are listed in the disposition ledger.
The external pilot stays frozen, blind, and unreviewed. Remaining unchecked
steps require human judgments, clear third-party reuse terms, or remote CI;
they are not marked complete. This final record changes documentation only.

Change commits include `ca2fd6d` (new experimental rules), `a58441e`
(claim-local evidence), `07646ee` (phrase overlap), `192bba2` (technical senses),
`f8f8f52` (literal wrapping), `a0cbd3a` (regex wrapping), `2de7cc2` (deferred
imports), `802be72` (measured pattern construction), and `91eb4ea` (integration
contracts). Earlier package commits are recorded above.

## Reassessment continuation

Planning date: 2026-10-09. Execution started: 2026-10-10.
Status: checked actions are complete; other actions retain their prerequisites.
Baseline revision: `bf53d0adfed8bd04884cbdfc542f365c026ee796`.

This continuation covers every issue from the second assessment. The previous
implementation improved source mapping, policy consistency, matching, and
measurement. The next work corrects remaining defects, tests useful additions,
and establishes independent evidence. Keep the original completed records and
unchecked human-review tasks intact.

The reassessment reran the curated regression evaluator: all-rules info/low
with GitHub anchors produced 336 true positives, six false positives, no misses,
and 428/434 passed negative checks; default production warning/low with anchors
off produced 106 true positives, four false positives, no misses, and 65/69
passed negative checks. Precision is 98.25% and 96.36%, respectively. The last
full local verification recorded 2,665 tests on Python 3.11–3.13 and 96.01%
coverage. These are regression and engineering results. The frozen 300-unit
natural-text pilot has no independent labels or effectiveness score.

### Scope and issue mapping

| Assessment issue | Work package |
| --- | --- |
| Phrases synthesized across masked inline content; incomplete predicate validation | P18 |
| Uncaught automatic TOML errors; parent configuration beyond a Git root | P19 |
| Missing SARIF column convention | P20 |
| Python extension casing differs between routing and parsing | P21 |
| Watch misses backward timestamps and some recreated files | P22 |
| Valid quality reports always succeed even with new mismatches | P23 |
| Labels lack annotation-time source binding; runtime and benchmark identity gaps | P24 |
| Fully reviewed clean source groups disappear from coverage counts | P25 |
| Placeholder checks confuse executable code, strings, and abstract contracts | P26 |
| Unrelated raw context suppresses undefined-comparative findings | P27 |
| Explicit starred parameter documentation conflicts with signature kinds | P28 |
| Explicit return annotation and documentation can contradict each other | P29 |
| Missing local Markdown link targets and supported cross-document fragments | P30 |
| Suggested replacements can trigger the same rule or lose meaning | P31 |
| Independent labels, Python holdout, source diversity, calibration, and dataset limits | P32 |
| Integration, documented behavior, performance, completion, and remote checks | P33 |

P18–P28 and P31 address confirmed defects or gaps. P29 and P30 are scoped
experiments. They require a written contract before implementation and remain
experimental until independent evidence supports wider use. Existing rule IDs
stay stable; assign a new ID only after checking the registry. Avoid duplicating
M005 reference-definition checks or expanding placeholder catalogs before P26.

### Execution order

| Stage | Packages | Dependency or coordination constraint |
| --- | --- | --- |
| Capture current evidence | P18/P19/P20/P21/P22 first tests; P32 review protocol | Preserve baseline and frozen holdout text |
| Correct independent operational defects | P19–P22 | May run alongside P18 with separate file ownership |
| Complete evaluation foundations | P24, P25, then P23 | Provenance and reviewed coverage precede the strict gate |
| Correct rule precision | P18, P26, P27, P28, P31 | Sequence shared rule-file edits; use the regression gate when available |
| Trial scoped new checks | P29, P30 | Written contracts, source validation, and production-policy tests |
| Obtain and evaluate independent evidence | P32 | Human annotation precedes detector comparison and holdout tuning |
| Final integration | P33 | Required engineering gates and honest unresolved-status record |

P32 protocol and source-inventory work can begin immediately. Human review and
publication of effectiveness results have their own prerequisites. Continue
independent engineering work while waiting for a reviewer. Preserve all 300
frozen source assignments; new coverage belongs to a separately frozen extension.

### Test and change discipline for this continuation

- Begin each behavior slice with the smallest failing test. Record the command,
  failure, and intended invariant before editing production code.
- Change one behavior at a time. Run its new test and the related existing tests
  before broader acceptance checks. Characterize behavior before a refactor.
- Use temporary fixtures and synthetic examples for deterministic tests. Keep
  external downloads, wall-clock thresholds, and human judgments outside unit tests.
- Check complete issue records when moving match logic: rule ID, message,
  suggestion, confidence, severity, ordering, and original-source endpoints.
- Preserve caller policy, inline suppression, baseline durability, and the
  original known false-positive inputs and negative annotations.
- Record deliberate annotation or detection-contract changes with reasons.
  Report known mismatches; a regression ledger must not suppress raw findings.
- Keep parser conformance, curated regression, independently reviewed natural
  text, and native human revisions as separately reported evidence.
- Update this document after each slice with status, test evidence, quality delta,
  and remaining prerequisites. Check a box only when its action is complete.
- Commit each coherent behavior change with a one-line message. Suggested
  messages below identify useful boundaries; do not combine unrelated packages.
- Run the P33 slice gate before each implementation commit. Repeat broader
  checks when new changes, failures, or unresolved concerns justify them.

The planning revision changed documentation only. Execution preserves runtime
dependencies, named profiles, baseline contents, and frozen pilot assignments.
The package-specific acceptance criteria below control completion.

## P18 — Validate complete phrase predicates against original source

Targets: `src/proseprobe/rules/_phrases.py`,
`src/proseprobe/rules/grammar.py`, `src/proseprobe/rules/vocab.py`,
`tests/test_rules/test_grammar.py`, `tests/test_rules/test_vocab.py`,
`tests/test_parsers/test_prose.py`, `tests/test_linter.py`,
`quality/annotations.json` and purpose-written regression fixtures.
Prerequisites: completed P02, P03 and P08; P24 before publishing new measurements.

Masked prose must not create a detection or an exemption that the original source
cannot support. Validate the entire predicate used to decide a match, including
its copula or modal, while keeping the existing diagnostic subspan. In particular,
V015 validates `is ... best` before reporting only `best`. Context used for
exceptions, definition suffixes, or confidence changes also needs original-source
evidence. Keep exact phrase catalogs, rule IDs, severities and ordering stable.

- [x] P18.1 Inventory the six assessed rules: G024, G025, G037, V014, V015 and
  V016. Record each candidate pattern, diagnostic subgroup, exception predicate,
  confidence predicate and existing focused tests. Audit direct sentence-regex
  consumers for the same defect; add another rule only after reproducing it.
- [x] P18.2 Add a passing characterization matrix for ordinary and wrapped
  positives in Markdown body/list/blockquote and Python docstring/comment prose.
  Assert complete issue records, including original-source exclusive endpoints.
- [x] P18.3 Add failing G037 negatives for
  ``Clients must `not` normally restart.`` and the HTML-masked equivalent. Confirm
  that the current false match is `must normally` before changing the rule.
- [x] P18.4 Route G037 candidates through the existing source-validation helper.
  Validate the modal and hedge together; retain legitimate whitespace and
  continuation prefixes. Run the G037 matrix before continuing.
- [x] P18.5 Add a failing G037 definition-suffix case where an intervening masked
  token makes an apparent `means` exemption. Assert that masking does not remove
  a genuine finding. Add an uninterrupted definition negative alongside it.
- [x] P18.6 Make that exemption validate its complete original-source suffix.
  Run G037 positives, negatives and source-span checks.
- [x] P18.7 Add failing G024 tests with inline code or HTML interrupting each
  fixed opener, including ``It must `not` be ensured that the file is closed.``
  Preserve a valid sentence-start opener and a wrapped positive.
- [x] P18.8 Validate G024's full anchored opener against the corresponding source
  slice without removing its sentence-start requirement. Run focused G024 tests.
- [x] P18.9 Add failing G025 tests with a masked interruption in both
  `You will need to` and `You can proceed to`. Include
  ``You `should reconsider` will need to restart.`` Retain ordinary repeated matches.
- [x] P18.10 Validate each complete G025 instruction phrase and rerun its focused
  tests, including a later valid candidate after an invalid interrupted one.
- [ ] P18.11 Add failing V014 tests for ``a large `unexpected` number of`` and
  ``a handful `unexpected` of``. Include
  ``A small `but measurable` number of errors occurred.`` Add a wrapped positive
  with exact endpoints.
- [ ] P18.12 Validate each full V014 quantity phrase. Keep its documented evidence
  policy and confidence behavior intact; run V014 tests.
- [ ] P18.13 Add failing V015 negatives for ``The parser is `not` the best.`` and
  interruptions within a multiword superlative. Assert no diagnostic from a
  fabricated copula/claim pair, even when the adjective span itself is literal.
- [ ] P18.14 Validate V015's whole `_CLAIM` match before selecting the `claim`
  subgroup for its diagnostic. Run the V015 detection and full-span matrix.
- [ ] P18.15 Add failing V015 guard tests where masked code/HTML invents a local
  comparison set, a hypothetical qualifier, or literal-discussion context.
  Pair each with a genuine explicit comparison or qualifier negative.
- [ ] P18.16 Use original-source bounded prose for each reproduced exemption.
  Preserve existing clause attachment and refrain from treating all nearby
  comparison vocabulary as evidence. Run V015 guard tests.
- [ ] P18.17 Add failing V016 negatives for ``The system never `not` fails.`` and
  interruptions within `always succeeds`, `eliminates all errors`, and
  `100% secure`. Add corresponding unmasked and wrapped positives.
- [ ] P18.18 Validate each whole V016 reliability predicate and run its focused
  detection/source-span tests.
- [ ] P18.19 Add failing V016 tests where masking fabricates a tested bound or
  changes its attachment, plus a case where masked text incorrectly changes
  confidence. Assert genuine attached bounds still qualify the observation.
- [ ] P18.20 Validate only the reproduced context predicates against original
  source, preserving the existing clause boundary and tested-scope policy.
  Run V016 confidence and bound tests.
- [ ] P18.21 Add a shared helper regression for Markdown markup, punctuation,
  block boundaries, CRLF, Unicode, Python comment prefixes and nested
  blockquote prefixes. Characterize legitimate formatting that each caller
  supports; do not globally strip markup to manufacture phrase adjacency.
- [ ] P18.22 Make the smallest helper correction justified by those tests.
  Avoid broadening matching for already validated rules. Run every current
  helper caller's tests and compare complete prior positive records.
- [ ] P18.23 Add one CLI/source-map integration assertion for G037 and V016, and
  one V015 assertion showing that the validated predicate and reported subgroup
  intentionally have different spans. Run focused linter/reporter tests.
- [ ] P18.24 Add purpose-written positive/negative corpus annotations for the
  corrected behaviors, retaining the old raw false-positive dispositions.
  Run the P23 regression gate and P33 package checks. Keep external holdout text
  unopened during this work.

Acceptance: masking cannot invent these predicates or their tested exemptions;
valid wraps remain detected with original-source spans; unchanged positives keep
metadata and ordering. Regression scores are reported with P24 provenance.
Suggested one-line commits: `Validate requirement phrases against original
source`; `Validate complete quantity and claim predicates`; `Preserve claim
exemptions only with source-backed context`.

## P19 — Make configuration discovery obey its error and boundary contracts

Targets: `src/proseprobe/config.py`, `tests/test_config.py`,
`tests/test_cli.py`, configuration documentation.
Prerequisites: reassessment baseline; independent of rule changes.

- [x] P19.1 Characterize the current precedence with temporary fixtures:
  current `.proseprobe.toml`, current `pyproject.toml` with
  `[tool.proseprobe]`, parent `.proseprobe.toml` through the Git root, user
  configuration, then defaults. Reuse passing tests where available.
- [x] P19.2 Add a failing unit test for an automatically discovered malformed
  current-directory `pyproject.toml`. Require `ConfigError` containing its path
  and parse diagnostic. A malformed file without a readable tool table also
  fails clearly; discovery must not silently guess that it is unrelated.
- [x] P19.3 Add a failing CLI regression for automatic discovery. Assert exit
  code 2, a configuration diagnostic on stderr, and no traceback or findings.
  Reuse the existing explicit-path malformed-TOML test as the comparison.
- [x] P19.4 Wrap discovery's TOML read/parse errors in the existing `ConfigError`
  contract. Add one deterministic read-error test using a patched file reader;
  avoid permission-mode tests that depend on the executing account.
- [x] P19.5 Add a failing boundary test with the starting directory itself as a
  Git root and a conflicting `.proseprobe.toml` above it. Parameterize a `.git`
  directory and a `.git` worktree file. Neither may inherit that parent file.
- [x] P19.6 Add the paired nested-directory test: a root-local
  `.proseprobe.toml` is eligible, but configuration above that root is not.
  Preserve current-directory precedence even when the directory is the root.
- [x] P19.7 Correct the upward-search stopping condition. Detect the marker in
  the starting directory as well as each parent; do not parse Git internals or
  add a Git subprocess to configuration discovery.
- [x] P19.8 Verify user fallback with `Path.home()` redirected to a temporary
  location. Reuse the existing parent-`pyproject.toml` exclusion test; keep that
  documented exclusion intact. Assert that an explicit `--config` still works
  outside the discovery boundary.
- [x] P19.9 Update the configuration documentation if its description needs
  clarification. Run focused configuration/CLI tests and the package gate.

Acceptance: automatic and explicit parsing failures share the documented CLI
error path. Discovery includes the Git root, stops there, supports worktree
markers, and preserves precedence, user fallback, and parent-pyproject policy.

Suggested commits: `Report configuration discovery parse errors consistently`;
`Stop configuration discovery at the starting Git root`.

## P20 — Declare SARIF columns as Unicode code points

Targets: `src/proseprobe/core/reporter.py`, `tests/test_reporter.py`,
`tests/test_cli.py`; existing source-position fixtures.
Prerequisites: P02 source-coordinate contract, already complete.

- [ ] P20.1 Add a failing reporter assertion that each SARIF run has
  `columnKind: "unicodeCodePoints"`, including a run with no findings.
- [ ] P20.2 Add a failing CLI fixture containing an astral character before a
  known finding, such as `😀 delve`. Assert the actual exclusive-end source
  slice and SARIF start/end columns in Python character units. Include a
  Python docstring variant if the existing Unicode integration test lacks it.
- [ ] P20.3 Add the run property without converting the linter's coordinates.
  Reuse ASCII and multiline reporter tests to establish unchanged regions,
  rule metadata, severity, confidence, and rank.
- [ ] P20.4 Record SARIF 2.1.0 §3.14.27 as the contract in the existing reporter
  documentation or test comment. Run reporter/CLI tests and the package gate.
  Do not add a runtime schema-validation dependency for this property.

Acceptance: SARIF explicitly identifies the coordinate convention used by all
text findings, and a reader can recover the source span after an astral
character. Other output formats preserve their existing schemas.

Suggested commit: `Declare Unicode code point columns in SARIF`.

## P21 — Align Python file classification across scan entry points

Targets: `src/proseprobe/core/linter.py`,
`src/proseprobe/parsers/prose.py`, a small shared file-kind helper only if needed,
`tests/test_linter.py`, `tests/test_cli.py`, parser dispatch tests.
Prerequisites: reassessment baseline; independent of P19/P20.

- [ ] P21.1 Add a failing linter test that explicitly supplied `example.PY`
  produces the same Python-only rule finding as `example.py`. Compare full
  finding records after normalizing only the filename.
- [ ] P21.2 Add a failing CLI comparison between an explicit `.PY` file and
  stdin with `--filename example.PY`. Assert Python documentation extraction,
  Python-only rule eligibility, suppression handling, and virtual path output.
- [ ] P21.3 Inventory existing suffix checks used for rule eligibility and
  prose extraction. Characterize `.py`, `.PY`, Markdown suffixes, and an
  unsupported suffix; preserve any intentional fallback behavior.
- [ ] P21.4 Make file classification consistent using a small shared predicate
  or the existing helper location. Keep the registry and parser interfaces;
  introduce no file-type plugin framework.
- [ ] P21.5 Add a discovery contract test with `.py` and `.PY` siblings:
  configured directory include globs retain their existing case behavior.
  A caller-supplied `*.PY` glob selects the uppercase file; explicit-file
  overrides and configured exclusions retain their current behavior.
- [ ] P21.6 Verify production/evaluator eligibility uses the same classification.
  Run focused linter/parser/CLI tests and the package gate. Document explicit
  filename classification only if the existing documentation is ambiguous.

Acceptance: supported explicit and virtual Python filenames have consistent
rule applicability regardless of suffix casing. This change does not silently
broaden directory discovery or reinterpret user glob patterns.

Suggested commit: `Align Python file classification for explicit and stdin scans`.

## P22 — Detect watch changes when timestamps move backward

Targets: `src/proseprobe/cli.py::_changed_files`, watch state initialization,
`tests/test_cli.py`, watch documentation.
Prerequisites: P21 before the integration comparison; helper work independent.

- [ ] P22.1 Add a failing helper test that scans a temporary file, changes its
  bytes, sets an earlier timestamp with `os.utime(ns=...)`, and scans again.
  Assert that the second version is returned exactly once.
- [ ] P22.2 Add deterministic tests for an unchanged stamp, a newer stamp, and
  equal `mtime_ns` with changed size. Assert first discovery always schedules
  the file. Use controlled stat values where filesystem precision differs.
- [ ] P22.3 Replace the increasing float-time comparison with inequality of
  `(st_mtime_ns, st_size)` stamps. Rename local state to describe the stamp,
  keeping the helper private and avoiding content hashing or a new watcher.
- [ ] P22.4 Add a failing deletion/recreation sequence: discover the file,
  delete it for one iteration, then recreate it with its old timestamp and
  size. Require removal of the departed path's cached stamp and scheduling
  upon rediscovery.
- [ ] P22.5 Prune state for paths no longer returned by successful discovery.
  Add a file-removal-between-discovery-and-stat case; skip its failed stat
  without terminating the loop. Confirm surviving paths retain their stamps.
- [ ] P22.6 Exercise two watch iterations through the CLI with a controlled
  sleep callback: the initial file has no finding, the backward-stamped edit
  adds one, and the next batch reports it. Stop with `KeyboardInterrupt`;
  avoid elapsed-time assertions or real waiting.
- [ ] P22.7 Reuse check/watch parity tests for configuration, profile, baseline,
  confidence, suppressions, quiet output, and read errors. Document that this
  polling scheme cannot detect changed bytes when both stamp fields remain
  identical and no deletion is observed. Run focused tests and the package gate.

Acceptance: watch notices forward or backward stamp changes, equal-time size
changes, and observed deletion/recreation. It schedules each changed version
once and preserves the current polling and reporting contracts.

Suggested commit: `Detect watch changes using nanosecond and size stamps`.

## P23 — Add an explicit reviewed regression gate

Targets: `benchmarks/rule_quality.py`, the smallest dedicated regression-gate
module if separation is useful, quality tests, `quality/` gate records,
`quality/README.md`, `Makefile`, existing CI workflow.
Prerequisites: P24 annotation/source/rule provenance, P25 reviewed coverage
accounting, and a fresh all-rules/default-production snapshot. Adding the
gate does not depend on acquiring human labels for the external pilot.

The existing `rule-quality` command remains a report-only measurement. The new
gate compares reviewed mismatches, never a count allowance or a population
precision target. All raw mismatches stay visible in both modes.

- [ ] P23.1 Characterize current report-only behavior with an in-memory or
  temporary reviewed corpus containing one false positive and one false
  negative. Assert successful evaluation still returns 0 and prints both.
- [ ] P23.2 Define a versioned known-mismatch record for a named effective
  policy. Bind each item to mismatch kind, rule ID, source identity/hash, and
  source span or stable expected-label identity. Record the review reason,
  annotation/rule contract identifiers, effective policy, and evaluation code
  provenance from P24. Runtime identity records the ledger's creation; it
  does not require unchanged runtime code, because the gate evaluates new code.
  Do not bind acceptance to a fixed FP/FN total.
- [ ] P23.3 Add failing validator tests for duplicate identities, invalid spans,
  unknown rules, changed source hashes, a mismatched policy, and unsupported
  record versions. Invalid gate input returns a clear error, not success.
- [ ] P23.4 Add record validation and deterministic mismatch identities.
  Preserve raw scoring, one-to-one matching, and full findings; an allowlisted
  mismatch is still an FP or FN in the report.
- [ ] P23.5 Add failing comparator tests: an exact known FP is allowed; a new
  FP fails even when another known FP disappears; a new FN or lost expected
  positive fails; moving a mismatch to a different source span fails. Distinct
  mismatches sharing a rule and line must remain distinguishable.
- [ ] P23.6 Add the comparator. A corrected known mismatch passes and is
  listed as resolved; require review before deleting its record, rather than
  reintroducing the finding to match a frozen count. Explain every newly
  failing identity in deterministic output.
- [ ] P23.7 Add failing coverage tests for explicit unreviewed, unsupported, and
  context-dependent regions, including a corpus with zero emitted findings.
  Strict gating must refuse unknown eligible review coverage from annotations,
  not infer completeness from the absence of detections. Permit out-of-policy
  exclusions only when recorded by the effective policy. Recognize the legacy
  exhaustive curated regression manifest under its existing contract. Its
  frozen gate record must bind the evaluated sources and annotation snapshot;
  this does not convert legacy judgments into independent human annotations.
- [ ] P23.8 Enforce the coverage precondition before accepting the comparison.
  Keep ordinary external evaluation available as report-only; refuse strict
  gating of the frozen unreviewed pilot without changing its labels or scope.
- [ ] P23.9 Add failing CLI tests for the explicit gate option: exit 0 for only
  reviewed known mismatches, 1 for a new reviewed regression, and 2 for invalid
  gate inputs or insufficient review coverage. Preserve complete text/JSON
  raw metrics and attach a separate gate result; ordinary invocation remains
  report-only and returns its existing code.
- [ ] P23.10 Add the CLI option and output contract. Require the requested
  policy to match the reviewed gate record; do not silently switch policies,
  discover project configuration, apply suppression baselines, or hide issues.
- [ ] P23.11 Review and freeze the current six all-rules FP identities and the
  default-production subset of four using the disposition ledger. Keep all
  six negative annotations and original input text. Store each policy's
  records explicitly; confirm there are currently no known FNs.
- [ ] P23.12 Add an explicit Make target that checks both reviewed regression
  policies. Document creation, intentional contract migration, correction, and
  manual review of gate records; provide no automatic acceptance/refresh path.
- [ ] P23.13 Add the new target to CI after its focused tests and package gate
  pass. Keep ordinary `rule-quality` available for measurements. Verify a
  disposable newly missed positive makes the Make target fail without editing
  the committed annotations. Remote execution is tracked under P33.

Acceptance: exact reviewed known mismatches remain visible and do not block the
gate. Any new FP or FN under the recorded policy fails, including replacements
that keep totals unchanged. Unknown coverage and stale provenance cannot
produce a passing strict gate. Independent human effectiveness targets remain
pending P32; this gate makes no generalization claim.

Suggested commits: `Validate reviewed regression mismatch records`;
`Add an explicit reviewed quality regression gate`;
`Run reviewed quality regression checks in CI`.

## P24 — Bind evaluation evidence to the material actually reviewed

Targets: `benchmarks/quality_scoring.py`, `benchmarks/rule_quality.py`,
`benchmarks/corpora.py`, `benchmarks/bench_rules.py`,
`tests/test_quality_scoring.py`, `tests/test_rule_quality.py`,
`tests/test_corpora.py`, `tests/test_benchmarks.py`, `quality/README.md`,
`quality/external/README.md`.

Prerequisites: the existing P05/P06/P07 implementation. Complete P24A before
accepting new independent annotations or enabling the strict P23 gate. P24B/C
can proceed independently of human review. Preserve readable version 1 and
version 2 manifests and their existing scoring semantics.

### P24A — Annotation identity and review metadata

- [ ] P24A.1 Record the existing version 1/2 loading, scope, and report contracts
  with focused tests; retain start-only legacy span behavior.
- [ ] P24A.2 Specify a version 3 annotation contract before implementation. Require
  each source's relative path, source identity, and SHA-256 of the exact UTF-8
  bytes reviewed. Retain version 2 scope fields and semantic matching rules.
- [ ] P24A.3 Specify one review header containing the blind-packet/index identity,
  review-protocol revision, reviewed rule-contract snapshot identity, declared
  profile/policy, and reviewer identifiers. Use pseudonymous identifiers where
  appropriate; metadata must describe actual review, not imply certification.
- [ ] P24A.4 Add a failing tiny-fixture test: changing source wording while leaving
  all annotated coordinates in bounds must make a bound manifest invalid.
- [ ] P24A.5 Add a failing test for a changed newline encoding and a changed
  non-ASCII character. Bind raw bytes; avoid silently normalizing reviewed text.
- [ ] P24A.6 Validate source hashes before scoring and name the source and expected
  identity in an `AnnotationError` on mismatch.
- [ ] P24A.7 Add parameterized failing tests for missing identity/hash fields,
  malformed hashes, duplicate source identities, and invalid review metadata.
- [ ] P24A.8 Validate the new fields using the existing strict schema helpers;
  reject unknown fields rather than accepting ambiguous metadata.
- [ ] P24A.9 Add a failing test for an annotation packet linked to a different
  frozen index or rule-contract snapshot. Verify those referenced artifacts
  locally; do not contact the web during evaluation.
- [ ] P24A.10 Store the reviewed contract snapshot and its checksum with the packet.
  A later contract change requires a recorded review decision before reusing
  affected labels; changing detector implementation alone does not rewrite labels.
- [ ] P24A.11 Add a failing export test that the blind originals and review index
  carry exact source-byte identities but contain no predictions or native revisions.
- [ ] P24A.12 Extend the existing packet export with the bound annotation template
  and index fields. Keep every exported source initially unreviewed.
- [ ] P24A.13 Add a failing test that source mutation during collection cannot
  produce a report claiming the original reviewed bytes. Revalidate the evaluated
  inputs before reporting, or reuse the verified bytes through the scan if the
  existing interfaces support it without a broader parsing redesign.
- [ ] P24A.14 Add legacy-compatibility report tests. Version 1/2 results must say
  `source_binding: legacy-unbound` and `review_provenance: unavailable`; preserve
  their counts and avoid inventing annotation-time hashes or reviewers.
- [ ] P24A.15 Add a strict evaluation option used by the independent-data gate;
  reject unbound annotations under that option while preserving report-only
  legacy evaluation. Test success and failure exit behavior before wiring P23.
  P23 may accept the legacy curated corpus through a separately source-bound
  regression ledger; that exception does not apply to independent labels.
- [ ] P24A.16 Document version 3 with one minimal offline fixture and a reviewed
  migration procedure. Migrating the curated regression manifest may add current
  source identities; it does not make past judgments independently human-reviewed.

Acceptance: a bound label cannot silently survive a different reviewed source,
packet, or contract snapshot; legacy measurements remain usable and explicitly
unbound. Test fixtures establish this without reading frozen holdout text.

Suggested one-line commits: `Bind new annotations to reviewed source bytes`;
`Record annotation review provenance and preserve legacy reports`.

### P24B — Runtime identity in quality reports

- [ ] P24B.1 Define the report identity: HEAD when available, tracked working-tree
  state, and a deterministic digest of the package/evaluator source actually used.
  Include relevant untracked Python implementation files; omit caches, downloaded
  corpora, outputs, and unrelated documents. Record the identity scope explicitly.
- [ ] P24B.2 Add failing tests in disposable repositories for clean HEAD, modified
  runtime code, staged changes, and an untracked implementation module.
- [ ] P24B.3 Build deterministic source identity within an existing
  utility boundary shared by evaluation and benchmarks. Avoid a provenance framework.
- [ ] P24B.4 Add tests for Git unavailable and an installed package outside a
  checkout. Report unavailable Git fields explicitly; retain a source digest and
  package version when their material is available.
- [ ] P24B.5 Add a relocation test: copying identical sources to a different
  temporary directory leaves their digest unchanged. Include relative names and
  bytes so renaming or editing runtime code changes the digest.
- [ ] P24B.6 Add a report test showing that the same HEAD with different runtime
  source bytes produces different identity and an explicit dirty-state indication.
- [ ] P24B.7 Add the identity to quality JSON with an intentional schema-version
  update and document compatibility. Keep existing `revision` readable if retained.
- [ ] P24B.8 Record the input manifest, bound source identities, annotation protocol,
  contracts, and effective policy in the same report. Test that these identities
  do not disappear under production-mode exclusions or confidence filtering.

Acceptance: reports distinguish an exact committed implementation from a changed
checkout and expose unavailable identity fields. No report implies HEAD alone
identifies uncommitted runtime behavior.

Suggested one-line commit: `Identify the runtime source used by quality reports`.

### P24C — Benchmark identity and diagnostic equivalence

- [ ] P24C.1 Characterize existing workload, policy, environment, and cache-state
  metadata tests. Preserve their meanings and existing timing measurements.
- [ ] P24C.2 Add a failing benchmark test requiring the runtime identity from P24B
  alongside workload SHA-256, Python/platform, effective policy, and cache state.
- [ ] P24C.3 Add a canonical digest of complete diagnostics, including relative
  path, rule, severity, confidence, full span, message, and suggestion. Test that
  equal finding counts with different findings produce different digests.
- [ ] P24C.4 Test deterministic ordering and relocation independence of the digest;
  a changed suggestion or endpoint must change it. Preserve multiplicity.
- [ ] P24C.5 Compute diagnostic identity outside timed scan intervals; add a test
  around the timing boundary instead of asserting machine-dependent durations.
- [ ] P24C.6 For new-process CLI measurements, verify the child implementation and
  policy identity rather than assuming the parent interpreter loaded the same code.
  Use an untimed child probe and actual module locations; preserve production
  CLI output and avoid adding a public provenance command solely for benchmarking.
- [ ] P24C.7 Test a selected workload or diagnostic result changing between
  iterations. Fail the comparison clearly rather than reporting a speed improvement
  for a different workload or changed observable behavior.
- [ ] P24C.8 Extend benchmark JSON and documentation with the identity fields and
  the comparison requirement: equal workload/policy/diagnostics and comparable
  environment before attributing a timing delta to an implementation change.

Acceptance: a benchmark result identifies its code and behavior as well as its
inputs. Existing speed measurements remain outside deterministic unit-test gates.

Suggested one-line commit: `Record benchmark runtime and diagnostic identities`.

## P25 — Count reviewed clean sources independently of detections

Targets: `benchmarks/quality_scoring.py`, `benchmarks/rule_quality.py`,
`tests/test_quality_scoring.py`, `tests/test_rule_quality.py`, `quality/README.md`.

Prerequisites: existing explicit review scopes; P24 identities should be included
in final reports. This correction precedes P23 coverage assertions and P32
source-correlated evaluation.

- [ ] P25.1 Define `reviewed_source_group_count` from eligible reviewed coverage,
  including fully reviewed clean prose. Keep total identified groups distinct.
- [ ] P25.2 Add a failing fixture with two source groups, each containing eligible
  reviewed prose but no expected issues or emitted findings; require two reviewed
  groups, zero detections, and unavailable precision/recall denominators.
- [ ] P25.3 Add a failing fixture mixing one clean reviewed source and one source
  with a supported issue. Require both groups in the coverage count/table.
- [ ] P25.4 Add tests that unreviewed, unsupported, and context-dependent regions
  do not create eligible reviewed coverage for the affected rule.
- [ ] P25.5 Add a test where only disabled or file-ignored rules were reviewed.
  Require policy exclusions and no eligible reviewed-group credit from those rules.
- [ ] P25.6 Add a partial-region test: a reviewed region counts its group once,
  but only whole eligible reviewed prose words enter its density denominator.
- [ ] P25.7 Add a test for multiple files from the same repository; count the group
  once and retain file/region counts rather than treating files as independent groups.
- [ ] P25.8 Add tests for unidentified groups. Keep them visible as unspecified
  coverage and exclude them from identified-group uncertainty claims.
- [ ] P25.9 Derive reviewed-group coverage from eligible annotations and extracted
  prose, independently of TP/FP/FN events. Reuse existing review-scope predicates.
- [ ] P25.10 Add explicit coverage rows for clean groups without fabricating
  findings, true negatives, or precision/recall observations.
- [ ] P25.11 Keep per-metric contributing groups separate from coverage groups.
  Two clean groups may support density evidence; they do not supply two nonempty
  precision denominators. Test this distinction before any cluster interval.
- [ ] P25.12 Correct uncertainty explanations to use the relevant metric's group
  support. Update report documentation and schema assertions with the new meanings.
- [ ] P25.13 Run the existing legacy and sparse quality fixtures. Verify unchanged
  detection/location counts and document the corrected coverage-only deltas.

Acceptance: reviewed clean material contributes coverage and density without
being mistaken for detections. Unreviewed text and disabled rules cannot inflate
coverage or support an unjustified interval.

Suggested one-line commit: `Include reviewed clean sources in coverage accounting`.

## P26 — Classify C004 placeholders using Python syntax

Targets: `src/proseprobe/rules/code.py`,
`src/proseprobe/data/code_patterns.py`, `src/proseprobe/parsers/python.py`,
`tests/test_rules/test_code.py`, `tests/test_parsers/test_python.py`,
`tests/test_linter.py`, rule documentation and purpose-written corpus fixtures.
Prerequisites: completed P02 and P14; P23 for regression acceptance.

The concrete regression is
`example = "raise NotImplementedError('example')"`.
A source string mentioning a raise statement must not be classified as executable
placeholder code. Preserve C004's existing comment-marker behavior. Use only
`ast` and `tokenize`; never import or execute analyzed source.

- [ ] P26.1 Characterize current C004 comment markers, concrete raises and
  inline `pass`/ellipsis placeholders, including issue spans and ordering.
  Record the narrow legitimate abstract/stub forms the new guard will recognize.
- [ ] P26.2 Add a failing test for the exact string regression, plus a docstring,
  ordinary comment, multiline string and f-string literal mentioning the same
  raise text. Confirm the failures come from the code-only path.
- [ ] P26.3 Replace code-only raw line matching with executable `ast.Raise`
  candidates calling the supported `NotImplementedError` form. Reuse cached
  AST/token data through the smallest parser access method required by C004.
- [ ] P26.4 Run the string/comment negatives and concrete-raise positives.
  Preserve the existing message kind and diagnostic source text for supported
  cases; document any intentional span correction.
- [ ] P26.5 Add failing multiline and Unicode raise-span cases, with a candidate
  after a semicolon and multiple executable candidates on one line. Decide
  diagnostic multiplicity explicitly from the current C004 contract.
- [ ] P26.6 Map AST UTF-8 columns through the existing P02 conversion; select
  physical tokens for the actual raise/call span. Run parser and C004 span tests.
- [ ] P26.7 Add failing inline negatives where `pass` or `...` occurs inside a
  string before `# TODO` or `# placeholder`; add real `pass` and literal ellipsis
  statement positives with the same comments.
- [ ] P26.8 Require the corresponding executable statement before classifying
  its inline comment. Keep comment-only marker recognition unchanged. Run this
  slice's positives and negatives.
- [ ] P26.9 Add paired tests for statically recognizable `abc.abstractmethod`
  declarations versus concrete incomplete methods. Cover recognized imported
  aliases only if their source bindings can be proved without imports.
- [ ] P26.10 Add the narrow abstract-contract guard supported by those tests.
  Unknown decorators must not imply that a declaration is abstract. Run C004
  tests and verify unchanged concrete-placeholder behavior.
- [ ] P26.11 Add paired overload/Protocol stub tests only for forms statically
  recognized from source imports/decorators/base classes. Preserve concrete
  method bodies that coexist with overload declarations.
- [ ] P26.12 Add the supported stub guard without broad name-based
  exclusions; leave unresolved aliases and class bases computed at runtime unsupported.
  Run the stub and ordinary-placeholder matrix.
- [ ] P26.13 Add invalid-Python/tokenization tests. Assert that actual comments
  remain available but C004 does not guess executable raises from malformed
  source. Add only the fallback needed by the documented contract.
- [ ] P26.14 Add focused CLI and corpus regressions for the string false positive
  and a real placeholder. Run P23 and P33 checks; update C004 documentation to
  describe syntax-backed scope and conservative guards.

Acceptance: text mentioning placeholder code is not mistaken for executable
code; narrow recognized abstract/stub contracts remain legitimate; existing
comment-marker diagnostics and static source mapping are preserved.
Suggested one-line commits: `Use Python syntax for placeholder raises`;
`Require executable statements for inline placeholders`;
`Preserve recognized abstract and stub contracts`.

## P27 — Attach G038 comparison evidence to the claim

Targets: `src/proseprobe/rules/grammar.py`,
`src/proseprobe/parsers/prose.py` only if an existing scope boundary is missing,
`tests/test_rules/test_grammar.py`, `tests/test_parsers/test_prose.py`,
`quality/annotations.json` and purpose-written regression fixtures.
Prerequisites: P18; P23; completed P10.

Replace the raw four-line lookback with an explicit bounded prose-evidence
contract. A measurement before an unrelated heading must not exempt
`The software is safer.` Keep G038 experimental, INFO/LOW; this is a
comparison-context check rather than a claim-truth detector.

- [ ] P27.1 Characterize valid current direct comparisons, questions,
  hypotheticals and literal wording discussion. Record which old negatives
  relied only on unrelated nearby measurements and need reviewed correction.
- [ ] P27.2 Add a failing regression with a measured sentence, then a heading,
  then `The software is safer.` Assert the claim is reported despite the prior
  number. Add a fully explicit `safer than ...` negative.
- [ ] P27.3 Replace the raw-line window for this slice with existing prose scope
  boundaries. Run the heading-isolation and explicit-comparison tests.
- [ ] P27.4 Add failing paragraph, list-item, blockquote, Python-owner, fenced
  code and inline-code boundary cases for unrelated comparison evidence.
- [ ] P27.5 Restrict evidence to the declared same-scope unit. Do not introduce
  a general parser redesign; run the scope-boundary matrix.
- [ ] P27.6 Add paired clauses where an unrelated quantity, table, benchmark
  mention or `first`/`other` occurs next to a comparative. Assert that such words
  alone do not exempt `safer`, while an attached named target does.
- [ ] P27.7 Require a source-validated target attached to the particular claim,
  reusing P10's bounded clause logic where its semantics match. Run these cases
  and preserve complete-predicate source validation from P18.
- [ ] P27.8 Add paired numeric comparisons with an explicit target and a mere
  standalone quantity. A number alone cannot establish what was compared.
- [ ] P27.9 Add only the explicitly supported numeric comparison forms.
  Run their focused tests; unsupported measurements retain advisory findings.
- [ ] P27.10 Add an immediately adjacent sentence with an explicit comparison
  and an ambiguous adjacent sentence. Decide whether the first supported form
  can be bound conservatively; defer ambiguous cross-sentence references.
- [ ] P27.11 Add a cross-sentence exemption only if the tests establish a
  clear attachment within the same scope. Otherwise keep the minimum same-clause
  policy and record the deferred forms. Run the declared evidence matrix.
- [ ] P27.12 Verify Unicode/wrapped claim spans, repeated claims with different
  targets, explicit suppression and confidence filtering. Update purpose-written
  annotations with reasons for intentional judgment changes, then run P23/P33.
- [ ] P27.13 Submit untouched natural development examples and G038 findings to
  P32's independent review. Promote neither severity nor profile membership
  from regression-only precision.

Acceptance: unrelated text cannot exempt a comparative; supported directly
attached comparisons remain clean; G038's experimental status and documented
limitations remain visible.
Suggested one-line commit: `Require claim-local evidence for undefined
comparatives`.

## P28 — Check explicit C009 variadic parameter kinds

Targets: `src/proseprobe/rules/code.py`,
`tests/test_rules/test_code.py`, `tests/test_parsers/test_python.py`,
C009 documentation and purpose-written regression fixtures.
Prerequisites: completed P14; P23.

`def f(args)` accompanied by `:param *args:` currently passes. Compare explicit
stars with the parser's existing `signature_parameters` kind metadata. Unstarred
Sphinx fields remain valid for ordinary and variadic parameter names; keep the
conservative unstarred forwarded-keyword behavior for `**kwargs`.

- [ ] P28.1 Add failing `:param *args:`/ordinary-`args` and
  `:param **kwargs:`/ordinary-`kwargs` tests. Assert one mismatch, source name
  endpoints and a message identifying the declaration/signature conflict.
- [ ] P28.2 Compare `*` to `var_positional` and `**` to `var_keyword` using existing
  metadata. Preserve C009's missing-name path; run these focused tests.
- [ ] P28.3 Add failing swapped-star tests for `*args` documented as `**args`
  and `**kwargs` documented as `*kwargs`. Add matching starred negatives.
- [ ] P28.4 Correct only the explicit-kind comparison and run the full paired
  kind matrix: ordinary, positional-only, keyword-only, variadic positional and
  variadic keyword parameters.
- [ ] P28.5 Add characterization assertions for unstarred variadic fields and
  unstarred delegated keys accepted by `**kwargs`. Do not require stars when
  they were omitted intentionally.
- [ ] P28.6 Verify NFKC names, typed Sphinx fields, async/nested functions,
  decorators marked `has_dynamic_decorators`, literal examples and malformed Python using existing
  cases plus missing explicit-kind assertions.
- [ ] P28.7 Add a focused CLI/corpus mismatch and its legitimate counterpart.
  Update C009's description only as needed; keep its ID and experimental
  metadata stable. Run P23 and P33 checks.

Acceptance: explicit stars agree with the declared parameter kind; unstarred
legitimate fields and conservative forwarded-keyword contracts keep their
existing behavior.
Suggested one-line commit: `Check explicit variadic docstring parameter kinds`.

## P29 — Add an experimental explicit return-type conflict check

Targets: `src/proseprobe/parsers/python.py`, `src/proseprobe/rules/code.py`,
`src/proseprobe/rules/__init__.py`, `src/proseprobe/config.py` only if its
experimental registry requires an entry, parser/rule/metadata/CLI tests,
`quality/annotations.json`, generated rule documentation.
Prerequisites: completed P14; P28 for reusable physical-field extraction; P23;
P24; P32 before any profile promotion.

Start with the unambiguous conflict `-> None` versus an explicit Sphinx
`:rtype: int`. The finding reports the inconsistency and asks the author to check
both declarations; it must not infer the intended runtime return value. Reserve a
new stable rule ID only after checking the current registry. Keep the rule
experimental with provisional INFO/MEDIUM metadata and available through existing explicit-selection policy;
do not change named profiles.

- [ ] P29.1 Define the first supported annotation/doc-type pair and the skip
  contract. Limit initial coverage to physical Sphinx fields and statically
  recognized types; defer Google/NumPy prose, aliases, unions, generics,
  overloads, generators, decorators marked `has_dynamic_decorators` and unresolved bindings.
- [ ] P29.2 Add a failing parser metadata test for a function annotated `None`,
  its nested/async counterparts and a function lacking a return annotation.
  Assert ownership and source-coordinate mapping.
- [ ] P29.3 Expose the smallest immutable return-annotation metadata required by
  this rule without changing the existing parameter tuple or AST cache contract.
  Run focused parser tests.
- [ ] P29.4 Add a failing rule test for `def f() -> None` with `:rtype: int`,
  plus a matching `:rtype: None` negative. Assert one finding at the documented
  type's exact physical source span.
- [ ] P29.5 Add the single explicit conflict and a neutral diagnostic.
  Reuse existing physical field/example guards where they match this rule's
  contract. Run the first positive/negative slice.
- [ ] P29.6 Add failing tests that literal directives, doctests, fenced
  examples, string fragments and a different function's fields cannot create
  a conflict. Add the smallest ownership/example guards and rerun them.
- [ ] P29.7 Add failing unsupported-case negatives for unions/Optional, aliases,
  rebound type names, quoted unresolved annotations, overloads, decorators marked
  `has_dynamic_decorators`, malformed Python and duplicate/conflicting `:rtype:` fields.
- [ ] P29.8 Add conservative guards; do not report a declaration when either
  side is unresolved. Run supported and unsupported cases together.
- [ ] P29.9 Consider additional mutually exclusive scalar pairs one at a time.
  For each accepted pair, first add a disagreement positive and valid subtype
  or conversion negatives. Exclude `bool`/`int`, numeric compatibility and
  subclass judgments unless a sound contract is proved; defer otherwise.
- [ ] P29.10 Check registry IDs and add the rule through the existing factory,
  metadata and experimental selection mechanisms. Add failing registration,
  `explain`, explicit-select and unchanged-profile assertions before wiring it.
- [ ] P29.11 Add corpus positives/negatives, suppression, confidence-policy,
  JSONL/SARIF and UTF-8 span assertions. Generate documentation with the existing
  generator; run P23/P33.
- [ ] P29.12 Evaluate precision and usefulness through P32's blind development
  review. Record unsupported types and disagreements; leave promotion pending
  until predeclared independent evidence supports it.

Acceptance: supported explicit contradictions are reported without guessing
which side is correct; unresolved or semantically compatible cases are skipped;
the new check remains experimental and existing rule IDs/profiles are stable.
Suggested one-line commits: `Expose static return annotation metadata`;
`Add experimental explicit return documentation conflicts`.

## P30 — Add optional project-local file link validation

Targets: `src/proseprobe/config.py`, `src/proseprobe/core/policy.py`,
`src/proseprobe/core/linter.py`, `src/proseprobe/rules/markup.py`,
`src/proseprobe/rules/__init__.py`, `src/proseprobe/parsers/markdown.py` only if
shared parsing extraction is justified, config/linter/markup/CLI tests,
`tests/test_rule_quality.py`, generated documentation and corpus fixtures.
Prerequisites: completed P15; P18; P23; P24; P32 before promotion.

The initial example is `[Install](setup.md#install)` when `setup.md` is missing.
Enable the capability only with an explicit project root and documented local
path/renderer policy. Do not infer website routes, check remote URLs, perform
network requests, or silently use the process working directory. Ordinary scans
and stdin remain unchanged when this capability is off. Keep M011 responsible
for same-document fragments; do not duplicate M005's duplicate-reference check.

- [ ] P30.1 Record supported targets: literal relative Markdown file paths,
  optional fragments under the existing GitHub anchor policy, and reference
  destinations. Define root-relative path behavior, query handling, generated
  route exclusions, unreadable targets and unsupported renderer outcomes.
- [ ] P30.2 Add a failing config test showing the capability off by default,
  invalid roots rejected and explicit roots resolved relative to the declared
  configuration source. Add unknown-option and show-config assertions.
- [ ] P30.3 Add the smallest explicit root/enable configuration supported
  by that contract. Run focused config tests before adding filesystem reads.
- [ ] P30.4 Add a failing linter test proving a scan context supplies the
  project root independently of cwd and independently of source-file discovery.
  Assert no project-local checking for virtual stdin without an explicit
  supported context.
- [ ] P30.5 Choose the smallest project-aware integration supported by the test:
  explicit rule construction/context injection with a scan-scoped target reader.
  Keep `Rule.check(content, filename)` compatibility for existing rules; avoid a
  global filesystem service or unrelated rule framework migration.
- [ ] P30.6 Add failing temporary-project tests for a missing `setup.md`, an
  existing sibling and a nested `../setup.md` still inside the root. Assert
  destination source spans and one finding per supported broken occurrence.
- [ ] P30.7 Add literal relative-file resolution within the explicit root.
  Run these cases with the same inputs under different cwd values.
- [ ] P30.8 Add failing boundary tests for `..` escape, symlink escape,
  percent-encoded separators, absolute filesystem paths and malformed encoding.
  Declare unsupported/out-of-root behavior without reading outside the root.
- [ ] P30.9 Enforce the boundary before target access using standard-library path
  and URL parsing. Run access-spy assertions proving out-of-root files were never
  opened; avoid reporting unsupported routes as definitely missing files.
- [ ] P30.10 Add failing tests for inline links with titles, balanced parentheses,
  Unicode/spaces, escaped destinations and used reference definitions. Add
  image/code/frontmatter/external/mailto/generated-route negatives.
- [ ] P30.11 Reuse M011's proven destination parsing through a narrowly shared
  helper only where both rules need it. Compare M011 complete results before and
  after extraction, then run both markup matrices.
- [ ] P30.12 Add failing `setup.md#install` cases for a present matching anchor,
  a missing anchor, duplicate headings and explicit HTML IDs. Assert that target
  fragment checking requires the explicit supported renderer.
- [ ] P30.13 Reuse the same renderer-specific anchor policy as M011. Do not
  guess mdBook/MDX/Liquid anchors. Run cross-file and same-file fragment tests.
- [ ] P30.14 Add failing scan tests for multiple links to one target, a target
  that changes between scans, unreadable/malformed UTF-8 targets and a target
  omitted by discovery. Assert bounded per-scan reads and documented errors.
- [ ] P30.15 Add a small scan-local target cache, reset for each scan.
  Distinguish missing from unreadable/unsupported targets; preserve existing
  input-error and files-checked semantics according to the declared contract.
  Run read-count tests without wall-clock thresholds.
- [ ] P30.16 Check registry IDs and add an experimental rule entry. Add failing
  explicit-selection, disabled-setting/severity-override, profile, provisional
  INFO/MEDIUM metadata,
  suppression and JSONL/SARIF assertions before connecting the factory.
- [ ] P30.17 Extend evaluator setup with the same explicit project context and
  provenance, then add a production/evaluation parity regression. Record the
  explicit context in an enabled all-rules track; default production keeps this
  optional capability off and records excluded positives. No implicit
  root discovery or external holdout reads are allowed.
- [ ] P30.18 Add a small purpose-written linked-file corpus and documentation
  covering supported roots/renderers/routes. Run P23/P33, then obtain P32's
  independent Markdown precision review before any promotion.

Acceptance: opt-in scans find supported missing files and fragments using an
explicit root/renderer contract; unsupported generated routes remain honest;
target reads stay inside the root and scan context; existing off-by-default
behavior, M005 and M011 contracts stay intact.
Suggested one-line commits: `Add explicit project context for local links`;
`Check optional project-local Markdown targets`;
`Validate supported cross-file fragments`.

## P31 — Evaluate and repair suggestion usefulness

Targets: `src/proseprobe/data/vocabulary.py`,
`src/proseprobe/data/phrases.py`, `src/proseprobe/rules/vocab.py`,
`tests/test_rules/test_vocab.py`, `tests/test_linter.py`,
`benchmarks/quality_scoring.py` and evaluation manifests only for the declared
human usefulness labels, suggestion documentation.
Prerequisites: P23; P24; P32 for semantic judgments.

The concrete regression is V001's `crucial` → `important`: the replacement is
itself detected by the effective default policy. Suggestions remain review
prompts; the linter does not rewrite files. A rescan checks whether the targeted
finding is resolved, while human review checks meaning, grammar and usefulness.
Neither a lower total finding count nor a passing rescan proves semantic quality.

- [ ] P31.1 Inventory suggestion-bearing rules and classify each output as a
  literal replacement, contextual review instruction or absent suggestion.
  Record existing inflection guards and overlaps; keep public Issue fields
  unchanged unless a concrete compatibility need arises.
- [ ] P31.2 Add a failing test for a sentence containing `crucial`, applying its
  literal suggestion only within the exact issue span in a disposable test
  buffer. Rescan under the same effective policy and assert the targeted
  vocabulary issue is resolved without a newly introduced warning.
- [ ] P31.3 Review the candidate replacement in context. Choose a supported
  alternative or omit the literal suggestion when no reliable substitute
  preserves the intended strength; do not ignore `important` to make the test
  pass. Run the pair and existing suggestion-table tests.
- [ ] P31.4 Add paired default and explicitly expanded vocabulary configurations.
  If a suggested literal is disallowed by the effective configured vocabulary,
  assert that the suggestion is withheld or replaced by neutral review guidance.
- [ ] P31.5 Add the smallest policy-aware suggestion check within the
  rule's existing configured instance. Run configured/default tests and preserve
  deterministic ordering and rule metadata.
- [ ] P31.6 Add a parameterized rescan characterization for literal suggestion
  entries using meaningful full sentences. Preserve precise spans, inflection,
  punctuation, quotation ownership and technical terminology in fixtures.
- [ ] P31.7 Turn each reproduced suggestion cycle or new warning into its own
  failing paired test; review and repair one entry at a time. Do not recursively
  apply suggestions or replace the catalog through a blanket filtered mapping.
- [ ] P31.8 Add valid near-miss tests where a literal replacement would alter
  technical meaning or grammatical agreement. Withhold only the unsupported
  suggestion, preserving the finding when its review prompt remains justified.
- [ ] P31.9 Run complete V001 and replacement-rule tests plus an effective-policy
  linter integration test. Document intentional suggestion changes and omissions;
  run P23/P33 before committing the catalog correction.
- [ ] P31.10 Define P32's usefulness questions separately: was the original
  finding helpful, did the suggestion fit the sentence, did it preserve meaning,
  and would the reviewer accept it? Permit `context-dependent` and unresolved
  judgments rather than forcing binary correctness.
- [ ] P31.11 Add failing evaluator tests for separate human suggestion judgments,
  missing judgments, paired source/revision provenance and report denominators.
  Keep automatic rescan outcomes separate from semantic usefulness scores.
- [ ] P31.12 Add only the agreed label/report extension through P24-bound
  annotation inputs. Run scorer tests; report annotation coverage and unresolved
  judgments so unreviewed suggestions are not counted as successful.
- [ ] P31.13 Collect blinded human judgments on untouched development sources
  and reserved revision pairs through P32. Review recurring failures, freeze
  changes, and use the holdout only for the declared final evaluation.

Acceptance: supported literal suggestions do not introduce the assessed targeted
cycle under the effective policy; inflection/technical-meaning guards remain;
semantic usefulness is measured from explicit human judgments and honest
coverage, with no rewrite mode or automatic success inferred from fewer findings.
Suggested one-line commits: `Avoid suggestions rejected by effective vocabulary
policy`; `Add suggestion rescan regressions`;
`Report independently reviewed suggestion usefulness`.

## P32 — Complete independent evaluation and extend source coverage

Targets: `quality/external/README.md`, `quality/sources.json`,
`quality/external/split-freeze.json`, a separate extension manifest/freeze,
`benchmarks/corpora.py`, `benchmarks/quality_scoring.py`,
`benchmarks/rule_quality.py`, `tests/test_corpora.py`,
`tests/test_quality_scoring.py`, independently supplied annotation artifacts.

Prerequisites: P24/P25 for accepted annotation reports. Blind sampling and
reviewer preparation can begin earlier. P23 controls curated regressions;
independent precision thresholds and rule/profile promotion require this package.

This package completes the open human-evaluation work in P06A.7–P06A.9,
P06B.3/P06B.6, P06C.3/P06C.7, P06D.3, P12.11, P13.8, P15.9,
P16.6–P16.8, and P16.10a. Update those earlier checkboxes only when their actual
acceptance evidence exists. P06D.5 remains conditional on clarified reuse terms.

### P32A — Preserve the pilot and declare coverage

- [ ] P32A.1 Revalidate the original 300-unit manifest/freeze identities without
  reading holdout prose, generating findings, or altering split assignments.
- [ ] P32A.2 Record the existing 170-development/130-holdout coverage by dataset,
  format, repository, author/pair group where available, and renderer/dialect.
  State that all 80 Python functions are development samples from two repositories.
- [ ] P32A.3 Declare supported claim populations before annotation: complete
  Markdown structure, Python docstrings/comments, sentence-level grammar/clarity,
  and explicit renderer-dependent checks. Keep their denominators separate.
- [ ] P32A.4 Specify which rule contracts each population can evaluate. Sentence
  inputs cannot establish document-structure recall; CodeSearchNet search labels
  cannot establish prose correctness; CommonMark cases establish parser conformance.
  Mark renderer checks on unsupported template dialects unsupported rather than clean.
- [ ] P32A.5 Keep new sources in a separately versioned extension manifest and
  freeze. Preserve the original pilot for its already declared evaluation purpose.
- [ ] P32A.6 Select fresh Python holdout repositories with no overlap with the
  development repositories, authors/projects where known, or related revisions.
  Prefer complete modules when surrounding code is needed to judge documentation.
- [ ] P32A.7 Select additional Markdown repositories in development and reserved
  holdout to reduce single-repository/domain dependence. Record the intended
  renderer and template dialect before selecting files.
- [ ] P32A.8 Declare an attainable source-group count and balanced sample budget
  before acquisition. Several independent repositories per format are the pilot
  goal; record unavailable genres rather than treating a sample count as coverage.
- [ ] P32A.9 Verify each candidate's pinned revision, upstream content license,
  attribution, access, and intended reuse before accepting cached text. Treat a
  hosting project's license as insufficient evidence for unrelated dataset contents.
- [ ] P32A.10 Add failing tiny-fixture tests for cross-manifest repository/pair
  overlap, duplicate bytes, normalized near duplicates, and split leakage.
- [ ] P32A.11 Extend existing split validation only as required to check the
  original and extension together; keep downloads out of unit tests.
- [ ] P32A.12 Cache and checksum the accepted development/holdout sources without
  detector-based selection. Freeze identities and assignments before further tuning.
- [ ] P32A.13 Export the new blind packet using P24 and verify its index and source
  identities. Holdout contents stay hidden from implementers during development.
- [ ] P32A.14 Pin the [CommonMark 0.31.2 examples](https://spec.commonmark.org/0.31.2/)
  and verify their reuse terms before copying fixtures. Record version, source
  checksum and the supported parser features selected for conformance checks.
- [ ] P32A.15 Map selected fence, inline-code, link/reference, heading and HTML
  examples to the existing extraction/masking contracts. Keep unsupported
  syntax and renderer extensions explicit; do not require a full HTML renderer.
- [ ] P32A.16 Add offline conformance cases using the current parser test files.
  For each reproduced mismatch, record a failing extraction/span assertion,
  apply the smallest correction, and run the affected parser/rule tests.
- [ ] P32A.17 Report conformance results separately from human writing-quality
  metrics. These examples supply syntax contracts, not useful-finding labels.

Acceptance: extension material adds independent projects and missing Python
holdout coverage without modifying or relabeling the original 300 sources.
Licenses, renderer limitations, and unsupported populations remain explicit.

Suggested one-line commit: `Freeze independent Python and Markdown evaluation sources`.

### P32B — Blind annotation and adjudication

- [ ] P32B.1 Obtain human reviewers for eligible sources and record reviewer
  identifiers. Do not substitute agent judgments for independent human labels.
- [ ] P32B.2 Prepare the review protocol and selected rule-contract snapshots.
  Require issue usefulness, intended meaning, exact spans, supported rules,
  exhaustive reviewed coverage, and unresolved-status reasons.
- [ ] P32B.3 Choose the double-annotation subset before showing any predictions;
  distribute it across formats and source groups. Record its selection seed/list.
- [ ] P32B.4 Add offline validator tests for incomplete coverage declarations,
  out-of-bounds spans, missing reviewer identity, source mismatch, and unresolved
  judgments accidentally represented as clean negatives.
- [ ] P32B.5 Give reviewers randomly selected originals and necessary source
  context only. Withhold detector output and native revisions during this first pass.
- [ ] P32B.6 Collect the initial annotations of eligible random prose, including
  independent issues the detector may miss and fully reviewed clean regions.
- [ ] P32B.7 Collect the second review of the preselected subset independently;
  retain both original judgments rather than overwriting disagreements.
- [ ] P32B.8 Record agreement/disagreement counts with their denominators, then
  adjudicate each disagreement with a rationale and reviewer identity.
- [ ] P32B.9 Freeze the initial adjudicated labels and coverage before generating
  detector predictions. Keep genuinely unresolved issues context-dependent.
- [ ] P32B.10 Run a separately identified triggered-finding review after the blind
  pass. Keep discovered labels, additional trigger-only labels, and coverage apart;
  trigger-only review supplies precision evidence rather than exhaustive recall.
- [ ] P32B.11 For sparse rules, request independently authored positives and near
  misses; mark them purpose-written and score them separately from natural text.
- [ ] P32B.12 Validate the accepted annotation artifacts with strict P24 binding
  and P25 coverage checks. Record actual reviewed quantities and remaining gaps.

Acceptance: supported natural-text recall uses exhaustive blind-reviewed regions,
precision uses explicit judgments, disagreements remain auditable, and no human
labels or negative coverage are inferred from absence of detector findings.

Suggested one-line commits: `Document blind review and adjudication protocol`;
`Record independently reviewed pilot annotations` (only after review exists).

### P32C — Use native edits as supplementary evidence

- [ ] P32C.1 Write a small W&I error-type mapping table linking only supported
  native edit categories to specific rule contracts. Record unsupported categories,
  annotator identity, and automatically assigned ERRANT types separately.
- [ ] P32C.2 Add failing offline tests for supported edits, unsupported edits,
  insertions/deletions, alternate annotators whose edits overlap, and artifacts
  caused by preprocessing. Preserve the tokenized-source coordinates already established in P06C.4.
- [ ] P32C.3 Add only the reviewed mapping; ambiguous native labels require
  judgment and cannot automatically become rule positives or negatives. An empty supported mapping
  is valid when no existing rule matches a native category.
- [ ] P32C.4 After blind original review is frozen, provide all four JFLEG and all
  ten ASSET references under their existing pair identities and access terms.
- [ ] P32C.5 Add deterministic paired-report tests for a resolved useful finding,
  a retained valid warning, a new incorrect warning, and unavailable correspondence.
- [ ] P32C.6 Record human judgments of usefulness and meaning preservation for
  each relevant before/after change; use native revisions as alternatives, not as
  ten independent sources or as automatic clean ground truth.
- [ ] P32C.7 Report paired warning changes beside their human outcomes and sample
  sizes. Do not use warning reduction, GLEU, or simplification labels alone as proof
  that this linter improved prose.
- [ ] P32C.8 Keep JFLEG's CC BY-NC-SA 4.0, ASSET's CC BY-NC 4.0, and W&I's
  noncommercial restrictions with materials and outputs as applicable. Continue
  excluding LOCNESS from this pilot under the documented distribution restriction.
- [ ] P32C.9 Retain exclusion of the README simplification package while reuse
  terms remain unresolved. Recheck primary terms only if this conditional source
  is pursued; accessible downloads and commit keywords do not establish permission
  or reliable clarity labels.
- [ ] P32C.10 If README reuse terms become clear, first add tiny offline
  revision-pair tests, then manually verify sampled revisions and freeze their
  source groups. Keep weak commit-keyword labels distinct from reviewed labels.

Acceptance: native edits add evidence about actionability without expanding
unsupported rule coverage or silently assigning quality judgments.

Suggested one-line commit: `Report independently judged revision-pair usefulness`.

### P32D — Report effectiveness and decide promotion

- [ ] P32D.1 Generate strict development reports for all-rules and the unchanged
  default production policy. Retain raw counts, eligible misses, exact/full-span
  accuracy, reviewed words, source coverage, exclusions, and usefulness judgments.
- [ ] P32D.2 Define a source-correlated uncertainty method and minimum contributing
  groups before implementation. Use repositories/authors or appropriate independent
  source groups, keeping every paired revision within its group.
- [ ] P32D.3 Add deterministic toy-group tests with unequal group sizes, clean
  reviewed groups, zero denominators, a dominant repository, and too few groups.
  If resampling is used, fix its seed and report its procedure and support.
- [ ] P32D.4 Calculate the justified interval in evaluation-only code without a
  runtime dependency. Return unavailable intervals with reasons when group support
  is inadequate; retain Wilson intervals as explicitly sample-only where useful.
- [ ] P32D.5 Publish per-rule/profile/format/context/source-group results with
  denominators. Avoid an aggregate improvement claim that conceals a regression
  in production warnings, supported recall, or a sparsely covered rule.
- [ ] P32D.6 Review P12 technical/quotation precision, P13 repeated words, P15
  renderer-specific anchors, and the new P26–P31 slices on development evidence.
  Preserve exact quotations and meaningful terminology when judging suggestions.
- [ ] P32D.7 Choose any proposed threshold, confidence, severity, default, or named
  profile change from development evidence and record a concrete rationale. Keep
  rules experimental when support is inadequate; no promotion is required.
- [ ] P32D.8 Predeclare independent quality targets, supported populations, minimum
  sample/group support, and treatment of unavailable metrics before opening holdout.
  Keep these targets distinct from P23's curated no-new-regressions gate.
- [ ] P32D.9 Freeze the candidate implementation/policy and evaluate once on the
  reserved holdout through the same strict report path; retain misses and raw false
  positives instead of altering labels to pass the target.
- [ ] P32D.10 Have human reviewers assess holdout usefulness under the frozen
  contracts. Publish agreement, unresolved cases, and source-correlated uncertainty.
- [ ] P32D.11 If holdout results prompt tuning, reclassify the inspected material
  as development evidence and reserve fresh source groups before another independent
  claim. Record the decision without silently reusing the same holdout.
- [ ] P32D.12 Update P06/P12/P13/P15/P16 pending steps with links to the real
  annotation/report evidence, or leave them open with the specific missing prerequisite.

Acceptance: effectiveness claims identify the population, independent reviewers,
exact code/data/policy, reviewed denominators, and uncertainty. Experimental rules
are promoted only when the declared evidence supports the concrete policy change.

Suggested one-line commits: `Report source-group uncertainty for independent evaluation`;
`Record independent effectiveness results and policy decisions`.

## P33 — Integrate the continuation and preserve release boundaries

Targets: all changed package tests, `PLAN.md`, `CHANGELOG.md`, `SPEC.md`,
`README.md`, `docs/rules.md`, `quality/README.md`, `RELEASE_BLOCKERS.md`.

Prerequisites: complete selected engineering slices P18–P31. Human-dependent
P32 work may remain open with its actual unmet prerequisites; it cannot be
represented as completed engineering verification. Reuse P17's acceptance gates
but rerun them against the continuation's final state.

Slice gate: run the focused tests, related integration tests, `make check`,
`make dogfood`, and the applicable quality reports after each coherent behavior
change. Add the P23 strict regression target once available. Review corpus
deltas and edited prose before a one-line implementation commit. Performance
checks are required when changed scan behavior, target reads, or measurements
could affect their contracts; deterministic unit tests do not time real hardware.

- [ ] P33.1 For each completed slice, record its red regression, focused green
  command, implementation commit, and explained corpus delta in the progress log.
- [ ] P33.2 For each new rule, repeat the P17A metadata, registration, selection,
  experimental/profile, executable examples, suppression, reporter-span, and
  baseline checks. Prior checked boxes do not cover new IDs automatically.
- [ ] P33.3 Update user-visible behavior and compatibility documentation for each
  completed correction, including annotation/report schemas and optional feature
  prerequisites. Generate inventory blocks through `make rule-docs`.
- [ ] P33.4 Scan edited prose with the repository's effective policy and existing
  baseline in JSON Lines. Review exact technical examples rather than changing
  them or refreshing the baseline to eliminate intentional findings.
- [ ] P33.5 Run `rtk proxy make rule-docs-check check dogfood rule-quality nfr-check`
  on the final implementation state. Run the new P23 regression gate separately
  if its package is complete; a report-only score remains a different outcome.
- [ ] P33.6 Verify filesystem and stdin text/JSON/JSON Lines/SARIF scans with
  Unicode, clean files, invalid configuration, and unreadable input. Retain
  documented exit codes and configuration precedence.
- [ ] P33.7 Verify watch mode and baseline maintenance after the P18–P22 changes,
  including legacy readable baselines and deterministic source coordinates.
- [ ] P33.8 Rerun the full tests under Python 3.11, 3.12, and 3.13 where local
  interpreters exist. Record unavailable environments rather than claiming coverage.
- [ ] P33.9 Require the remote Ubuntu Python 3.11–3.13 matrix for the exact final
  commit when remote CI is available. Keep P17C.2 open until that evidence exists;
  local matrix results do not substitute for remote execution.
- [ ] P33.10 Compare full-scan timing, startup, and memory using P24C's equal
  workload/policy/diagnostics identities and recorded environments. Investigate
  material regressions without adding machine-specific unit-test thresholds.
- [ ] P33.11 Publish current regression results for both policies and disposition
  every changed mismatch. The starting continuation snapshot is 336 TP/6 FP/0 FN
  all-rules and 106 TP/4 FP/0 FN production; those are recorded evidence, not
  immutable numbers or independent natural-text effectiveness estimates.
- [ ] P33.12 Review every continuation package against its acceptance criteria.
  Mark completed, intentionally deferred, or awaiting human/external evidence with
  a reason. Preserve the original execution record and frozen pilot identities.
- [ ] P33.13 Record the final commit, clean/dirty state, source/report identities,
  successful commands, limitations, and remaining P32 judgments in `PLAN.md`.
- [ ] P33.14 If a release is later requested, follow `RELEASE_BLOCKERS.md` for
  that exact release commit, including package inspection and publication identity.
  Do not create a release/tag or publish as part of this plan alone.

Acceptance: the final engineering state passes the repository gates with reviewable
commits and current evidence. Independent evaluation, unavailable remote checks,
conditional datasets, and publication remain accurately distinguished.

Suggested one-line commit: `Record continuation verification and remaining evaluation gates`.


## Continuation execution record

### Baseline — 2026-10-10

Starting commit: `d3cb7a1`. The worktree was clean. `make check dogfood
rule-quality` passed with 2,665 tests and the recorded 336 TP/6 FP/0 FN
all-rules corpus results. Independent human review remains pending; a reviewer
request is open. The frozen external holdout is unopened.

### P19 — Automatic configuration errors

Four regressions failed before correction: malformed tool/project TOML, a
deterministic read denial, and CLI error handling. Discovery now raises the
existing `ConfigError` with its source path and diagnostic; CLI exit 2 writes
no findings or traceback. Existing precedence is preserved. All 259 focused
configuration/CLI tests pass. An isolated snapshot containing only this slice
passed `make check dogfood rule-quality`; raw quality results are unchanged.
The snapshot excludes unrelated parallel edits and uses its own source tree.
Git-root boundary work remains open.

### P18 — Requirement predicates use original source

Eleven regressions failed before correction. G024/G025/G037 and four additional
reproduced consumers (G016/G017/G019/G022) now validate their full source
predicates. G037 definition suffixes also require literal evidence. Eighty-four
complete-record characterizations preserve ordinary and wrapped positives across
Markdown and Python contexts. HTML equivalents were already clean and remain
paired characterizations. Existing continuation-prefix handling was extracted
for guard reuse; markup stripping did not expand. The isolated slice passed
`make check dogfood rule-quality`, preserving all 336 TP and six known FPs.
Quantity/reliability predicates and remaining helper/integration checks are open.

### Independent claims — user decision

On 2026-10-10 the user requested deferral of independent effectiveness claims.
P32 human annotation, semantic usefulness judgments, calibration, holdout scoring
and profile promotion remain deferred. Engineering and blind-packet preparation
continue. No independent human labels or population claims will be inferred.

### P19 — Git-root discovery boundary

Two directory/worktree-marker regressions failed before correction. The upward
search now checks the starting directory's Git marker before climbing and still
includes a root-local configuration. Ten added tests preserve nested precedence,
user fallback and explicit paths beyond the automatic boundary. All 269 focused
configuration/CLI tests and the isolated `make check dogfood rule-quality`
snapshot pass. Configuration documentation now states both error and boundary
contracts. P19 is complete; raw corpus detections remain unchanged.
