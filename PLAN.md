# ProseProbe outstanding work

Updated: 2026-10-14. The delegated agent review is complete; its results and
policy decision are in the [execution record](quality/reviews/2026-10-13-agent-resume/EXECUTION.md).
This checklist contains only outstanding work and its prerequisites.

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
- [ ] P32D.5a Declare the intended highlight unit for G038, V015, C004 and C009
  before assessing the four recorded endpoint differences. Keep exact-span
  accuracy separate from semantic event matches; do not refresh accepted labels.
- [ ] P32D.5b Bind required owning signatures, heading inventories and target
  context beside future bounded diagnostic readings. Start with failing row-map,
  context-selection and size-limit tests if packet generation needs a change.
- [ ] P32D.6a Assess technical terminology and exact quotations, preserving
  genuine generic positives.
- [ ] P32D.6b Assess G039 repeated-word precision on independently reviewed prose.
- [ ] P32D.6c Assess C004 executable placeholders and C009 parameter-kind checks
  in supported Python contexts.
- [ ] P32D.6d Clarify C004's intentional unsupported-operation boundary with
  accepted contract examples before labeling the unresolved Requests guard.
  Start with failing tests for any resulting behavior change.
- [ ] P27.13 Assess G038 on untouched independent development examples.
- [ ] P29.12 Assess C010 precision/usefulness under its narrow return contract;
  retain unsupported types and disagreements.
- [ ] P15.9 Assess M011 under each document's declared renderer; retain unsupported
  dialects explicitly.
- [ ] P30.18d.1 Select further permitted development originals from metadata;
  enumerate supported local Markdown references without predictions and retain
  eligibility skips. The first Requests context has zero eligible references.
- [ ] P30.18d.2 Bind complete pinned native inventories, required target bytes or
  verified absence and renderer context for each eligible new reading. Preserve
  original manifests/splits; freeze new artifacts separately.
- [ ] P30.18d.3 Obtain independent human M012 judgments and validate their source
  and target scopes before bound evaluation. Report actual denominators; empty
  reference populations cannot supply effectiveness estimates.
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

## Superseded human questions

The user delegated review to agents. R005 and its alias/exposure questions remain
human-unanswered; no response or identity was inferred. Its exact original
L18 C1–L38 C117 scope and three-rule contract are reused in separate agent
records. Seven previously detector-exposed originals remain excluded by ID and
hash. Further actual human review and independent claims retain their prerequisites.
