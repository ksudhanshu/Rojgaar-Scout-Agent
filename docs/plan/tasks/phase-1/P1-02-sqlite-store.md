# P1-02 · SQLite store

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1 day | P1-01 | todo |

## Why
A single local SQLite file holds jobs, run history and feedback, needs no server, and supports full-text search (FTS5) and vectors (sqlite-vec) later. `first_seen`/`last_seen` power "new today", staleness and repost detection.

## What to do
- [ ] `src/rojgaar/store.py` with migrations (simple numbered SQL files).
- [ ] Tables: `jobs` (uid PK, fields from P1-01, `first_seen`, `last_seen`, `market`), `sources` (name, tier, tos_url, last_reviewed), `runs` (date, status, started_at, finished_at, counts), `feedback` (job uid, rating, reason tag, at).
- [ ] Upsert that updates `last_seen` on re-sightings and keeps `first_seen`.
- [ ] Default path `~/RojgaarScout/state/rojgaar.db`, overridable by env var.

## Done when
- Inserting the same job twice keeps one row with updated `last_seen`.
- A query for "first seen today" returns only new jobs.
