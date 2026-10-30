# P2-01 · Experience bank schema and first bank

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 2 · Profile + ranking | 1 day | P0-01 | todo |

## Why
`bank.yaml` is the single source of truth for everything the tool may say about you. Tailoring may only select, reorder and rephrase claims from it, never invent. Stable IDs make every CV bullet traceable.

## What to do
- [ ] `schemas/bank.schema.json`: roles (id, org, title, start, end, location) with claims (id, text, metrics `[{value, unit}]`, skills, qualifiers, evidence, `verified_by_user`, alt_phrasings); education (id, degree, school, score `{value, scale}`); skills; certifications; projects.
- [ ] Hand-write 15–20 of your own claims with IDs like `exp.acme.b3`.
- [ ] Generate `profile.json` (JSON Resume view) from the bank for prompts and export; the bank stays the source of truth.

## Done when
- Your bank validates against the schema; `profile.json` regenerates from it deterministically.

## Notes
Qualifiers matter: "co-led" and "team of 4" are exactly what LLMs silently drop.
