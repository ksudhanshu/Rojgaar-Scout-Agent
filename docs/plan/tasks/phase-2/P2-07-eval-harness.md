# P2-07 · Labeled eval set and `rojgaar eval`

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 2 · Profile + ranking | 2 days | P2-06 | todo |

## Why
Research found an LLM rerank sometimes does **worse** than a cheap retriever. Without your own labels you can't tell whether a prompt or model change helped. This set becomes the regression suite.

## What to do
- [ ] Label ~150 postings from your own feed 0–3: 50 from the judge's top, 50 from the middle of stage 2, 50 random.
- [ ] Store in `eval/labels.jsonl` (private by default; ship a synthetic example set in the repo).
- [ ] `rojgaar eval` reports: stage 1 false-drop rate (target ≈0 for label ≥2), stage 2 recall@40, stage 3 NDCG@10 and precision@10, Cohen's κ judge-vs-you, and an order-swap test for position bias.
- [ ] Save each run's metrics with the prompt/model version.

## Done when
- `rojgaar eval` prints all metrics; a baseline is recorded in `docs/decisions/` and a target set for stage 2 recall.
