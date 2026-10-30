# P5-05 · Contributor guide and adapter template

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 5 · Polish & community | 1 day | P1-04 | todo |

## Why
New sources are the easiest contribution for an open-source community. A guide plus a template keeps quality and the ToS posture consistent.

## What to do
- [ ] `CONTRIBUTING.md`: setup, tests, branch naming, decision records, AGPL warning.
- [ ] `docs/adding-a-source.md`: adapter interface, fixtures, rate rules, `sources.yaml` entry with tier/ToS link, what never gets accepted (logins, CAPTCHA bypass, proxies).
- [ ] `src/rojgaar/sources/_template.py` + a template test.
- [ ] Issue templates: new source, bug, company registry addition.

## Done when
- Someone who has not seen the code adds a working ATS adapter using only the guide.
