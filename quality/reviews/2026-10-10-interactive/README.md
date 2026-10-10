# Interactive development review

Session date: 2026-10-10. The user resumed human review and requested readings
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
The full original lives at `originals/0000.md` beneath that root. Its provenance,
license URL and attribution remain in the selection and reading records.
The source material is available under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The original pilot and extension manifests are unchanged.

Reviewer identity and previous prediction exposure have been requested.
No human answer, accepted label or reviewed coverage has been recorded yet.
One user supplies one review; a second independent reviewer remains unassigned.
Human replies will be retained literally and separately from proposed mappings.
Any inferred interpretation or issue coordinates require human confirmation.

A clean judgment covers only the displayed region and declared rules. Other
regions and rules remain unreviewed. Detector output and native revisions stay
withheld until accepted initial labels for the declared batch are frozen.
This session establishes no population effectiveness or semantic-usefulness claim.

Validation used 28 failing-first synthetic presenter cases and 158 related
presenter/corpus/annotation tests. Holdout rejection precedes any source byte
read. Oversized readings fail without truncation. No natural detector scan was
used to validate the formatter or the initially unreviewed packet.
