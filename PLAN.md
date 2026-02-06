# Slop Lint — Development Plan

## Phase 9 — Slim dev dependencies

### Current state

Runtime dependencies are already zero — `dependencies = []`.

The build backend (`hatchling`) is a PEP 517 requirement and cannot be
removed.

The dev extras currently bundle five packages into a single group:

```toml
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1.0",
    "hypothesis>=6.0",
]
```

### Analysis

| Dev dependency | Where used | Hard requirement? |
|---|---|---|
| `pytest` | Every test file — fixtures, parametrize, conftest | **Yes** — 519 tests depend on it |
| `hypothesis` | `tests/test_property.py` only (261 lines) | No — property-based fuzz tests |
| `pytest-cov` | `make test-cov` only (CLI flag) | No — never imported by code |
| `mypy` | `make typecheck` only | No — never imported by code |
| `ruff` | `make lint` / `make format` only | No — never imported by code |

### Plan

**9.1  Split extras into tiers**

```toml
[project.optional-dependencies]
test = ["pytest>=7.0"]
dev  = ["pytest>=7.0", "pytest-cov>=4.0", "mypy>=1.0", "ruff>=0.1.0", "hypothesis>=6.0"]
```

- `pip install -e ".[test]"` — minimum needed to run `make test`.
- `pip install -e ".[dev]"` — full contributor experience (unchanged).

**9.2  Guard hypothesis behind `importorskip`**

In `tests/test_property.py`, add at the top:

```python
hypothesis = pytest.importorskip("hypothesis")
```

This makes the entire file skip cleanly when hypothesis is not installed,
so `pip install -e ".[test]" && make test` still passes.

**9.3  Make Makefile targets resilient**

Add `@command -v <tool> >/dev/null 2>&1 || …` guards to `lint`,
`typecheck`, and `test-cov` targets so they print a skip message instead
of failing when ruff / mypy / pytest-cov are absent.

**9.4  Clean stale packages from .venv**

Uninstall leftover runtime deps that are no longer declared:

```
pip uninstall -y typer rich click mistune regex shellingham \
    markdown-it-py mdurl Pygments
```

### Implementation order

1. Update `pyproject.toml` with tiered extras.
2. Guard hypothesis import in `test_property.py`.
3. Update Makefile targets with tool-availability checks.
4. Uninstall stale packages from `.venv`.
5. Run `make all` to verify.  Run `make test` with `.[test]` only to
   verify the slim path works.
6. Commit.
