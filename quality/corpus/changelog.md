# Changelog excerpt

All notable changes to the parser are recorded here.

## 1.4.0 — 2026-08-06

The release adds Setext heading support and corrects columns after block quote
markers. It also removes a duplicate cache lookup.

As of August 2026, version 1.4.0 is the supported release in this example.

### Fixed

- Preserve escaped brackets in link labels.
- Report the opening fence when a code block is not closed.
- Keep paths relative to the workspace root.

### Changed

The implementation of the parser now uses one pass instead of two. Here,
“implementation” names a concrete code change rather than empty academic prose.
