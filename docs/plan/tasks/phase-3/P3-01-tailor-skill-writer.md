# P3-01 · `rojgaar-tailor` skill and writer agent

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 3 · Drafting + truthfulness | 2 days | P2-01, P2-05 | todo |

## Why
The writer turns your bank into a CV aimed at one job. Its only allowed moves are select, reorder and rephrase. Every bullet carries the ID of the claim it came from, so code can check it.

## What to do
- [ ] `schemas/draft_output.schema.json`: summary, sections, bullets `[{text, src: [claim IDs]}]`, skills list, cover-letter fields.
- [ ] `.agents/skills/rojgaar-tailor/SKILL.md`: read job + bank via MCP; pick the most relevant claims; rephrase toward the job's language **without adding facts**; mark missing requirements as gaps, never add them; output via `save_application_draft`.
- [ ] Writer subagent definitions for Claude and Codex, tools limited to rojgaar MCP.
- [ ] Use placeholders for personal details (see P3-07).

## Done when
- For 5 real jobs, every output bullet has at least one valid `src` ID and the draft validates against the schema.
