# P4-03 · Claude Code plugin and marketplace

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 4 · Daily automation + multi-CLI | 1.5 days | P2-05, P3-03 | todo |

## Why
A plugin lets a Claude Code user install everything with `/plugin marketplace add` and nothing else. Codex can read the same marketplace file.

## What to do
- [ ] `plugins/claude/.claude-plugin/plugin.json` with skills, agents (`ranker`, `writer`, `verifier`) and `.mcp.json` launching `uvx rojgaar-scout mcp`.
- [ ] Use `${CLAUDE_PLUGIN_DATA}` for anything persistent (`${CLAUDE_PLUGIN_ROOT}` changes on update); user data still lives in `~/RojgaarScout/`.
- [ ] `userConfig` for API keys marked `sensitive`.
- [ ] Root `.claude-plugin/marketplace.json`.
- [ ] Skills stay in `.agents/skills/` with standard frontmatter only; no Claude-only fields in shared skills.

## Done when
- `claude plugin validate --strict` passes; a fresh Claude Code install runs `/rojgaar-scout:daily` manually end to end.
