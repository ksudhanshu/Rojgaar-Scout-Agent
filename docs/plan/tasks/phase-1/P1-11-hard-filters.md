# P1-11 · Hard filters

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1 day | P1-09, P1-10 | todo |

## Why
Stage 1 of the funnel is free and deterministic: drop what clearly fails your rules so nothing expensive ever sees it. The key rule is **fail-open**: a missing field never drops a job, because many good postings omit salary or visa info.

## What to do
- [ ] `src/rojgaar/filters.py` applying, in order: already seen, excluded company, excluded keyword/title word, location (via P1-10), remote mode, employment type, max age (`first_seen`), seniority (±1 level), salary (drop only if stated max < floor), sponsorship (drop only if posting explicitly says no sponsorship **and** you need it).
- [ ] Record the reason for every drop (`dropped_by`) so you can audit false drops.

## Done when
- Tests show unknown salary, unknown location type and unknown seniority all **pass**.
- `rojgaar report --no-llm --show-dropped` lists drop reasons.
