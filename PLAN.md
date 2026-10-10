# ProseProbe outstanding work

Updated: 2026-10-10. Independent human evaluation remains deferred by user
request. Resume that work only when the user requests it and reviewers are
available. Remote CI and conditional release checks remain separate gates.
Previous tasks and execution records are preserved in Git history at `8547182`.

## Working rules

- For behavior changes, reproduce the defect with a failing test, make the
  smallest correction, then run related tests and repository gates. Reuse
  existing contract tests when they already cover the behavior.
- Commit each completed change with a one-line message and update this plan.
- Preserve the [original sources](quality/sources.json),
  [original split freeze](quality/external/split-freeze.json),
  [extension sources](quality/external/extension-sources.json), and
  [extension freeze](quality/external/extension-freeze.json). Keep related
  sources and revision pairs in one split; protect holdout material from tuning.
- Keep raw false positives, misses and unresolved judgments visible. Preserve
  source bytes, spans, provenance and the existing baseline.
- Retain source licenses and attribution under the
  [external corpus guide](quality/external/README.md). LOCNESS stays excluded;
  the README revision dataset stays excluded until reuse terms are verified.

## Remote verification

- [ ] P33.9 Obtain passing Ubuntu Python 3.11–3.13 CI results for the exact
  candidate commit. Record its SHA and result links; local runs do not satisfy
  this gate. This also covers the earlier P17C.2 requirement.

## Independent annotation — deferred

Prerequisites: user resumes evaluation and eligible human reviewers are
available under the recorded source terms. Follow the existing
[blind review protocol](quality/external/review-protocol.md) and
[source-bound annotation guide](quality/README.md).

- [ ] P32B.1 Assign eligible human reviewers and record their identifiers and
  permitted source access.
- [ ] P32B.5 Distribute blind originals, declared contracts and necessary source
  context. Withhold predictions and native revisions during the initial pass.
- [ ] P32B.6 Collect exhaustive issue and coverage annotations for eligible random
  prose, including clean regions and issues the detector may miss.
- [ ] P32B.7 Obtain an independent second annotation of the
  [preselected subset](quality/external/double-annotation-selection.json).
  Retain both original judgments.
- [ ] P32B.8a Report agreement and disagreement counts with their denominators.
- [ ] P32B.8b Adjudicate each disagreement with reviewer identity and rationale;
  retain genuinely unresolved cases as context-dependent.
- [ ] P32B.9 Freeze accepted initial labels and reviewed coverage before generating
  detector predictions.
- [ ] P32B.10 Conduct a separately identified triggered-finding review. Keep its
  additional labels separate from blind labels and exhaustive recall coverage.
- [ ] P32B.11 Obtain independently authored positives and near misses for sparse
  rules; identify and score these separately from natural text.
- [ ] P32B.12 Validate accepted version 3 artifacts for source binding, spans,
  reviewer provenance and explicit coverage. Record reviewed quantities and gaps.

Sentence sources cannot establish document-structure recall. Module-dependent
Python contracts require complete, bound context; function-only CodeSearchNet
samples cannot supply it. Unsupported renderers, templates and unresolved
contexts remain unsupported. CommonMark conformance supplies syntax evidence.

## Suggestion and revision review — deferred

Prerequisite: initial blind annotations are frozen. Use explicit reviewed
correspondence and the existing usefulness/paired-report schemas.

- [ ] P32C.4 Provide all four JFLEG and all ten ASSET references under their
  original pair identities and recorded access terms. Keep alternatives in the
  same source group.
- [ ] P31.13 Collect four separate judgments for each relevant suggestion:
  finding helpfulness, sentence fit, meaning preservation and reviewer acceptance.
  Preserve missing, unresolved and context-dependent answers.
- [ ] P32C.6a Record exact original/revision identities and explicit diagnostic
  correspondence for each evaluated pair.
- [ ] P32C.6b Collect human judgments of revision usefulness and preserved meaning,
  including retained valid warnings and newly incorrect warnings.
- [ ] P32C.7 Report warning transitions beside human outcomes and actual
  denominators. Native edit categories, fewer warnings and passing rescans do
  not establish semantic quality.

## Development evaluation and calibration — deferred

Prerequisite: accepted independent development labels and supported contexts.
Holdout prose and predictions stay hidden from implementers during development.

- [ ] P32D.1 Generate source-bound reports for all-rules and unchanged default
  production policy. Retain raw counts, misses, full-span accuracy, reviewed
  words, exclusions, coverage and usefulness judgments.
- [ ] P32D.5 Publish per-rule/profile/format/context/source-group results with
  denominators and uncertainty. Use the existing whole-group method; report
  unavailable intervals and reasons when support is inadequate.
- [ ] P32D.6a Review technical terminology and exact quotations against natural
  development labels, preserving retained generic positives.
- [ ] P32D.6b Assess G039 repeated-word precision on independently reviewed samples.
- [ ] P32D.6c Assess C004 executable placeholders and C009 parameter-kind checks
  in supported Python contexts.
- [ ] P27.13 Assess G038 comparison claims and their evidence on untouched
  development examples.
- [ ] P29.12 Assess C010 precision and usefulness under its current narrow return
  contract; record unsupported types and disagreements.
- [ ] P15.9 Assess M011 against documents using its declared renderer; retain
  unsupported dialects explicitly.
- [ ] P30.18 Obtain independent Markdown precision review for M012 only after
  native source paths and referenced target context are preserved and bound.
  Until that prerequisite is met, independent M012 scoring remains unavailable.
- [ ] P32D.7 Choose any proposed threshold, confidence, severity, default or
  profile change from development evidence and record the rationale. Promotion
  is optional; insufficient evidence leaves rules experimental.

## Reserved holdout evaluation — deferred

Prerequisites: development review and candidate decisions are frozen. Follow the
existing protocol's source-group support and uncertainty requirements.

- [ ] P32D.8 Predeclare quality targets, supported populations, minimum sample
  and group support, and unavailable-metric handling before opening holdout.
  Keep these targets separate from the curated regression gate.
- [ ] P32D.9a Freeze the candidate implementation and effective policy.
- [ ] P32D.9b Evaluate once on the reserved holdout through the same validated
  source-bound report path. Preserve raw false positives and misses.
- [ ] P32D.10 Obtain human holdout usefulness judgments under frozen contracts;
  publish agreement, unresolved cases and source-correlated uncertainty.
- [ ] P32D.11 If holdout results prompt tuning, reclassify inspected material as
  development evidence and reserve fresh source groups before another claim.

## Conditional follow-ups

### README revision dataset

Pursue only if access and primary reuse terms permit the intended evaluation.

- [ ] P32C.10a Verify access, reuse terms, attribution and source provenance before
  accepting material from the currently excluded package.
- [ ] P32C.10b Add failing offline adapter tests for any newly needed behavior;
  reuse existing revision-pair contracts where applicable.
- [ ] P32C.10c Manually verify sampled revisions. Keep commit-keyword labels
  distinct from independently reviewed clarity judgments.
- [ ] P32C.10d Freeze accepted source/pair groups and split assignments separately
  from existing sources before detector-based evaluation.

### Release

- [ ] P33.14 When a release is explicitly requested, complete every gate in
  [RELEASE_BLOCKERS.md](RELEASE_BLOCKERS.md) for that exact release commit,
  including package checks, legal/publication identity and trusted publishing.
