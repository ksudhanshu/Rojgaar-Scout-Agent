# P4-07 · 7-day unattended soak test

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 4 · Daily automation + multi-CLI | 7 days elapsed (~1 h active) | P4-02, P4-06 | todo |

## Why
A daily tool is only proven by running daily. Real-world failures (expired logins, a source changing format, the laptop asleep) only show up over several days.

## What to do
- [ ] Let the schedule run for 7 consecutive days on your machine, including at least one night with the laptop asleep at run time.
- [ ] Rotate the host across the week so each of Claude Code, Codex and Muse runs at least twice.
- [ ] Each morning: read the report, note problems in `docs/decisions/0004-soak-test.md`.

## Done when
- 7 successful daily reports in a row; each host produced a valid report; every issue found has a fix or a ticket.
