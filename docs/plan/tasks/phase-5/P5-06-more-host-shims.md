# P5-06 · Gemini CLI and OpenCode shims

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 5 · Polish & community | 1 day | P4-06 | todo |

## Why
The shared skills + MCP design makes extra hosts cheap. Adding them widens the user base at little cost.

## What to do
- [ ] Gemini CLI: `gemini-extension.json` pointing at the MCP server and skills.
- [ ] OpenCode: MCP config writer in `rojgaar setup opencode`.
- [ ] Verify headless invocation for each and add to `run-daily --host`.
- [ ] Mark as "community-supported" in the README until soak-tested.

## Done when
- Each new host runs the daily skill manually and produces a schema-valid result.
