# P1-12 · Company registry and slug discovery

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 2 days | P1-04 | todo |

## Why
No ATS publishes its customer list, so the tool must know which company uses which ATS and under what slug. A curated, verified Bay Area registry is also the hardest thing for competitors to copy.

## What to do
- [ ] `config/companies.us.yaml`: `name`, `ats`, `slug`, `careers_url`, `hq`, `added`, `verified`.
- [ ] Seed ~50 SF/Bay Area companies you would actually apply to.
- [ ] `rojgaar companies discover <careers_url>`: fetch the careers page and detect patterns (`boards.greenhouse.io/{slug}`, `jobs.lever.co/{slug}`, `jobs.ashbyhq.com/{slug}`, `apply.workable.com/{slug}`, `{tenant}.wdN.myworkdayjobs.com`).
- [ ] Learn new slugs from apply URLs seen in aggregator jobs; queue them for your approval.
- [ ] Answer the open question: which ATSs dominate your 50? Use it to order adapter work.

## Done when
- 50 seeded companies with verified slugs; `discover` correctly identifies the ATS for 10 test URLs.
