# ProseProbe outstanding work

Updated: 2026-10-13. The user requested completion without further interaction.
Use the existing evaluators and CI. Preserve actual human judgments, identify
agent judgments separately, and keep unsupported independent claims deferred.
Earlier engineering work and execution records remain in Git history.

## Working rules

- For behavior changes, start with a failing test, make the smallest correction,
  then run related tests and repository gates. Data-only work uses existing
  schema, source-binding and coverage validators.
- Commit each completed stage with a one-line message; remove completed actions
  from this plan and retain results in the session execution record.
- Preserve frozen original/extension sources, split assignments, exact source
  bytes, contracts, baseline, native pair groups and all raw mismatches.
- Select development records from metadata before opening bytes. Never use a
  whole-manifest loader that reads reserved holdout sources before filtering.
- Use the [review protocol](quality/external/review-protocol.md). Agent reviews
  cannot satisfy human independence or meaning-preservation requirements.
- Keep the effective default policy and experimental status unchanged unless
  sufficient development evidence justifies a documented proposal.
- Include a direct reading link if any future review request is made. The
  existing interactive length limit remains 80 lines of 80 characters.

## Unattended execution

Session: `quality/reviews/2026-10-13-autonomous/`.
R001–R003 retain three human clean scopes for G038/V015/V016, with unknown prior
exposure and unverified independence. R004 supplied a clarification request,
not a judgment; its human scope remains unreviewed. The agent pilot covers five
licensed development Markdown sources in three source groups. It is a declared
convenience sample and does not establish representative population quality.

- [ ] A04a Run source-bound all-rules and unchanged production reports for each
  human reading and each agent review, using the existing report path.
- [ ] A04b Summarize raw counts, policy exclusions, eligible reviewed words,
  source-group support and unavailable metrics. Separate human and agent rows.
- [ ] A04c Record a development decision for the three claim rules. Keep other
  rule assessments unavailable where no eligible labels were collected.
- [ ] A07 Freeze the candidate, push a review branch and create a draft PR to
  trigger Ubuntu Python 3.11–3.13 CI. Record exact-SHA evidence for P33.9.
- [ ] A08 Publish an execution record, prune completed actions and leave only
  conditional work requiring genuinely unavailable evidence or release intent.

## Deferred independent evidence

These requirements remain valid, but they cannot be fulfilled by fabricating
human reviewers or treating native edits or agent judgments as writing truth.
No further user questions are needed for the unattended development track.

- [ ] P32B.1/.5/.6/.7/.8a/.8b/.9/.10/.11/.12 Obtain eligible independent human
  reviewers, exhaustive blind labels, double annotation, disagreements,
  adjudication and frozen coverage; then separately review triggered findings
  and sparse positives. Preserve identity, exposure and access provenance.
- [ ] P31.13 and P32C.4/.6a/.6b/.7 After frozen initial labels, obtain the four
  human suggestion judgments and native-pair correspondence/outcomes. Keep
  JFLEG/ASSET alternatives together; warning changes are mechanical evidence.
- [ ] P32D.1/.5/.6a/.6b/.6c/.7, P27.13, P29.12 and P15.9 Complete independent
  per-rule/profile/format/context development evidence before calibration or
  promotion. G039, C004, C009, C010 and M011 need their own supported labels.
- [ ] P30.18 Preserve and bind native Markdown source paths, pinned complete
  target inventories and referenced target bytes/verified absence before M012
  independent review. A missing local cached target cannot establish absence.
- [ ] P32D.8/.9a/.9b/.10/.11 Predeclare independent targets and support, freeze
  the candidate and labels, then evaluate reserved holdout once. If results
  prompt tuning, reserve fresh source groups before a further independent claim.

## Conditional acquisition and release

- [ ] P32C.10a/.10b/.10c/.10d Acquire the excluded README revision package only
  after explicit reuse terms permit it; add failing adapter tests if necessary,
  verify revisions and freeze new groups separately. Article licensing and
  native commit categories cannot establish corpus reuse or clarity truth.
- [ ] P33.14 When a release is explicitly requested, complete every gate in
  [RELEASE_BLOCKERS.md](RELEASE_BLOCKERS.md) for that exact release candidate,
  including package, legal/publication identity and trusted-publishing checks.
