# ProseProbe improvement plan

Status: in progress; checkboxes record verified work.
Assessment date: 2026-10-09.

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

- [ ] P01.1 Add a failing discovery test in a temporary Git repository with
  `/docs/ignored.md` in `.gitignore`, invoking discovery with `Path("docs")`.
  Assert that the ignored file is absent and an ordinary sibling is present.
- [ ] P01.2 Add a test comparing relative and absolute scans of the same directory.
  Compare selected file identities while retaining the documented output paths.
- [ ] P01.3 Correct the coordinate system passed to `git check-ignore`: send
  absolute candidates or paths relative to its working directory, then map the
  results back to discovery candidates.
- [ ] P01.4 Cover overlapping roots and a filename containing spaces. Preserve
  NUL-delimited input and output handling.
- [ ] P01.5 Verify the existing explicit-file override: an explicitly named file
  retains its current Git-ignore behavior, and configured exclusions still apply.
- [ ] P01.6 Preserve behavior outside Git repositories and when Git is unavailable.
  Reuse existing tests unless one of these branches lacks coverage.
- [ ] P01.7 Add a CLI regression for `check docs` that asserts findings and
  `files_checked`, rather than testing only the discovery helper.
- [ ] P01.8 Run the focused discovery and CLI tests, then the package gate.

Acceptance: relative and absolute directory scans select the same files without
changing explicit-file policy, path reporting, or failure handling.

## P02 — Use one coordinate system for Python source mapping

Targets: `src/proseprobe/parsers/python.py`, `tests/test_parsers/test_python.py`,
`tests/test_linter.py`, existing reporter tests.

- [ ] P02.1 Add a failing extraction test for `def résumé(): """delve"""` and
  compare its extracted prose with the ASCII-name counterpart.
- [ ] P02.2 Assert the V001 start and exclusive end columns against the original
  Unicode source, using character positions rather than UTF-8 byte positions.
- [ ] P02.3 Add boundary cases with a non-ASCII parameter name, a multibyte string
  character, and adjacent literal tokens in a docstring.
- [ ] P02.4 Add the smallest conversion from AST byte offsets to character
  offsets. Apply it to both start and end boundaries used for token selection.
- [ ] P02.5 Audit other AST-coordinate consumers, including string-literal
  extraction. Add a regression and change a consumer only if it has the same
  mismatch or violates an existing source-position contract.
- [ ] P02.6 Verify multiline docstrings, comments, async functions, and malformed
  Python using existing cases plus any missing Unicode assertion.
- [ ] P02.7 Exercise the corrected finding through JSON Lines and SARIF; assert
  valid original-source spans and unchanged field semantics.
- [ ] P02.8 Add a corpus positive and a nearby Unicode negative case, then run the
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

- [ ] P03.1 Add a failing parser test asserting one closed block, language
  `python`, and the correct opening and closing lines for this fixture.
- [ ] P03.2 Add a failing linter test asserting no V001 finding inside the block
  and no M007 unclosed-fence error.
- [ ] P03.3 Separate opening delimiter recognition from the information string.
  Retain the first information token as the language where the existing API
  requires it; accept remaining information without interpreting attributes.
- [ ] P03.4 Test backtick and tilde fences, multiple information tokens, empty
  information, and attribute-only forms. Keep invalid backtick information
  strings distinct from valid tilde information strings.
- [ ] P03.5 Preserve strict closing rules: matching delimiter character,
  sufficient delimiter length, and no trailing closing information.
- [ ] P03.6 Verify indentation limits, blockquoted fences, shorter embedded
  delimiters, and source columns using the existing parser contracts.
- [ ] P03.7 Retain a positive M007 test for a genuinely unclosed fence with
  attributes, reported at its opening delimiter.
- [ ] P03.8 Add a quality-corpus negative for the valid fixture and run the parser,
  markup, linter, and package checks.

Acceptance: valid code remains masked from prose checks, while malformed or
unclosed fences still produce accurate diagnostics.

## P04 — Share effective scan policy with evaluation

Targets: `src/proseprobe/cli.py`, `src/proseprobe/core/`, `src/proseprobe/config.py`,
`benchmarks/rule_quality.py`, `tests/test_cli.py`, `tests/test_rule_quality.py`.

