# External evaluation pilot

The pilot contains 300 source units awaiting independent human annotation.
`quality/sources.json` records provenance; `split-freeze.json` records the frozen
source assignments. Source text, downloaded archives, native references, and
blind review packets live in the ignored `downloads/evaluation/` cache. These
materials are excluded from the published package. No detector predictions were
used to select this pilot, and no pilot effectiveness score exists yet.

## Validate and prepare review

From the project root:

```sh
rtk proxy .venv/bin/python -m benchmarks.corpora quality/sources.json --cache downloads/evaluation
rtk proxy .venv/bin/python -m benchmarks.corpora quality/sources.json --cache downloads/evaluation --export-blind blind/originals.jsonl
rtk proxy .venv/bin/pytest tests/test_corpora.py -q
```

The validator checks native download and sample SHA256 checksums, cache paths,
provenance, native record shape, and split isolation. It prints counts without
printing prose. The blind packet contains originals and source identities;
human revisions and detector findings stay outside that packet. Changing a
cached sample after validation causes conversion to fail its checksum check.

The source manifest is an acquisition record, separate from issue annotations.
`review_status: unreviewed` applies to every source unit. `read_sample()` returns
the original prose and native references without running the linter or applying
native labels. Use a virtual `.py` filename for CodeSearchNet functions and a
virtual `.md` filename for the other formats when an annotated evaluation is
ready. Original source identities and native coordinate systems must accompany
any exported diagnostic or annotation.

The acquired cache also contains `blind/originals/` with exact `.md` or `.py`
originals, `blind/index.json` mapping their names to frozen source identities and
checksums, and `blind/annotations.unreviewed.json` for the evaluator's version 2
annotation schema. Its `expected`, `negative_cases`, `reviewed_rules`, and
`regions` lists are empty. Human reviewers populate reviewed rules or regions
and issue spans before evaluation; empty lists establish unknown coverage.
The evaluator's root for these files is `downloads/evaluation/blind/`.

## Sampling and provenance

| Source | Units | Split | Native labels and limits |
| --- | ---: | --- | --- |
| GitHub Docs | 50 complete Markdown files | Development | Published documentation; no writing-quality labels. Raw frontmatter and Liquid remain intact. |
| Rust book | 50 complete Markdown files | Holdout | Published documentation; no writing-quality labels. Includes mdBook syntax and raw code fences. |
| CodeSearchNet Python | 80 functions | Development | Function/docstring pairs; code-search judgments are excluded from prose scoring. |
| JFLEG | 40 originals, four references each | Holdout | Human grammar/fluency revisions; sentence-level evidence. |
| ASSET | 40 originals, ten references each | Holdout | Human simplifications; sentence-level clarity evidence. |
| W&I development | 40 M2 sentences | Development | Human corrections and automatically assigned ERRANT types. Native tokenization remains visible. |

Sampling ranks eligible file paths or sentence indices by SHA256 with the seed
`proseprobe-p06-2026-10-09`. Markdown files are complete documents. CodeSearchNet
is a bounded sample of its mirror's first 100 Python test rows; it covers two
repositories and is not a representative sample of the full dataset. Each
source repository stays in one split. Originals and all references stay
together. Unknown author relationships are grouped conservatively by dataset.
The acquired identity hash freezes all 300 units before heuristic tuning.

[GitHub Docs](https://github.com/github/docs) content carries CC BY 4.0;
[the Rust book](https://github.com/rust-lang/book) carries MIT or Apache-2.0.
Pinned license URLs and attribution appear in every sample record.

The [CodeSearchNet primary archive](https://github.com/github/CodeSearchNet)
returned HTTP 403 on 2026-10-09. The bounded
[CodeSearchNet mirror](https://huggingface.co/datasets/code-search-net/code_search_net)
snapshot and original GitHub permalinks are recorded separately. Upstream
Apache Airflow and you-get licenses were verified at the referenced commits.
All 80 originals were compared with 41 pinned raw source modules: 48 match
exactly and 32 differ only in boundary whitespace. The native function text
was retained without dedenting. Every function parses independently; surrounding
module context is cached for source verification and remains separate from the
function input used for a scan.

[JFLEG](https://github.com/keisks/jfleg) carries CC BY-NC-SA 4.0 and
[ASSET](https://github.com/facebookresearch/asset/blob/main/LICENSE) carries
CC BY-NC 4.0. Keep their non-commercial and attribution restrictions with the
cached material and any permitted derivative release.

The [BEA archive](https://www.cl.cam.ac.uk/research/nl/bea2019st/) checksum is
recorded. Its W&I license permits non-commercial research and education and
restricts use within sold or licensed products and services. This local pilot
uses only W&I A/B/C development sentences. LOCNESS sentences are excluded
because its license restricts third-party distribution. Native token-to-character
spans refer to the tokenized source, not a reconstructed original essay.

The [README simplification study](https://arxiv.org/html/2308.09940v1) links an
accessible Zenodo record advertising a 12.2 MB replication package. Its generic
`other-open` license entry and absence of a LICENSE file in the tagged upstream
tree leave corpus reuse terms unresolved. That dataset was excluded. Commit
keywords would supply weak evidence requiring manual verification if terms
become clear.

## Independent annotation handoff

1. Assign eligible reviewers and confirm that their access fits each source's
   reuse terms. Keep restricted source material in its permitted local context.
2. Give reviewers only the blind originals packet, relevant source context,
   rule contracts, and the declared profile. Complete the initial random-prose
   review before showing native revisions or detector predictions.
3. For each source, record reviewed rules, eligible prose regions, supported
   issues found independently, and exhaustive coverage of those regions.
   Preserve the original source identity and character span. Sentence-level
   inputs cannot justify document-structure recall claims.
4. Classify an issue as useful, a false positive, or context-dependent; record
   the intended meaning and a brief reason. Mark unresolved cases explicitly.
   Fully reviewed regions with no issue are negative evidence. Unreviewed
   regions remain unknown.
5. Double-annotate a preselected subset, keep both judgments, and record the
   adjudication rationale and reviewer identity. Freeze this initial annotation
   before comparing detector output.
6. Review triggered findings in a separately identified pass. Preserve issues
   found during blind review even when the detector misses them. A review of
   warnings alone supports precision estimates, not recall.
7. Compare relevant warnings across JFLEG/ASSET variants after blind review.
   Judge usefulness and preserved meaning; fewer findings alone do not prove a
   better revision. Record unsupported native error types and tokenization
   artifacts separately.
8. Keep purpose-written rule examples, the legacy regression corpus, and this
   natural-text pilot distinguishable. Preserve existing false-positive
   evidence. Publish denominators and source-group uncertainty before making
   population-level claims.

Independent annotation, disagreements, supported-error mapping, and effectiveness
measurement remain pending. No human labels have been manufactured or inferred
from native revisions.
