# P4-06 · `rojgaar doctor` and CI validation

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 4 · Daily automation + multi-CLI | 1 day | P4-03, P4-04, P4-05 | todo |

## Why
Most support questions are setup problems. `doctor` answers them before a user has to ask, and CI catches broken manifests before release.

## What to do
- [ ] `rojgaar doctor` checks: Python and package versions; `~/RojgaarScout/` exists and files validate; which hosts are installed and logged in; MCP config present per host; schedule installed; last run status; sources reachable (one cheap request each).
- [ ] Clear fix hints for each failure.
- [ ] CI: `claude plugin validate --strict`, `skills-ref validate` on `.agents/skills/`, JSON-schema checks on example config.

## Done when
- `doctor` passes on a good setup and names the exact fix on each broken case tested; CI runs all validators.