- [ ] P04.1 Characterize policy precedence for configured profiles, CLI profiles,
  explicit selections, ignores, severity overrides, and confidence filtering.
  Reuse the existing CLI tests as the reference behavior.
- [ ] P04.2 Add an evaluator-to-CLI parity test on one controlled Markdown file
  and one Python file. Compare complete issue records after normalizing only
  path presentation and output envelopes.
- [ ] P04.3 Extract only reusable policy construction and result filtering into
  core. Keep argument parsing, configuration discovery, and operational output
  in their existing layers; do not create a new framework.
- [ ] P04.4 Add evaluator options for profile, minimum severity, and minimum
  confidence, and test their parsing and invalid-value diagnostics.
- [ ] P04.5 Preserve a named all-rules measurement mode for the existing corpus,
  including experimental rules. Label it separately from default CLI behavior.
- [ ] P04.6 Add parity cases for every built-in profile, no-profile behavior,
  experimental-rule selection, per-file ignores, and inline suppressions.
- [ ] P04.7 Keep baseline filtering out of raw effectiveness measurements.
  Test baselined adoption behavior separately so accepted debt cannot inflate
  reported precision or recall.
- [ ] P04.8 Report effective policy, package version, corpus identity, and metric
  counts in a deterministic machine-readable evaluation result.
- [ ] P04.8a Test that ambient repository or user configuration cannot change a
  frozen evaluation run. Use explicit isolated evaluation configuration, while
  preserving the CLI's ordinary configuration discovery.
- [ ] P04.9 Verify that `check`, stdin, `watch`, and baseline maintenance retain
  their existing policy and exit-code contracts after extraction.
- [ ] P04.10 Run CLI, configuration, profile, evaluator, and package checks.

Acceptance: production-policy evaluation matches the CLI, and all-rules results
remain available with an explicit label and unchanged legacy interpretation.

## P05 — Separate annotation scope, detection, and location scoring

Targets: `benchmarks/rule_quality.py`, `quality/annotations.json`,
`quality/README.md`, `tests/test_rule_quality.py`.

- [ ] P05.1 Add failing tests proving that supplied `end_line` and `end_column`
  survive loading and finding collection. Preserve legacy annotations without
  endpoints as start-only checks.
- [ ] P05.2 Validate endpoint order, nonempty concrete spans, and bounds. Keep
  explicitly permitted zero-width findings distinct from malformed spans.
- [ ] P05.3 Add a scoring case with a correct start and an incorrect end. Require
  detection credit to remain separate from a failed span-accuracy check.
- [ ] P05.4 Add cases for an incorrect start, a missing finding, and duplicate
  findings. Preserve strict exact-location scoring and one-to-one matching.
- [ ] P05.5 Define separately reviewed semantic matches, using stable annotation
  identities or explicit span correspondence. Do not turn arbitrary overlapping
  findings into correct detections.
- [ ] P05.6 Define annotation coverage for external corpora by file, rule family,
  and prose region. Introduce explicit unreviewed and unsupported outcomes for
  material outside that coverage.
- [ ] P05.7 Test that an unmatched finding is a false positive only where
  annotations are exhaustive for the evaluated rule and region.
- [ ] P05.8 Test recall denominators: exclude rules outside the declared policy
  or annotation scope; count eligible positives removed by confidence filtering
  as missed detections. Never derive eligibility from whether a rule fired.
- [ ] P05.9 Preserve strict every-rule positive/negative coverage for the current
  regression corpus. Permit sparse external coverage through a documented
  manifest extension or separate loader, with tests for legacy compatibility.
- [ ] P05.9a Support narrow negative regions in external annotations. Test a valid
  use and a genuine same-rule violation on one line so a line-wide negative
  cannot conceal the distinction. Preserve legacy line-wide negative cases.
- [ ] P05.10 Keep context-dependent adjudications visible. Report how many cases
  are unresolved instead of omitting them from headline metrics.
- [ ] P05.11 Add severity, confidence, file-type, and profile breakdowns with
  denominators. Test empty groups and deterministic ordering.
- [ ] P05.12 Document the schema and scoring definitions; rerun legacy scores and
  explain any change before adopting the new report.

Acceptance: detection quality, source-location accuracy, policy coverage, and
annotation completeness can be assessed separately without hiding mismatches.

## P06 — Build an independent evaluation corpus

