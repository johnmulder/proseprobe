# ProseProbe outstanding work

Updated: 2026-10-13. The unattended development track is complete; results,
limits and exact candidate CI evidence are in the
[execution record](quality/reviews/2026-10-13-autonomous/EXECUTION.md).
Only conditional work remains. No further interactive review is requested.

## Working rules

- For behavior changes, start with a failing test, make the smallest correction,
  then run related tests and repository gates. Data-only work uses existing
  schema, source-binding and coverage validators.
- Commit each completed stage with a one-line message, update this document and
  keep completed actions in execution records rather than this checklist.
- Preserve original/extension source bytes, split freezes, contracts, baseline,
  pair groups, reviewer provenance and every raw mismatch.
- Select development records from metadata before reading bytes. Never use a
  whole-manifest loader that opens reserved holdout sources before filtering.
- Follow the [review protocol](quality/external/review-protocol.md). Agent
  judgments remain development evidence; they cannot replace independent human
  annotation, agreement or semantic-usefulness evidence.
- Keep defaults and experimental status unchanged without sufficient evidence.
- If a future review is requested, include its direct reading link and limit it
  to 80 lines of 80 characters, including instructions and questions.

## Independent human annotation — deferred

Prerequisites: eligible actual human reviewers and permitted source access.
The three previous human scopes remain limited; prior exposure is unknown and
independence unverified. Agent annotations are separately identified.

- [ ] P32B.1 Record eligible reviewer identifiers, exposure and permitted access.
- [ ] P32B.5 Provide fresh blind originals, contracts and supported context.
- [ ] P32B.6 Collect exhaustive issue spans and reviewed coverage, including
  genuine clean regions and detector misses.
- [ ] P32B.7 Obtain a second independent human annotation of the existing
  metadata-selected subset; retain both original judgments.
- [ ] P32B.8a Report agreement/disagreement counts and actual denominators.
- [ ] P32B.8b Adjudicate disagreements with identity and rationale; preserve
  unresolved cases as context-dependent.
- [ ] P32B.9 Freeze accepted independent labels and coverage before predictions.
- [ ] P32B.10 Review triggered findings separately from exhaustive blind labels.
- [ ] P32B.11 Obtain independent sparse positives and near misses; identify their
  population separately from natural text.
- [ ] P32B.12 Validate accepted version 3 bindings, spans, provenance and coverage;
  report reviewed quantities and gaps.

## Suggestion and revision usefulness — deferred

Prerequisite: accepted initial independent labels are frozen.

- [ ] P32C.4 Provide all four JFLEG and ten ASSET references within their original
  source/pair groups and access terms.
- [ ] P31.13 Collect separate human judgments for finding helpfulness, sentence
  fit, meaning preservation and acceptance; preserve missing/contextual answers.
- [ ] P32C.6a Bind exact original/reference identities and reviewed diagnostic
  correspondence for each evaluated pair.
- [ ] P32C.6b Obtain human revision-usefulness and meaning-preservation judgments,
  including retained valid warnings and newly incorrect warnings.
- [ ] P32C.7 Report mechanical warning transitions beside human outcomes and
  actual denominators; fewer warnings do not establish semantic quality.

## Independent development calibration — deferred

Prerequisites: supported contexts and accepted independent development labels.

- [ ] P32D.1 Generate all-rules and unchanged production reports with raw counts,
  misses, full-span accuracy, exclusions, coverage and usefulness judgments.
- [ ] P32D.5 Publish per-rule/profile/format/context/source-group results with
  denominators and declared whole-group uncertainty; retain unavailable metrics.
- [ ] P32D.6a Assess technical terminology and exact quotations, preserving
  genuine generic positives.
- [ ] P32D.6b Assess G039 repeated-word precision on independently reviewed prose.
- [ ] P32D.6c Assess C004 executable placeholders and C009 parameter-kind checks
  in supported Python contexts.
- [ ] P27.13 Assess G038 on untouched independent development examples.
- [ ] P29.12 Assess C010 precision/usefulness under its narrow return contract;
  retain unsupported types and disagreements.
- [ ] P15.9 Assess M011 under each document's declared renderer; retain unsupported
  dialects explicitly.
- [ ] P30.18 Before M012 independent review, bind native source paths, complete
  pinned target inventories and referenced target bytes or verified absence.
  Add failing tests for stale/incomplete bindings and path/symlink escapes before
  any binding implementation. A missing cached target cannot prove absence.
- [ ] P32D.7 Propose thresholds, confidence, severity, defaults or promotion only
  from sufficient development evidence; promotion remains optional.

## Reserved holdout — deferred

Prerequisites: independent development review and candidate decisions frozen.
Reserved holdout material remains unopened.

- [ ] P32D.8 Predeclare targets, supported populations, minimum sample/group
  support and unavailable-metric handling before opening holdout.
- [ ] P32D.9a Freeze the independent candidate implementation and effective policy.
- [ ] P32D.9b Evaluate once using the same validated source-bound report path;
  preserve raw false positives and misses.
- [ ] P32D.10 Obtain human holdout usefulness judgments; publish agreement,
  unresolved cases and source-correlated uncertainty.
- [ ] P32D.11 If inspected holdout prompts tuning, reclassify it as development
  and reserve fresh source groups before any further independent claim.

## Conditional acquisition and release

The 2026-10-13 primary-source check still found unresolved reuse terms for the
README revision package. No package or adapter was acquired; LOCNESS remains
excluded. Current evidence is in the execution record and `dataset-terms.json`.

- [ ] P32C.10a Obtain explicit permitted reuse terms, attribution and provenance
  before accepting the excluded README package.
- [ ] P32C.10b Add failing adapter tests for any newly needed behavior, then reuse
  existing revision-pair contracts when possible.
- [ ] P32C.10c Verify sampled revisions; keep native commit/edit labels separate
  from independently reviewed clarity judgments.
- [ ] P32C.10d Freeze accepted new sources/pairs/groups separately from the
  existing source and split freezes before detector-based evaluation.
- [ ] P33.14 When a release is explicitly requested, complete every gate in
  [RELEASE_BLOCKERS.md](RELEASE_BLOCKERS.md) for that exact release candidate,
  including package, legal/publication identity and trusted publishing.
