# P1-05 · Workable and SmartRecruiters adapters

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1 day | P1-04 | todo |

## Why
They widen employer coverage with the same adapter pattern. SmartRecruiters' auth status is uncertain, so verify before enabling it by default.

## What to do
- [ ] **Workable:** public widget/account JSON endpoint; map to `Job`.
- [ ] **SmartRecruiters:** test the company postings endpoint without a key. If a key is now required, ship it in the opt-in tier instead.
- [ ] Fixtures and offline tests for both.
- [ ] Add both to `config/sources.yaml` with `tier`, `tos_url`, `last_reviewed`.

## Done when
- Tests pass; `sources.yaml` records SmartRecruiters' verified auth status.
