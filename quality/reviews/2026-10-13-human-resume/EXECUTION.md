# Interactive plan execution

Session date: 2026-10-13, America/Denver. The user resumed interactive review
and requested bounded readings, one-line commits and ongoing plan updates.

H01: Committed the fresh R005 batch and exact questions in `bc1badf` before
answers or predictions. The reading has 50 lines, at most 80 characters per
line, and a direct link. The separate five-line provenance question also fits
the combined limit. Both questions remain pending. Earlier judgments and their
frozen reports remain unchanged; R004 still has no human judgment.

P30.18a: Added an offline native-context preparation helper and 55 synthetic
tests. Tests first failed for the missing implementation. Later failing tests
covered a `.` cache path, split-related metadata, filesystem case aliases and
exact cross-split source hashes before each correction.

The helper binds declared Markdown sources and targets to one pinned SHA-1
Git commit and a complete recursive object inventory. It rejects stale source
or target bytes, incomplete inventories, escaping paths, symlink/submodule
ancestry, partial repositories and conflicting materializations. Cache reads
are confined by POSIX descriptors; private materialization uses immutable
verified byte snapshots. Present targets require verified cached bytes; absent
targets require absence from the pinned inventory.

Source selection and split checks happen on manifest metadata before cache
byte access. Exact hashes and recorded pair/near-duplicate groups protect the
reserved split. Unknown normalized duplicate evidence stays unavailable; it
cannot be recovered without reading reserved sources. No natural or holdout
bytes were used in these synthetic tests.

This stage proves only explicitly declared targets. Reference enumeration,
annotation binding and strict evaluator integration remain outstanding. The
existing unbound local-link rejection remains unchanged; independent M012
scoring is still unavailable. No default policy, baseline or source freeze was
changed. Historical report implementation hashes retain their original meaning.

Verification: `make check dogfood rule-quality-regression` passed with 3,568
tests, Ruff, strict Mypy, generated documentation and baseline-aware prose
checks. Curated scores remain 366 TP / 6 FP / 0 FN under all-rules and
106 TP / 4 FP / 0 FN under production, retaining all exact known mismatches.
These are regression results, not independent effectiveness estimates.
`native-preparation-checks.json` binds the full local gate log.
