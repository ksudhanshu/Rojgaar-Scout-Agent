# P1-07 · HN "Who is hiring", The Muse, USAJOBS adapters

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1.5 days | P1-01, P1-03 | todo |

## Why
HN's monthly thread is rich in Bay Area startup roles; The Muse and USAJOBS add US coverage through documented APIs.

## What to do
- [ ] **HN:** Algolia HN API (no key). Find the current month's "Ask HN: Who is hiring?" thread; parse top-level comments into `Job` (company, title, location, remote, URL). Mark parse confidence; low-confidence items keep raw text.
- [ ] **The Muse:** public API (500 req/h without key, 3,600 with); filter to SF/Bay Area and remote.
- [ ] **USAJOBS:** free key; your email as the User-Agent (required); filter by location.

## Done when
- Fixture tests pass; HN parser extracts company + location from at least 80% of a recorded thread's comments.
