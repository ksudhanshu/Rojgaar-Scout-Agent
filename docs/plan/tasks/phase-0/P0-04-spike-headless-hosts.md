# P0-04 · Spike: headless runs in all three CLIs

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 0 · Setup & spikes | 1 day | P0-03 | todo |

## Why
The daily run calls each CLI non-interactively. Each host configures MCP differently and has its own permission and sandbox flags. Find the working invocation for each now, while it is cheap to change course.

## What to do
- [ ] **Claude Code:** register the toy server in `.mcp.json`; run `claude -p "use fetch_greenhouse on <board>" --output-format json --permission-mode dontAsk --allowedTools "mcp__<server>__*"`. Also try `--json-schema` and `--max-budget-usd`.
- [ ] **Codex:** add `[mcp_servers.rojgaar]` to `config.toml`; run `codex exec --json --sandbox workspace-write "…"`.
- [ ] **Muse:** add `mcp_servers` (with `"schema_version": 1`) to `~/.config/muse/settings.json`; run `muse exec --json "…"`.
- [ ] Check whether Claude Code reads `AGENTS.md` directly or only through the `CLAUDE.md` import.
- [ ] Check whether `dontAsk` works with an MCP wildcard in `--allowedTools`.
- [ ] Record the exact working command, exit codes and output shape for each host.

## Done when
- `docs/decisions/0001-headless-invocation.md` has a table: host × (command, config file, auth used, JSON output OK?, tool call OK?, notes).

## Notes
Never use `--yolo`, `danger-full-access` or `bypassPermissions`, even in the spike.
