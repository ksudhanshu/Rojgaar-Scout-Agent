# P2-06 · `rojgaar-rank` skill and rubric judge

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 2 · Profile + ranking | 2 days | P2-03, P2-05 | todo |

## Why
Stage 3 is where the model earns its keep. Asking for "a score out of 100" gives noisy numbers; asking for categorical scores per dimension with evidence, then computing the final score in code, is explainable and tunable.

## What to do
- [ ] `schemas/judge_output.schema.json`: per job, dimensions 0–3 (title alignment, must-have coverage with met/partial/missing per requirement and the bank item that meets it, seniority/YOE fit, logistics, preference fit), `verdict` (strong/good/stretch/poor), `dealbreaker_hit`, ≤3 reasons, ≤3 gaps, `risk_flags`.
- [ ] `.agents/skills/rojgaar-rank/SKILL.md` (standard frontmatter only): fetch shortlist via MCP, judge in batches of 5–10 behind a constant profile prefix (prompt-cache friendly), shuffle order, temperature 0 where supported, save via `save_ranking`.
- [ ] `src/rojgaar/rubric.py`: weighted score from `preferences.yaml` weights.
- [ ] Ranker subagent definition (Claude `.claude/agents/ranker.md`, Codex `.codex/agents/ranker.toml`).

## Done when
- Run manually in Claude Code on 10 real jobs: 100% schema-valid output with reasons and gaps; final order computed in code.
