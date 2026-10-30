# P3-03 · Verifier agent and `rojgaar-verify` skill

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 3 · Drafting + truthfulness | 1 day | P3-02 | todo |

## Why
Code catches mechanical errors; a second model in a **fresh context** catches meaning drift, like a claim reworded into something stronger. Fresh context matters: a reviewer that saw the writer's reasoning tends to agree with it.

## What to do
- [ ] `.agents/skills/rojgaar-verify/SKILL.md`: given only the cited source claims and the draft (not the job, not the writer's notes), flag any bullet that says more than its sources.
- [ ] Verifier subagent definitions for Claude and Codex; for Muse, spawn a child agent from the skill.
- [ ] Output findings in the same format as P3-02; merge into one findings list.

## Done when
- On the planted-fabrication fixtures, the verifier flags at least the meaning-drift cases code can't catch; findings appear in `review.md`.
