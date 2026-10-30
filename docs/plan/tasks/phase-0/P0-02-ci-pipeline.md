# P0-02 · Set up CI

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 0 · Setup & spikes | 0.5 day | P0-01 | todo |

## Why
CI is the cheapest guard against regressions in adapters and prompts. Starting it while the suite is empty costs minutes; adding it later costs a cleanup.

## What to do
- [ ] `.github/workflows/ci.yml` running on push and PR: `uv sync`, `ruff check`, `ruff format --check`, `pytest`.
- [ ] Add one trivial test (`tests/test_version.py`).
- [ ] Block network in tests (e.g. `pytest-socket`) so adapters must use recorded fixtures.
- [ ] Reserve later CI steps as commented placeholders: `claude plugin validate --strict`, `skills-ref validate` (filled in P4-06).

## Done when
- CI is green on the empty test.
- A test that tries a real HTTP request fails in CI.
