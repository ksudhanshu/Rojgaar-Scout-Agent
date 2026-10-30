# Rojgaar-Scout — instructions for coding agents

This file is read by Codex, Muse Code and (through `CLAUDE.md`) Claude Code.

## What this project is
A local-first job search agent. A deterministic Python core (`src/rojgaar`) fetches public job
postings, filters and scores them; the host CLI's model only ranks a shortlist and drafts CVs.
**The tool never submits applications.**

## Hard rules
1. Never add a tool, command or skill that submits an application, fills a web form, sends email
   or logs in to a job board on the user's behalf.
2. All network access lives in `src/rojgaar/http.py` and `src/rojgaar/sources/`. Agents and skills
   never fetch the web; they use the `rojgaar` MCP tools.
3. Never put anything from `pii.yaml` into a prompt, log or MCP tool result.
4. CV and cover-letter text may only select, reorder and rephrase claims from `bank.yaml`.
   Every bullet carries `src` claim IDs. `rojgaar check-draft` must pass before a draft is ready.
5. Respect source terms: honest User-Agent, one request per host at a time, honour `Retry-After`,
   no CAPTCHA bypass, no proxies, no scraping of LinkedIn/Glassdoor.
6. Do not copy code from AGPL projects (AIHawk, ApplyPilot, OpenResume).

## Working on the code
- Python ≥ 3.11, `uv` for environments. `make install` then `make test`.
- Tests are offline: HTTP is mocked with `httpx.MockTransport` and recorded fixtures in
  `tests/fixtures/`. Do not add tests that hit the network.
- Unit tests: `tests/unit/`. Integration tests: `tests/integration/` (marked `integration`).
- Keep modules small and pure where possible; side effects go in `store.py`, `http.py`, `cli.py`.

## Skills
Shared skills live in `src/rojgaar/data/skills/*/SKILL.md` (shipped inside the package) with standard
Agent Skills frontmatter only (`name`, `description`). Do not add host-specific frontmatter there.
`rojgaar setup <host>` copies them into the user's workspace as `.agents/skills` and `.claude/skills`.
