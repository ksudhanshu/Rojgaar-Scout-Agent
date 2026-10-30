# P1-06 · Remote job API adapters

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1.5 days | P1-01, P1-03 | todo |

## Why
Free remote-job feeds add remote-US roles from companies not yet in your registry. Each has its own usage rules, which the adapter must encode.

## What to do
- [ ] **Himalayas:** free key, 60 req/min and 10k/day; filter to US-eligible; don't redistribute.
- [ ] **Remotive:** at most ~4 fetches a day, never more than 2 req/min; data has a 24 h delay.
- [ ] **RemoteOK:** first array element is a legal notice; keep attribution and a link back.
- [ ] **We Work Remotely:** category RSS feeds.
- [ ] Filter to `remote-US` or worldwide-remote using `applicant_location_requirements` where present.
- [ ] Show source attribution in every report line.

## Done when
- Fixture tests pass for all four; each adapter enforces its rate rule in code.
