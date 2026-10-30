# P4-05 · Muse adapter

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 4 · Daily automation + multi-CLI | 1 day | P2-05, P3-03 | todo |

## Why
Muse reads `AGENTS.md`, `CLAUDE.md` and `.agents/skills/`, but its plugin and subagent formats are undocumented. Rely only on what is documented.

## What to do
- [ ] `rojgaar setup muse`: add `mcp_servers.rojgaar` to `~/.config/muse/settings.json` with `"schema_version": 1` (the official key is `mcp_servers`, not `mcpServers`). Back up first; idempotent.
- [ ] Verifier: spawn a child agent from the verify skill's instructions (no definition file).
- [ ] Pin and test a specific Muse version in CI or docs.
- [ ] Note: committed project memory loads even in untrusted workspaces; keep nothing sensitive in repo memory files.

## Done when
- `muse exec --json` runs the daily skill end to end; exit codes 0/1/2/130/143 are handled by `run-daily`.
