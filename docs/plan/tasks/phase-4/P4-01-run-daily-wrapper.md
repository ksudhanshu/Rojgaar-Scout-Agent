# P4-01 · `rojgaar run-daily` wrapper

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 4 · Daily automation + multi-CLI | 2 days | P1-13, P2-06, P3-06 | todo |

## Why
This is the one command the scheduler calls. It must be **idempotent** (safe to run twice), bounded (time and budget caps) and safe (no bypass flags), because nobody is watching at 7 a.m.

## What to do
- [ ] Take a lock file; exit if another run holds it.
- [ ] Exit immediately if `runs` already has a success row for today.
- [ ] Run fetch → filters → cheap scoring → shortlist (all in Python, before any host).
- [ ] Invoke the chosen host headless with the `/rojgaar-daily` skill, using the commands from P0-04:
  - `claude -p "/rojgaar-scout:daily" --output-format json --permission-mode dontAsk --allowedTools "mcp__plugin_rojgaar-scout_rojgaar__*" --max-budget-usd <cap>`
  - `codex exec --json --output-schema … --sandbox workspace-write`
  - `muse exec --json --disable-approval --max-model-steps <N>`
- [ ] Time limit; validate returned JSON against schema; JSONL log to `state/logs/`; desktop notification with a one-line summary.
- [ ] Never pass `--yolo`, `danger-full-access` or `bypassPermissions`.

## Done when
- Running twice in a day does nothing the second time; a killed run releases the lock; a host failure still leaves the `--no-llm` report.
