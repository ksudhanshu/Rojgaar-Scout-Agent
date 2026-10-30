# P5-07 · Docs and PyPI release

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 5 · Polish & community | 1.5 days | P4-07 | todo |

## Why
Users need to know exactly what the tool reads, what it sends to a model provider, and what it will never do, before they trust it with their CV.

## What to do
- [ ] README: quick start (`uvx rojgaar-scout init`), host setup per CLI, daily schedule, screenshots of a report and an application folder.
- [ ] `docs/data-flow.md`: what stays local, what reaches the model provider (job text, bank claims with placeholders), what never does (`pii.yaml`).
- [ ] `docs/sources-and-terms.md`: every source with tier, ToS link, last reviewed date; the no-scraping rules.
- [ ] `docs/login-options.md` from P0-06.
- [ ] Release `rojgaar-scout` 0.1.0 to PyPI via trusted publishing; tag; changelog.

## Done when
- A new user on a clean machine follows the README to a first report without help; `uvx rojgaar-scout --version` works from PyPI.
