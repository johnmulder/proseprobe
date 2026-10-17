# Interactive development review

Session started: 2026-10-10. Last activity: 2026-10-11. The user resumed human review and requested readings
of at most 80 lines of 80 characters, including instructions and questions.

`selection.json` declares the source-order seed, unchanged manifest identities,
initial rules and syntax-only exclusions. No detector output or issue judgment
selects a reading. The initial cohort is development GitHub Docs Markdown.
Sources without exposed prose are skipped without assigning human labels.

`R001.json` binds the exact full original bytes, displayed region, contract
snapshot, rendered text and literal source-coordinate map. Its JSON string
preserves the exact user-facing question. The cached `R001.txt` under the packet
root is a text view; source whitespace is kept outside formatting hooks.
Display continuations prefer word boundaries while
preserving every character and the original line endings in the map.

`index.json`, `contracts.json` and `annotations.unreviewed.json` mirror the fresh
version 3 packet under the ignored cache directory:
`downloads/evaluation/blind/interactive-2026-10-10-v1/`.
R001’s full original lives at `originals/0000.md` beneath that root. Its provenance,
license URL and attribution remain in the selection and reading records.
The source material is available under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The original pilot and extension manifests are unchanged.

`reviewer.json` identifies the actual session user with an opaque identifier.
A display name and previous prediction exposure are unknown; independence is
unverified. A second independent reviewer remains unassigned.

`R001.response.json` preserves the literal three-rule no-issue response, including
`No Issure`. Its normalization changes spelling only; no alternative meaning or
issue coordinates were inferred. `annotations.R001.reviewed.json` validates one
reviewed region, L19 C1 through L21 C330, for G038/V015/V016 only. Whole-file
review, other rules and purpose-written negatives remain undeclared.
`guidance.v1.md` captures the invented training examples provided before the
answer; its checksum is linked from the response.

`R002.json` binds the next seeded source reading, presented in 76 lines of at
most 80 characters. `R002.response.json` retains the user's literal clean answer
for all three rules. `R002/annotations.reviewed.json` validates only L16 C1
through L40 C260 for those rules. Its separate packet lives under
`downloads/evaluation/blind/interactive-2026-10-10-R002-v1/`; tracked index,
contracts and unchanged unreviewed template remain in `R002/`.

`R003.json` is submitted with 51 lines of at most 80 characters. It shows the
opening section of the next seeded source, an archived service-level agreement.
The displayed region is L14 C1 through L22 C594; later tables, exclusions and
redemption terms remained unreviewed in that reading. The question permits
missing-context judgments. Its separate packet lives under
`downloads/evaluation/blind/interactive-2026-10-10-R003-v1/`; tracked index,
contracts and unreviewed template are in `R003/`. `R003.response.json` retains
the user's literal no-issue answer for all three rules. The version 3 annotation
in `R003/annotations.reviewed.json` validates only the displayed region.

`R004.json` continues the same source with the complete table and exclusions
section, L23 C1 through L32 C389, presented in 72 lines of at most 80 characters.
Earlier context comes from R003. The remaining redemption section, L33–L38,
needs a later reading. The separate packet lives under
`downloads/evaluation/blind/interactive-2026-10-10-R004-v1/`; tracked index,
contracts and unreviewed template are in `R004/`. R004's response asked for
the region; `R004.clarification.json` preserves it without assigning a judgment.
On 2026-10-13 the user requested unattended work, so this request was retired.
The separate agent-assisted session is `quality/reviews/2026-10-13-autonomous/`.

Each packet uses the same unchanged contract snapshot. Earlier packet indexes
and initially unreviewed templates remain unchanged. No natural detector
predictions or native revisions have been shown.

A clean judgment covers only the displayed region and declared rules. Other
regions and rules remain unreviewed. Detector output and native revisions stay
withheld until accepted initial labels for the declared batch are frozen.
This session establishes no population effectiveness or semantic-usefulness claim.

Validation used 28 failing-first synthetic presenter cases and 158 related
presenter/corpus/annotation tests. Holdout rejection precedes any source byte
read. Oversized readings fail without truncation. No natural detector scan was
used to validate the formatter or the initially unreviewed packet.
