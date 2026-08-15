# Release blockers

Last evaluated: 2026-08-15.

Complete every gate below for the exact **ProseProbe 0.1.0** release commit.
Do not create the `v0.1.0` tag or publish a GitHub release early: publishing
that release starts the PyPI workflow.

## Repository gates

- [ ] Confirm the worktree is clean and `master` matches `origin/master`:

  ```console
  git status --short --branch
  git rev-parse HEAD
  git rev-parse origin/master
  ```

- [ ] Run the local quality and release checks on that commit:

  ```console
  make check
  make dogfood
  make rule-quality
  make nfr-check
  ```

- [ ] Require the complete GitHub CI matrix to pass for the same commit on
  Python 3.11, 3.12, and 3.13. Do not rely on the status of a different or
  merely more recent commit.

## Package gates

- [ ] Build the source and wheel distributions, then validate both:

  ```console
  make build
  twine check --strict dist/*
  ```

- [ ] Inspect the packaged README rendering and confirm its documentation and
  license links resolve outside a checkout.
- [ ] Install the wheel in a new virtual environment and smoke-test:

  ```text
  proseprobe version
  proseprobe check --help
  python -m proseprobe version
  import proseprobe
  ```

## Release identity gates

- [ ] Choose the legal copyright holder and add it after
  `Copyright (c) 2026` in [`LICENSE`](LICENSE). Keep it consistent with the
  ownership and author information the project intends to publish.
- [ ] Replace the `0.1.0` `Unreleased` marker in
  [`CHANGELOG.md`](CHANGELOG.md) with the ISO release date, add an empty
  `Unreleased` section, and review the notes against the final diff.
- [ ] Replace the README's pre-release installation guidance with the published
  PyPI, pipx, and `v0.1.0` pre-commit commands only for the final release
  candidate.
- [ ] Confirm no local or remote `v0.1.0` tag or GitHub release exists before
  creating the audited tag.
- [ ] Confirm the PyPI JSON endpoint returns 404 immediately before
  publication. A pending trusted publisher does not reserve the project name.

## Trusted publishing gates

- [ ] Create or verify the pending PyPI trusted publisher with these exact
  values:

  | Field | Value |
  | --- | --- |
  | PyPI project | `proseprobe` |
  | GitHub owner | `johnmulder` |
  | Repository | `proseprobe` |
  | Workflow | `release.yml` |
  | Environment | `pypi` |

- [ ] Confirm the protected GitHub `pypi` environment requires approval and
  permits only `v*` tags.
- [ ] Confirm the pending publisher appears in PyPI and matches the GitHub
  workflow and environment exactly.

## Publication boundary

After every gate passes, create the `v0.1.0` GitHub release from the audited
commit. The release workflow builds once, attaches the distributions, and waits
for approval on the protected `pypi` environment. Approving that environment
authorizes publication to PyPI.
