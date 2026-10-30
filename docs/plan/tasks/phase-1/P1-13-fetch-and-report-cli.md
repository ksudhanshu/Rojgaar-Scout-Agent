# P1-13 · `rojgaar fetch` and `rojgaar report --no-llm`

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1 day | P1-04 … P1-12 | todo |

## Why
This is the Phase 1 milestone: a useful daily list with no AI at all. If this list is already good, the LLM only has to make it better; if it is bad, no prompt will fix it.

## What to do
- [ ] `rojgaar fetch`: run every enabled source from `preferences.yaml` → sanitize → normalize → dedup → store; print counts per source (fetched, new, duplicate, errors).
- [ ] `rojgaar report --no-llm`: write `~/RojgaarScout/reports/YYYY-MM-DD.md` listing jobs first seen since the last report that pass hard filters, grouped by company, with source attribution and apply links.
- [ ] A failing source logs an error and never stops the others.

## Done when
- A second run the same day reports "0 new".
- The report lists only new jobs since yesterday, each with source attribution.
- No adapter exceeds 1 concurrent request per host; the test suite passes offline.
