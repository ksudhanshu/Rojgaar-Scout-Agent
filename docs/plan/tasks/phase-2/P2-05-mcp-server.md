# P2-05 · rojgaar MCP server

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 2 · Profile + ranking | 2 days | P1-02, P0-03 | todo |

## Why
The MCP server is the only door between the host model and your data. Narrow, typed tools mean a malicious job posting has no channel to exfiltrate anything or take an action you didn't design.

## What to do
- [ ] `src/rojgaar/mcp_server.py`, launched by `uvx rojgaar-scout mcp`.
- [ ] Read tools: `get_shortlist(date)`, `get_job(uid)`, `get_profile()`, `get_bank()`, `get_preferences()`.
- [ ] Write tools: `save_ranking(json)`, `save_report(markdown)`, `save_application_draft(uid, files)`, `record_feedback(uid, rating, reason)`.
- [ ] Validate every write against its JSON schema; write only under `~/RojgaarScout/`.
- [ ] No network tool, no shell, no email, no submit.
- [ ] `get_*` never returns `pii.yaml` contents.

## Done when
- Tool listing shows only the tools above; schema-invalid writes are rejected with a clear error; a path-traversal attempt fails.