Targets: `quality/`, evaluation-only adapters under `benchmarks/`,
`tests/test_rule_quality.py`, new adapter tests where needed.

### P06A — Provenance, sampling, and annotation

- [ ] P06A.1 Define a source manifest with URL, revision, checksum, license,
  attribution, source identity, format, and evaluation split.
- [ ] P06A.2 Test rejection of missing provenance, duplicate sample identities,
  invalid splits, and paths escaping the permitted corpus location.
- [ ] P06A.2a Test a corrupted cached sample and validate its checksum before
  conversion. Keep downloads outside unit tests and external datasets outside
  the published package unless their inclusion is deliberate and licensed.
- [ ] P06A.3 Establish a few-hundred-sample pilot across complete Markdown
  documents, Python docstrings, and comments. Record format and genre counts;
  size alone does not establish representativeness.
- [ ] P06A.4 Freeze development and holdout source identities before rule tuning.
  Split by repository, document, or author as appropriate; keep related revisions
  and before/after pairs in the same split.
- [ ] P06A.5 Test split isolation, including duplicates and near-identical
  excerpts when their source identities are available.
- [ ] P06A.5a Assign GitHub Docs to one split because it is one repository. Obtain
  additional verified, licensed documentation sources for the other splits;
  keep the GitHub Docs revision and its excerpts together.
- [ ] P06A.6 Write annotation guidance for useful findings, false positives,
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
- [ ] P06A.10 Preserve the original 12 false-positive cases as honest regression
  evidence. Record whether each is corrected, explicitly handled by policy, or
  retained as a documented limitation.

### P06B — Technical Markdown and Python

