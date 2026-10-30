# P1-10 · Preferences loader and Bay Area alias table

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1 day | P0-01 | todo |

## Why
`preferences.yaml` is the single place you control the search. Few postings say "Bay Area" literally, so the location filter needs an alias table that expands it into the cities postings actually use.

## What to do
- [ ] `schemas/preferences.schema.json` matching `preferences.example.yaml` (markets.us, filters, ranking, report).
- [ ] Loader with clear validation errors; default path `~/RojgaarScout/profile/preferences.yaml`.
- [ ] Ship `preferences.example.yaml` with defaults: `San Francisco, CA`, `Bay Area, CA`, `remote-US`.
- [ ] `config/metros.yaml`: `Bay Area, CA` → San Francisco, Oakland, San Jose, Palo Alto, Mountain View, Sunnyvale, Santa Clara, Menlo Park, Redwood City, San Mateo, Fremont, Berkeley, Cupertino, South San Francisco, Emeryville, Foster City, Burlingame, Milpitas, Los Gatos, Walnut Creek, Pleasanton, San Ramon, Hayward, plus "SF Bay Area", "Silicon Valley".
- [ ] Location matcher that uses the alias table and handles "Remote (US)", "Remote - United States", "Anywhere in the US".

## Done when
- Tests: "Mountain View, CA" matches `Bay Area, CA`; "Remote – US only" matches `remote-US`; "Austin, TX" matches neither.
