# P1-04 · Greenhouse, Lever, Ashby adapters

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 2 days | P1-01, P1-03 | todo |

## Why
These three are official, public, free, and give the employer's own full description, often with salary. They are the backbone of US coverage, especially for Bay Area tech companies.

## What to do
- [ ] Adapter interface in `src/rojgaar/sources/base.py`: `fetch(company) -> list[Job]`.
- [ ] **Greenhouse:** `GET boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` (no auth).
- [ ] **Lever:** `GET api.lever.co/v0/postings/{site}?mode=json`. Check whether `createdAt` is present (open question).
- [ ] **Ashby:** `GET api.ashbyhq.com/posting-api/job-board/{name}?includeCompensation=true`.
- [ ] Map each into `Job`; keep `raw`.
- [ ] Record real responses for 5 companies you'd apply to as fixtures in `tests/fixtures/<ats>/`.

## Done when
- Offline tests pass on fixtures for all three.
- A live smoke run prints normalized titles, locations and URLs from all three.
