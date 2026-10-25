# Release status and blockers

Last evaluated: 2026-10-25. ProseProbe 0.1.0 remains unpublished.

## Verified source preparation

The source preflight at `2fff536944bb91dff0d5012625b337b2f6979bba` completed
with a clean worktree matching remote `master`:

- `make check dogfood rule-quality rule-quality-regression nfr-check` passed:
  3,996 tests, 96.35% coverage against the 90% floor, and the existing curated
  mismatch sets unchanged at six for all rules and four for production.
- The [hosted CI matrix](https://github.com/johnmulder/proseprobe/actions/runs/39544639711)
  passed for that exact source on Python 3.11, 3.12, and 3.13, including the docs
  and build jobs.
- The wheel and source archive built, `twine check --strict` passed, four
  isolated-wheel command/import checks passed, and all ten packaged README URLs
  returned HTTP 200.
- [`LICENSE`](LICENSE) already names John Mulder as the 2026 copyright holder.
- GitHub's `pypi` environment requires review by `johnmulder` and permits only
  `v*` tags. The remote `release.yml` matches the reviewed workflow, uses that
  environment, and grants `id-token: write` for trusted publishing.

These results qualify the recorded source. They do not freeze a final release
candidate after subsequent documentation or metadata changes. No release tag,
GitHub publication, PyPI upload, or protected-environment approval was performed.
The private pending PyPI publisher has not been verified.

## Remaining release work

- [ ] Finalize [`CHANGELOG.md`](CHANGELOG.md): replace the `0.1.0` `Unreleased`
  marker with the ISO release date, add an empty `Unreleased` section, and review
  the notes against the final diff. Update README installation guidance to the
  intended PyPI, pipx, and `v0.1.0` pre-commit commands at the final release
  candidate stage.
- [ ] Freeze that final clean commit and confirm `master` matches
  `origin/master`. Repeat the commit-sensitive local checks and require the
  complete hosted CI matrix for the same final commit:

  ```console
  git status --short --branch
  git rev-parse HEAD
  git rev-parse origin/master
  make check dogfood rule-quality rule-quality-regression nfr-check
  ```

- [ ] Build and strictly validate distributions from the final candidate.
  Inspect its packaged README and external documentation/license links, then
  install its wheel in a new virtual environment and run the command/import
  smoke checks:

  ```console
  make build
  twine check --strict dist/*
  proseprobe version
  proseprobe check --help
  python -m proseprobe version
  python -c 'import proseprobe'
  ```

- [ ] Verify the pending PyPI trusted publisher in the private PyPI account
  with these exact values, and confirm it matches the protected GitHub workflow
  and environment:

  | Field | Value |
  | --- | --- |
  | PyPI project | `proseprobe` |
  | GitHub owner | `johnmulder` |
  | Repository | `proseprobe` |
  | Workflow | `release.yml` |
  | Environment | `pypi` |

- [ ] Immediately before publication, confirm no local or remote `v0.1.0` tag
  or GitHub release exists and the PyPI JSON endpoint returns 404. A pending
  trusted publisher does not reserve the project name. Recheck the environment
  and workflow protections if their configuration has changed.

## Publication boundary

Do not create `v0.1.0` or publish a GitHub release before the remaining gates
pass for the audited commit. Publishing that GitHub release starts the PyPI
workflow. It builds once, attaches the distributions, and waits for approval on
the protected `pypi` environment. Approving that environment authorizes
publication to PyPI.
