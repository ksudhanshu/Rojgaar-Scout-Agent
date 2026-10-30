# P2-03 · Cheap scoring: BM25 + embeddings + RRF

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 2 · Profile + ranking | 2 days | P1-11, P2-01 | todo |

## Why
Stage 2 of the funnel ranks everything that passed the hard filters on your laptop's CPU, for free, so only the best 30–60 reach the LLM. Two different methods fused together are more robust than either alone.

## What to do
- [ ] BM25 over title + skills using SQLite FTS5.
- [ ] Local embeddings with `fastembed` (`bge-small-en-v1.5` default); store vectors in sqlite-vec or numpy.
- [ ] "Ideal job descriptions": have the host model write 1–3 ideal JDs from your profile once; embed them as queries (match JD-to-JD, not CV-to-JD).
- [ ] Fuse rankings with Reciprocal Rank Fusion: `score = Σ 1/(60 + rank)`.
- [ ] Take the top N (default 40, configurable) as the shortlist.

## Done when
- `rojgaar rank-candidates` writes a shortlist with per-job BM25 rank, embedding rank and fused score.
- Runs on 2,000 jobs in under a minute on a laptop.
