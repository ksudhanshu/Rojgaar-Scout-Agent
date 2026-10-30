# P0-05 · Spike: auth and networking under the OS scheduler

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 0 · Setup & spikes | 1 day | P0-04 | todo |

## Why
This is the riskiest unknown in the whole plan. A launchd or systemd job runs without your GUI session, so keychain or OAuth logins may not be available, and Codex/Muse sandboxes may block the MCP server's network. If this fails, the fallback design must be chosen before Phase 1.

## What to do
- [ ] Write a tiny shell wrapper that runs each P0-04 command and logs stdout, stderr and exit code.
- [ ] macOS: a LaunchAgent plist with `StartCalendarInterval`, a few minutes ahead. Linux: a systemd user service + timer with `Persistent=true`.
- [ ] Test each host twice: with your normal subscription login, and with an API key env var (`ANTHROPIC_API_KEY`, `CODEX_API_KEY`, `META_API_KEY`).
- [ ] Test with the laptop asleep at the scheduled time; confirm the catch-up run.
- [ ] Test whether the MCP server can reach the network under Codex and Muse defaults. If not, test the fallback: fetch everything **before** calling the host, so the MCP server only reads SQLite.

## Done when
- `docs/decisions/0002-scheduler-auth.md` records pass/fail per host × OS × auth method, the chosen default, and the fallback.

## Notes
The plan's preferred answer either way: `run-daily` does all fetching before invoking a host, which avoids the sandbox question entirely.
