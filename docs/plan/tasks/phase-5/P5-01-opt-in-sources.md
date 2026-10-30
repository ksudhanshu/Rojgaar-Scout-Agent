# P5-01 · Opt-in source tier

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 5 · Polish & community | 2 days | P1-13 | todo |

## Why
Some sources work but are undocumented, keyed, paid or legally grey. They stay off by default; a user can turn them on knowingly.

## What to do
- [ ] **Workday** `cxs` endpoint (undocumented; page size capped at 20; asking for more returns empty).
- [ ] **Adzuna** (free key; terms allow personal job search; credit "The Adzuna API").
- [ ] **Jooble** (keyed; snippets + tracking redirects).
- [ ] **JobSpy for Indeed** with a clear ToS/robots warning.
- [ ] Each is enabled only by adding it to `markets.us.sources` and confirming a warning once; `sources.yaml` records tier and ToS link.
- [ ] LinkedIn and Glassdoor scrapers are never shipped.

## Done when
- Each opt-in adapter has fixture tests and refuses to run until the user has acknowledged its warning.
