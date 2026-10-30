# P1-01 · Job schema and normalizer

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1 day | P0-01 | todo |

## Why
Every source returns a different shape. One internal record lets filters, scoring and the LLM ignore where a job came from. Reusing schema.org `JobPosting` field names means you don't invent a vocabulary.

## What to do
- [ ] `schemas/job.schema.json` and a matching dataclass/pydantic model `Job` in `src/rojgaar/normalize.py`.
- [ ] Required: `uid` (`<ats>:<company>:<job_id>`), `title`, `description_text`, `company`, `locations[]`, `apply_url`, `source`, `first_seen`.
- [ ] Optional: `date_posted`, `remote` (`remote|hybrid|onsite|unknown`), `applicant_location_requirements`, `salary {min,max,currency,period}` (actual values only, never estimates), `employment_type`, `seniority_hint`, `valid_through`, `raw` (original payload).
- [ ] Location normalization helper: city, state, country, `remote-US`.

## Done when
- Unit tests round-trip a sample from each planned source type into `Job` and validate against the schema.

## Notes
Date traps: Greenhouse `updated_at` is not a posted date; Workday `postedOn` is text like "Posted 3 Days Ago". `first_seen` (your own timestamp) is the only date you can fully trust.
