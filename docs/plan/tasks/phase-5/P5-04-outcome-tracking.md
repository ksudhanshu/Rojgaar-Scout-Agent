# P5-04 · Outcome tracking

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 5 · Polish & community | 1 day | P3-06 | todo |

## Why
Outcomes (applied, screen, interview, offer, rejected) tell you whether the score threshold and the drafts actually work, sooner than any benchmark.

## What to do
- [ ] `rojgaar status <uid> applied|screen|interview|offer|rejected|withdrawn` updates `status.json` history.
- [ ] `rojgaar stats`: applications, response rate, interview rate by verdict band and by source.
- [ ] Use outcome data to suggest a score threshold.

## Done when
- `rojgaar stats` shows rates per verdict band from real `status.json` files.
