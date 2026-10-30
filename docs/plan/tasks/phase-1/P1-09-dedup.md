# P1-09 · Deduplication

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1.5 days | P1-02 | todo |

## Why
The same job appears on the employer's ATS, on aggregators and as reposts. Showing it three times wastes your attention and LLM tokens. Fuzzy title matching merges different jobs (one practitioner saw "Analyst I" merged with "Analyst II"), so use exact keys first.

## What to do
- [ ] Cascade of exact keys: (1) ATS type + job ID, (2) canonical apply URL with tracking params stripped, (3) normalized `company | title | city-or-remote`.
- [ ] Treat the employer's own ATS record as canonical; merge missing fields from copies.
- [ ] Repost detection: MinHash-LSH on description shingles (`datasketch`, 128 permutations, threshold ~0.8) within the same company, confirmed by exact Jaccard.
- [ ] Record `duplicate_of` so the report can say "also on RemoteOK".

## Done when
- A second fetch on the same day inserts 0 duplicates.
- Fixture tests: cross-board duplicate merged; "Engineer I" vs "Engineer II" kept separate; lightly edited repost detected.
