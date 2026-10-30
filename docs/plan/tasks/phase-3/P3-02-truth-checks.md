# P3-02 · Deterministic truth checks

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 3 · Drafting + truthfulness | 2 days | P3-01 | todo |

## Why
A 2026 study found strict prompts alone still left a fabrication in 50% of tailored resumes, and human review alone left 75%. Layered checks cut fabrication far more. Code checks are the layer that never gets tired.

## What to do
- [ ] `src/rojgaar/truth/` checks, each returning findings with the bullet and reason:
  - every bullet has a valid `src` ID;
  - every number and date in a bullet appears in its cited claim;
  - every skill term exists somewhere in the bank (catches JD "trap" skills);
  - qualifiers preserved ("co-led" never becomes "led");
  - timeline consistent (no technology before it existed or before the role started).
- [ ] Fixture set of drafts with planted fabrications: invented metric, dropped "co-", JD trap skill, anachronism, unsourced bullet.
- [ ] Any finding blocks the draft from being marked ready.

## Done when
- 100% of planted fabrications are caught; clean drafts produce zero findings.
