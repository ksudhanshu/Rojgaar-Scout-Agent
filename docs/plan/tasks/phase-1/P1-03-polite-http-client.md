# P1-03 · Polite HTTP client

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 1 day | P0-01 | todo |

## Why
The legal risk in job data is contracts and account bans, not reading public pages. Guardrails belong in code, not policy text, so every adapter inherits them automatically.

## What to do
- [ ] `src/rojgaar/http.py` wrapping `httpx`:
  - Honest User-Agent: `RojgaarScout/<version> (+<repo URL>; personal job search)`.
  - Per-host concurrency 1, 1–3 s jittered delay.
  - Honour `Retry-After` on 429/403; exponential backoff; give up after N tries.
  - robots.txt check for HTML fetches.
  - On-disk response cache with ETag/Last-Modified support.
  - Hard timeout per request.
- [ ] Never: CAPTCHA solvers, stealth browsers, rotating proxies, logging in on the user's behalf.

## Done when
- Tests (with a fake server) prove: one concurrent request per host, Retry-After respected, cache hit on second call.
