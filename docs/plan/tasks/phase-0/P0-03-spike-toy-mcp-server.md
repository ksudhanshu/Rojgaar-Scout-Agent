# P0-03 · Spike: toy stdio MCP server

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 0 · Setup & spikes | 0.5 day | P0-01 | todo |

## Why
MCP over stdio is the one tool layer all three CLIs share. Before designing real tools, prove that a ~20-line Python server can be launched by each host and can make an outbound HTTPS request.

## What to do
- [ ] Add the official Python MCP SDK as a dependency.
- [ ] `src/rojgaar/spike_mcp.py`: one tool `fetch_greenhouse(board: str)` that GETs `https://boards-api.greenhouse.io/v1/boards/{board}/jobs` and returns the job count and first 3 titles.
- [ ] Run it standalone with the MCP inspector to confirm the tool lists and returns.

## Done when
- The inspector shows the tool and a real board returns job titles.

## Notes
This is throwaway code. Delete it once P2-05 replaces it.