- [ ] P06B.1 Pin a [GitHub Docs](https://github.com/github/docs) revision and select
  full Markdown files with headings, links, frontmatter, tables, fences, and
  Liquid markup. Record its CC BY 4.0 content license and attribution.
- [ ] P06B.2 Add a tiny offline fixture and a failing loader test that preserves
  source text and source identity. Load samples without running templates or
  treating repository content as instructions.
- [ ] P06B.3 Annotate the selected files. Treat published documentation as
  candidate negative material, never as guaranteed error-free ground truth.
- [ ] P06B.4 Select the Python subset of
  [CodeSearchNet](https://github.com/github/CodeSearchNet). Record upstream
  repository and license metadata; its project MIT license does not replace
  the data's upstream licenses.
- [ ] P06B.5 Test a tiny CodeSearchNet JSON Lines adapter for function source,
  docstring text, repository identity, and missing fields. Preserve source
  offsets where available and declare missing surrounding module context.
- [ ] P06B.6 Annotate writing quality independently. Keep code-search relevance
  annotations outside prose-quality scoring.

### P06C — Grammar and fluency

- [ ] P06C.1 Select the development material from
  [W&I+LOCNESS / BEA-2019](https://www.cl.cam.ac.uk/research/nl/bea2019st/),
  recording its non-commercial restriction and archive checksum.
- [ ] P06C.2 Test a tiny M2 reader for token spans, insertions, deletions, no-op
  annotations, and multiple annotators. Do not merge incompatible annotator edits.
- [ ] P06C.3 Map only supported error types to relevant rules. Record unsupported
  categories and automatically assigned ERRANT types separately.
- [ ] P06C.4 Test token-to-source mapping and detokenization around punctuation
  and contractions. Report preprocessing artifacts separately from rule errors.
- [ ] P06C.5 Load [JFLEG](https://github.com/keisks/jfleg) source sentences and all
  four human corrections. Record its CC BY-NC-SA 4.0 license.
- [ ] P06C.6 Test pair identity, missing references, and split preservation on
  small offline files before loading the full selected subset.
- [ ] P06C.7 Review relevant warning changes across source and corrected variants.
  Use detection and actionability metrics; generated-text GLEU scores do not
  directly measure this linter.

### P06D — Simplification and software revisions

- [ ] P06D.1 Load [ASSET](https://github.com/facebookresearch/asset) originals and
  ten human simplifications, recording its CC BY-NC 4.0 license.
- [ ] P06D.2 Test pair identity and references on a tiny offline fixture. Restrict
  interpretation to sentence-level clarity and complexity rules.
- [ ] P06D.3 Review whether relevant warnings disappear after a human revision,
  remain useful, or appear incorrectly. Never treat fewer warnings as sufficient
  evidence of a better revision.
- [ ] P06D.4 Recheck access and licensing for the replication package linked by
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

- [ ] P07.1 Retain the direct-rule benchmark and label what it measures.
- [ ] P07.2 Characterize Markdown and Python parser construction counts in direct
  rule calls and in `Linter`. Distinguish warmed caches from cleared caches.
- [ ] P07.3 Add a failing runner test that proves the full-scan measurement uses
  production policy, file discovery, reading, extraction, and result filtering.
- [ ] P07.4 Add a small offline workspace with both file types, an ignored file,
  and known findings; assert selected files and result equivalence.
- [ ] P07.5 Measure cold-process CLI startup separately from warmed scan timing.
  Include serialization when reporting whole-CLI timing; identify the output
  format and keep it fixed across comparisons.
- [ ] P07.6 Add representative corpus samples, then report median timing,
  variation, bytes processed, files checked, active rule count, and environment.
- [ ] P07.7 Test rate calculations with controlled durations. Use actual batch
  bytes and elapsed time rather than deriving throughput from an unweighted
  average across differently sized synthetic files.
- [ ] P07.7a Test Unicode workloads and compute byte throughput from UTF-8 byte
  length. Include many distinct small files as well as repeated content, so cache
  pressure and cache-friendly measurements remain distinguishable.
- [ ] P07.8 Keep wall-clock thresholds out of ordinary unit tests. Preserve the
  repository's existing startup and memory gates.
- [ ] P07.9 Profile only measured slow paths. Propose a separate measured
  correction if the evidence warrants a cache, traversal, or concurrency change.

Acceptance: benchmark results describe the path measured and can support a
before/after comparison. No optimization is required merely to finish this plan.

## P08 — Make phrase detection independent of line wrapping

Targets: `src/proseprobe/rules/vocab.py`, `src/proseprobe/parsers/prose.py`,
`tests/test_rules/test_vocab.py`, `tests/test_linter.py`, baseline tests.

- [ ] P08.1 Add a failing V009 pair for the same phrase on one line and wrapped:
  `due to the fact that` versus `due to the\nfact that`.
- [ ] P08.2 Assert both source endpoints for the wrapped phrase in Markdown and
  Python documentation. Preserve the single-line diagnostic contract.
- [ ] P08.3 Add negative cases crossing a paragraph, heading, list item, separate
  docstring, or comment/prose boundary.
- [ ] P08.4 Add a masked-gap negative such as `in \`sorted\` order to`. Matching
  whitespace must not manufacture a phrase across hidden code or markup.
- [ ] P08.5 Move the shared replacement-table matcher to source-mapped sentences.
  Accept layout whitespace only within one permitted prose region and verify
  the original source covered by a candidate match.
- [ ] P08.6 Cover the other helper consumers separately: V010, V011, V013, and
  V017. Adapt V011's decision-compound exception to complete multiline spans.
- [ ] P08.7 Inventory older literal phrase matchers. Migrate each affected matcher
  only after its own failing wrap-invariance test; do not rewrite unrelated rules.
- [ ] P08.8 Characterize inline suppression and baseline behavior for multiline
  matches. Verify that distinct matches cannot share an accidental identity.
- [ ] P08.9 If those tests expose a baseline defect, design the smallest correction
  with compatibility tests before changing stored identities. Preserve existing
  readable baseline versions and atomic writes.
- [ ] P08.10 Add wrap variants to the corpus, compare all changed findings, and
  run focused rule, mapping, baseline, and package checks.

Acceptance: wrapping alone does not alter supported phrase detection, and spans
remain accurate without joining unrelated or masked content.

## P09 — Narrow hedge stacking

Targets: `src/proseprobe/rules/grammar.py`,
`tests/test_rules/test_grammar.py`, quality-corpus cases.

- [ ] P09.1 Add a failing negative for `The cache may expire, or the server might
  restart.` Assert that separate alternatives do not receive a high-confidence
  stacking diagnostic.
- [ ] P09.2 Retain a positive for `may possibly`, with exact span, high confidence,
  and the existing modal suggestion.
- [ ] P09.3 Add coordinated independent clauses, distinct sentences, and a
  genuinely redundant stack, including wrapped variants.
- [ ] P09.4 Add conservative clause guards for recognized separate propositions.
  Lower confidence where the sentence-wide count remains ambiguous rather than
  claiming certainty from the count alone.
- [ ] P09.5 Preserve phrase-level metadiscourse checks and prevent duplicate
  diagnostics inside a confirmed redundant-modal span.
- [ ] P09.6 Verify profile confidence filters and add corpus positives and
  negatives for the distinctions above.

Acceptance: redundant hedges remain detectable, while independently qualified
claims no longer receive unjustified high-confidence stacking alerts.

## P10 — Require evidence to qualify the matched claim

Targets: evidence helpers and V015/V016 in `src/proseprobe/rules/vocab.py`,
`tests/test_rules/test_vocab.py`, quality-corpus cases.

### P10A — Comparatives and superlatives

- [ ] P10A.1 Add a failing positive for `Release 4 is the fastest parser.` An
  unrelated version number must not exempt the superlative.
- [ ] P10A.2 Add negatives for a directly stated comparison with metric and scope,
  such as `In this benchmark, A was fastest among the three tested parsers.`
- [ ] P10A.3 Test unrelated dates, ports, people, links, and numbers in adjacent
  sentences, including a different subject in the same paragraph.
- [ ] P10A.4 Replace presence-only evidence checks with narrow claim-local
  qualification. For uncertain association, retain a lower-confidence review
  prompt instead of treating the claim as proven.
- [ ] P10A.5 Keep V015 experimental until P16 supplies sufficient independent
  precision evidence. Preserve current profile membership unless deliberately
  changed after review.

### P10B — Reliability assertions

- [ ] P10B.1 Add a failing positive for `The parser was tested over 100 runs.
  The parser never fails.` Finite testing must not exempt the universal assertion.
- [ ] P10B.2 Add a negative for the bounded observation `The parser never failed
  during those 100 runs.` Assert that the bound qualifies the same observation.
- [ ] P10B.3 Replace any current test that exempts an unbounded assertion merely
  because a neighboring sentence reports testing. Retain its old input as a
  positive regression with a documented expectation change.
- [ ] P10B.4 Test tense changes, unrelated subjects, explicit tested conditions,
  and a sentence containing both a bounded observation and an unbounded claim.
- [ ] P10B.5 Narrow the bound association without attempting general factual
  verification. Preserve findings where the qualification is unresolved.
- [ ] P10B.6 Verify V016 profile behavior and source spans, then review all corpus
  mismatches introduced by the new evidence policy.

Acceptance: evidence of an observation cannot silently validate an unrelated
comparison or a universal claim. Detection still describes a prose issue rather
than asserting whether a claim is factually true.

## P11 — Remove redundant overlapping phrase alerts

Targets: `src/proseprobe/data/phrases.py`, V002/G009, corresponding rule tests,
metadata, output, and quality tests.

- [ ] P11.1 Add a failing test for `Let's dive into the API.` asserting one
  longest phrase match per rule, rather than both prefix matches.
- [ ] P11.2 Test repeated nonoverlapping occurrences so deduplication does not
  hide a second occurrence elsewhere in the sentence or document.
- [ ] P11.3 Resolve contained matches locally within each affected rule. Preserve
  accurate spans, ordering, and independently meaningful overlapping rules.
- [ ] P11.4 Inventory phrases owned by both V002 and G009. Define which rule
  owns each identical diagnosis and record the reason.
- [ ] P11.5 Add tests for selecting V002 alone, G009 alone, and both rules before
  changing shared-pattern ownership. Preserve useful explicit-selection behavior.
- [ ] P11.6 If ownership would break that contract, specify grouping that retains
  each rule ID and machine-output meaning before changing presentation. Do not
  add an undocumented JSON/SARIF shape or suppress findings globally.
- [ ] P11.7 Verify inline suppression, baseline matching, metadata descriptions,
  and corpus expectations for the chosen ownership or grouping behavior.

Acceptance: one phrase does not produce repeated copies of the same diagnosis;
distinct diagnoses and explicit rule selections remain understandable.

## P12 — Preserve technical meanings and exact quotations

Targets: V001/V002/V004, vocabulary data, Python/Markdown context helpers,
`tests/test_rules/test_vocab.py`, technical-review corpus, agent guidance.

- [ ] P12.1 Inventory all 12 existing false positives and classify their causes:
  technical sense, literal quotation, or evidence association.
- [ ] P12.2 Add paired tests for technical constructions and generic uses of
  `key`, `significant`, `fundamental`, and `implement` inflections. Include cases
  where a valid technical term shares a sentence with a separate prose violation.
- [ ] P12.3 Add narrowly scoped context exceptions for reviewed constructions,
  covering case, inflection, wrapping, and Markdown/Python parity.
- [ ] P12.4 Preserve the existing `robust regression` exception and reject
  unrelated same-line exemptions. Do not silently change the documented
  whole-line `allowed_phrases` contract while adding built-in span checks.
- [ ] P12.5 Deliberately revise tests that currently require warnings on recognized
  technical uses. Keep generic administrative uses as positives and document
  the changed policy rather than deleting inconvenient tests.
- [ ] P12.6 Test that suggestions fit the source form and meaning. Omit a
  suggestion when the rule cannot provide a valid replacement.
- [ ] P12.7 Retain linting of ordinary blockquotes: a draft callout and an exact
  quotation can use the same Markdown syntax.
- [ ] P12.8 Verify the existing narrow suppression mechanism for an explicitly
  preserved quotation. Add only missing tests; do not infer quote intent from
  typography alone or add blanket quotation exemptions.
- [ ] P12.9 Document residual raw-detector quotation findings and caller handling.
  Keep raw-corpus false positives visible; report policy-handled cases separately.
- [ ] P12.10 Add journalism contrasts for a named source and a quantified trend.
  Inspect V005/V008 association with following context; retain low confidence
  when support cannot be safely associated with the matched claim.
- [ ] P12.11 Compare precision and retained generic positives on development
  samples, then evaluate once on reserved holdout material through P16.

Acceptance: technical exceptions preserve the intended meaning without masking
other findings. Exact quotation handling is explicit, and unresolved detector
limitations remain visible in evaluation.

## P13 — Add repeated adjacent function-word detection

Targets: grammar rules, registry, profiles, rule tests, metadata/docs, corpus.

- [ ] P13.1 Define a small reviewed vocabulary of likely accidental function-word
  repetitions and choose a new unused rule ID from canonical metadata.
- [ ] P13.2 Add a failing positive for `Read the the configuration.` Assert the
  repetition span and a conservative suggestion.
- [ ] P13.3 Add a positive for `with with`, including a wrapped occurrence and
  Python docstring/comment cases.
- [ ] P13.4 Add negatives for `had had`, `that that`, punctuation-separated words,
  proper names, inline code, fenced examples, and separate prose blocks.
- [ ] P13.4a Define which word span a repeated run reports. Test case variation
  and a three-word run, requiring one finding for its duplicated tail.
- [ ] P13.5 Detect only the declared vocabulary in source-mapped prose. Do not
  generalize to arbitrary repeated words or infer intentional quoted examples.
- [ ] P13.6 Verify explicitly preserved quotations through the established
  suppression policy, with raw findings reported honestly where intent is absent.
- [ ] P13.7 Register the rule as experimental first and specify initial severity
  and confidence. Test normal default scans as well as profiles: experimental
  classification alone does not exclude a rule from legacy all-category scans.
- [ ] P13.8 Complete the new-rule checklist in P17, then measure independent
  precision before proposing profile promotion.

Acceptance: the rule catches the stated typing errors and leaves legitimate
repetition and masked content alone, without making authorship claims.

## P14 — Add stale docstring parameter declarations

Targets: `src/proseprobe/parsers/python.py`, `src/proseprobe/rules/code.py`,
parser/code tests, registry, metadata/docs, corpus.

- [ ] P14.1 Add a failing test for a function accepting `url` and `timeout` whose
  docstring declares `:param retries:`. Assert a span on the stale declaration.
- [ ] P14.2 Characterize parser parameter metadata for positional-only,
  positional, keyword-only, variadic, and bound-method parameters.
- [ ] P14.3 Preserve parameter kinds and `**kwargs` presence in the smallest
  metadata extension needed by the rule. Test a normal function parameter named
  `self` or `cls` separately from actual bound-method conventions. Leave C007's
  existing normalized parameter tuple unchanged.
- [ ] P14.4 Add positives for a renamed parameter and a misspelled declared name;
  add negatives for valid declarations and absent documentation.
- [ ] P14.5 Start with explicit Sphinx `:param` fields. Test typed forms,
  indentation, multiline descriptions, and source mapping; reject prose that
  merely mentions the same text without a supported field declaration.
- [ ] P14.5a Mask recognized docstring examples before extracting declarations.
  Test literal field examples, escaped content, and concatenated source strings
  so diagnostic coordinates come from source-aligned documentation.
- [ ] P14.6 Skip module/class documentation and unsupported runtime signatures.
  With delegated `**kwargs`, retain conservative behavior instead of declaring
  every extra documented keyword stale.
- [ ] P14.7 Compare declared names against the owning function's signature.
  Keep this distinct from C007's opening-sentence/signature repetition check.
- [ ] P14.8 Test nested functions, methods, async functions, and Unicode names.
  Assert that a declaration is paired with the correct owner.
- [ ] P14.9 Add the rule as experimental with explicit defaults and complete P17.
- [ ] P14.10 Defer Google/NumPy sections until each format has tested boundaries
  and independent samples. Treat each added format as a separate later slice.

Acceptance: explicit stale declarations are actionable; missing documentation,
delegated keywords, and unsupported formats do not become new violations.

## P15 — Add optional same-document fragment validation

Targets: Markdown parser/markup rules, configuration, registry, metadata/docs,
parser/configuration/markup tests.

- [ ] P15.1 Choose and document one supported renderer's anchor policy using its
  primary specification. Record heading slug rules, duplicate headings, explicit
  anchors, URL encoding, and supported Markdown extensions.
- [ ] P15.2 Keep fragment validation disabled by default through an explicit,
  validated renderer/anchor setting. Add a failing default-off test before
  registering the rule; experimental classification alone is insufficient.
- [ ] P15.3 Add a failing enabled-rule positive for `[installation](#install)`
  without a matching heading or supported explicit anchor.
- [ ] P15.4 Add negatives for a matching heading, supported explicit anchor,
  duplicate-heading suffix, and encoded destination under the declared policy.
- [ ] P15.4a Establish direct-link destination extraction with titles and
  delimiters before comparing fragments. Test explicit HTML anchors in non-code
  source separately from heading extraction; do not infer them from heading text.
- [ ] P15.5 Test that external URLs and cross-file fragments are outside this
  rule's scope. Skip empty fragments and images. Do not fetch pages or add
  cross-repository link checking.
- [ ] P15.6 Handle reference-style links at their definition destination span.
  Test several uses of one broken definition and require one finding there.
- [ ] P15.7 Preserve direct-link destination spans and mask code examples. Mark
  generated Liquid/MDX anchors as unsupported where the policy cannot resolve them.
- [ ] P15.8 Test invalid configuration, explicit enablement, renderer configuration
  in metadata, profile interaction, and disabled-default behavior.
- [ ] P15.9 Complete P17 and evaluate against documents using the chosen renderer.
  Record unsupported dialects as such rather than as false positives.
- [ ] P15.9a Add an explicitly enabled renderer policy to the all-rule corpus
  track and its provenance. Test corpus coverage for the optional rule without
  changing production defaults or pretending disabled rules emitted findings.

Acceptance: opted-in checks resolve only the declared anchor policy, produce
accurate destination spans, and leave default scans unchanged.

## P16 — Evaluate usefulness and calibrate confidence

Targets: evaluator reports, held-out corpus, annotation guidance, CI measurement.

- [ ] P16.1 Add deterministic metric tests for precision, eligible-issue recall,
  false warnings per 1,000 prose words, and source-span accuracy.
- [ ] P16.2 Define the prose-word denominator from eligible extracted prose.
  Exclude masked code and report separate Markdown, docstring, and comment totals.
- [ ] P16.3 Add confidence intervals and sample sizes for per-rule precision.
  Test empty denominators and small samples; do not report certainty from one case.
- [ ] P16.3a Account for findings grouped within source repositories. Use
  source-cluster-aware uncertainty where sufficient sources support it; otherwise
  state that simple intervals describe only the reviewed sample.
- [ ] P16.4 Report both totals across findings and averages across supported rules,
  with rare rules and unsupported/unreviewed cases visible.
- [ ] P16.4a Report source-level variation where sample sizes permit. Do not treat
  many sentences from one repository as independent evidence from many projects.
- [ ] P16.5 Review default warning/error behavior separately from all-rule and
  informational results. Keep high-confidence failures visible even when the
  aggregate score improves.
- [ ] P16.6 Assess whether a warning leads to a useful, meaning-preserving edit.
  Use independent human judgments on held-out technical samples and retain
  disagreement records.
- [ ] P16.7 Evaluate JFLEG/ASSET before-and-after differences as supplementary
  evidence. Inspect new warnings on human corrections and retained valid warnings.
- [ ] P16.8 Choose confidence/default/profile changes using development evidence,
  then evaluate the chosen policy once on the reserved holdout set.
- [ ] P16.9 Treat later tuning prompted by holdout errors as development work and
  reserve fresh independent sources before claiming another generalization result.
- [ ] P16.10 Keep corpus metrics report-only until reviewed coverage supports a
  justified gate. Then specify a no-new-regressions check and any numeric
  thresholds with documented denominators and small-sample treatment.
- [ ] P16.10a Set quality targets from reviewed development data before consulting
  holdout results. Test the gate on controlled regressions and retain known
  mismatches explicitly instead of adopting a blanket pass threshold.
- [ ] P16.11 Publish results with commit, policy, corpus version, sample sizes,
  uncertainty, known limitations, and the disposition of every assessed issue.

Acceptance: a measured improvement means more useful findings or fewer incorrect
ones without hiding eligible misses, changing the population, or losing meaning.

## P17 — Package completion and integration gates

Apply this checklist to each behavior slice. Run the final integration checklist
after all selected packages are complete. A deferred optional feature needs a
written decision and its unmet prerequisite; it must not appear as completed.

### New-rule checklist

- [ ] P17A.1 Allocate an unused ID and declare class metadata, supported file
  types, content scope, severity, confidence, and any real configuration field.
- [ ] P17A.2 Register the rule and test its selection, ignore handling, severity
  overrides, and experimental/profile classification.
- [ ] P17A.3 Update metadata, profile, and rule-count assertions to reflect the
  declared rule catalog. Preserve registry consistency checks.
- [ ] P17A.4 Add the handwritten rule-reference section and required executable
  positive/negative examples; generate canonical inventory and category counts
  with `make rule-docs`.
- [ ] P17A.5 Add at least one genuine positive and one explicit negative corpus
  case. Add more independent coverage before using it to justify promotion.
- [ ] P17A.6 Verify JSON Lines/SARIF span behavior, deterministic ordering, inline
  suppression, and baseline interaction where the rule introduces a new case.

### Checks for each slice

- [ ] P17B.1 Run the smallest relevant test command until the new regression is
  green, then run related integration tests.
- [ ] P17B.2 Review every changed corpus finding and expectation. Preserve false
  positives as mismatches until the behavior or annotation has a justified change.
- [ ] P17B.3 Run `make rule-docs-check`, `make check`, `make dogfood`, and
  `make rule-quality`. Explain quality deltas; the current evaluator's successful
  exit does not mean it has no false positives.
- [ ] P17B.4 Run the ProseProbe JSON Lines scan on edited prose with the project's
  existing policy and baseline. Review technical terms and exact examples before
  rewriting them.
- [ ] P17B.5 Update `CHANGELOG.md` and affected specification/configuration docs
  for user-visible changes. Keep generated blocks generated.

### Final integration

- [ ] P17C.1 Run `make check`, `make dogfood`, `make rule-quality`, and
  `make nfr-check` on the final implementation commit.
- [ ] P17C.2 Require the Python 3.11, 3.12, and 3.13 CI matrix for that commit.
  Report any unavailable remote check explicitly.
- [ ] P17C.3 Verify representative filesystem and stdin scans in text, JSON,
  JSON Lines, and SARIF, including clean inputs and operational errors.
- [ ] P17C.4 Verify `watch` and baseline maintenance after shared-policy changes.
  Preserve legacy readable baselines, deterministic identity, and atomic writes.
- [ ] P17C.5 Compare the full-scan benchmark and memory/startup probes with P00/P07
  evidence. Investigate material regressions before closing the plan.
- [ ] P17C.6 Review each package against its acceptance criteria and record
  completed, deferred, or unresolved status with supporting test and corpus results.
- [ ] P17C.7 Keep publication separate. Follow `RELEASE_BLOCKERS.md` if a release
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
