# P4-04 · Codex adapter

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 4 · Daily automation + multi-CLI | 1 day | P2-05, P3-03 | todo |

## Why
Codex reads `AGENTS.md` and `.agents/skills/` natively; it only needs subagent TOML files and MCP config.

## What to do
- [ ] `.codex/agents/{ranker,writer,verifier}.toml` mirroring the Claude agents.
- [ ] `rojgaar setup codex`: add `[mcp_servers.rojgaar]` to `~/.codex/config.toml` (back up first; idempotent).
- [ ] Keep `AGENTS.md` under Codex's 32 KiB cap.
- [ ] Document network behaviour from P0-05.

## Done when
- `codex exec` runs the daily skill end to end and produces a schema-valid result.
