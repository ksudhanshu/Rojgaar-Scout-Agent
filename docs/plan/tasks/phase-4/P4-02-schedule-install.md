# P4-02 · `rojgaar schedule install`

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 4 · Daily automation + multi-CLI | 1.5 days | P4-01, P0-05 | todo |

## Why
The CLIs' built-in schedulers don't fit: cloud tasks have no local files, desktop tasks need the app open, `/loop` expires. OS schedulers can catch up after the laptop sleeps.

## What to do
- [ ] macOS: write a LaunchAgent plist (`StartCalendarInterval`), load with `launchctl`.
- [ ] Linux: systemd user service + timer with `Persistent=true`.
- [ ] Windows: Task Scheduler XML with `StartWhenAvailable=true`.
- [ ] Default time just off the hour (e.g. 07:13) to avoid the top-of-hour rush.
- [ ] `rojgaar schedule status` and `rojgaar schedule remove`.
- [ ] Set the auth method chosen in P0-05/P0-06 (env var file with restricted permissions if API key).

## Done when
- Install → status → remove works on macOS and Linux; a missed run fires on wake.
