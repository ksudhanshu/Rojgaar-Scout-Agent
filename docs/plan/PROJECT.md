# Rojgaar-Scout-Agent — Project Plan

> An MIT-licensed job search agent that runs locally on your own machine, inside AI coding CLIs (Claude Code, OpenAI Codex CLI, Meta Muse Code). Every day it scans job boards, ranks openings against your profile, reports the best matches, and drafts a tailored CV and cover letter for each. **You review and submit; the tool never submits.**

## Scope

| Item | Decision |
|---|---|
| Market | **US only** |
| Default locations | **San Francisco, CA**, **Bay Area, CA**, remote-US |
| Host CLIs | Claude Code, Codex CLI, Muse Code (one shared skill set) |
| License | MIT |
| Submission | Never automated. No submit or form-fill tool exists. |
| Data | Stays on your machine in `~/RojgaarScout/` |

## Architecture in one paragraph

A **deterministic Python core** (`rojgaar` CLI + stdio MCP server) does everything that has a correct answer: fetching from public job APIs, sanitizing, deduplicating, filtering, cheap scoring, storage (SQLite) and rendering. The **host CLI's model** only does judgment: ranking a shortlist of 30–60 jobs, drafting CVs and cover letters for the top 5, and verifying them. The **OS scheduler** (launchd / systemd / Task Scheduler) runs `rojgaar run-daily` each morning. See the System Design canvas and `Rojgaar Scout Agent build plan.md` for the full reasoning.

```
OS scheduler → rojgaar run-daily → [core: fetch → sanitize → dedup → filter → score → shortlist]
             → host CLI headless → [ranker → writer → verifier] via rojgaar MCP tools
             → code checks + render → reports/ + applications/ → YOU review and apply
```

## Key files

| File | Purpose |
|---|---|
| `~/RojgaarScout/profile/bank.yaml` | Every true claim about you, each with a stable ID (source of truth) |
| `~/RojgaarScout/profile/preferences.yaml` | Market, locations, filters, ranking weights, report settings |
| `~/RojgaarScout/profile/pii.yaml` | Name, phone, email — never sent to a model |
| `~/RojgaarScout/state/rojgaar.db` | SQLite: jobs, sources, runs, feedback |
| `~/RojgaarScout/applications/<date>_<company>_<role>/` | jd, fit-report, cv.pdf/.docx, cover letter, review.md, status.json |

## Phases

| Phase | Goal | Rough effort* |
|---|---|---|
| **0 · Setup & spikes** | Repo exists; the riskiest unknowns (headless auth, sandbox networking, terms) are answered | 1 week |
| **1 · Deterministic core** | `rojgaar fetch` + `report --no-llm` list new SF/Bay Area/remote-US jobs, deduplicated, with no LLM | 2–3 weeks |
| **2 · Profile + ranking** | Your profile exists; the funnel ranks jobs and you can measure its quality | 2–3 weeks |
| **3 · Drafting + truthfulness** | Tailored CV + cover letter per top job, with every claim traced and checked | 2–3 weeks |
| **4 · Daily automation + multi-CLI** | Unattended daily runs on all three CLIs | 2 weeks |
| **5 · Polish & community** | Opt-in sources, feedback loop, contributor docs, PyPI release | 2+ weeks, ongoing |

\* Planning estimates for one part-time developer (~10–15 h/week), not measured figures.

**Ordering rule:** validate what could kill the project before building what is merely work. That is why Phase 0 is all spikes.

## Task index

Status values: `todo` · `in-progress` · `done` · `blocked`. Each task has its own file under `tasks/`.

### Phase 0 — Setup & spikes
| ID | Task | Depends on | Effort |
|---|---|---|---|
| [P0-01](tasks/phase-0/P0-01-repo-skeleton.md) | Create the repo skeleton | — | 0.5 d |
| [P0-02](tasks/phase-0/P0-02-ci-pipeline.md) | Set up CI | P0-01 | 0.5 d |
| [P0-03](tasks/phase-0/P0-03-spike-toy-mcp-server.md) | Spike: toy stdio MCP server | P0-01 | 0.5 d |
| [P0-04](tasks/phase-0/P0-04-spike-headless-hosts.md) | Spike: headless runs in all three CLIs | P0-03 | 1 d |
| [P0-05](tasks/phase-0/P0-05-spike-scheduler-auth.md) | Spike: auth and networking under the OS scheduler | P0-04 | 1 d |
| [P0-06](tasks/phase-0/P0-06-provider-terms-review.md) | Review provider terms for scheduled use | — | 0.5 d |

### Phase 1 — Deterministic core
| ID | Task | Depends on | Effort |
|---|---|---|---|
| [P1-01](tasks/phase-1/P1-01-job-schema-normalizer.md) | Job schema and normalizer | P0-01 | 1 d |
| [P1-02](tasks/phase-1/P1-02-sqlite-store.md) | SQLite store | P1-01 | 1 d |
| [P1-03](tasks/phase-1/P1-03-polite-http-client.md) | Polite HTTP client | P0-01 | 1 d |
| [P1-04](tasks/phase-1/P1-04-ats-adapters-core.md) | Greenhouse, Lever, Ashby adapters | P1-01, P1-03 | 2 d |
| [P1-05](tasks/phase-1/P1-05-ats-adapters-extra.md) | Workable and SmartRecruiters adapters | P1-04 | 1 d |
| [P1-06](tasks/phase-1/P1-06-remote-job-apis.md) | Remote job API adapters | P1-01, P1-03 | 1.5 d |
| [P1-07](tasks/phase-1/P1-07-hn-themuse-usajobs.md) | HN, The Muse, USAJOBS adapters | P1-01, P1-03 | 1.5 d |
| [P1-08](tasks/phase-1/P1-08-sanitizer.md) | Sanitizer | P1-01 | 0.5 d |
| [P1-09](tasks/phase-1/P1-09-dedup.md) | Deduplication | P1-02 | 1.5 d |
| [P1-10](tasks/phase-1/P1-10-preferences-and-metros.md) | Preferences loader and Bay Area alias table | P0-01 | 1 d |
| [P1-11](tasks/phase-1/P1-11-hard-filters.md) | Hard filters | P1-09, P1-10 | 1 d |
| [P1-12](tasks/phase-1/P1-12-company-registry.md) | Company registry and slug discovery | P1-04 | 2 d |
| [P1-13](tasks/phase-1/P1-13-fetch-and-report-cli.md) | `rojgaar fetch` and `report --no-llm` | P1-04…P1-12 | 1 d |

### Phase 2 — Profile + ranking
| ID | Task | Depends on | Effort |
|---|---|---|---|
| [P2-01](tasks/phase-2/P2-01-experience-bank.md) | Experience bank schema and first bank | P0-01 | 1 d |
| [P2-02](tasks/phase-2/P2-02-rojgaar-init.md) | `rojgaar init` onboarding | P2-01, P1-10 | 2 d |
| [P2-03](tasks/phase-2/P2-03-cheap-scoring.md) | Cheap scoring: BM25 + embeddings + RRF | P1-11, P2-01 | 2 d |
| [P2-04](tasks/phase-2/P2-04-risk-score.md) | Ghost and scam risk score | P1-02 | 1 d |
| [P2-05](tasks/phase-2/P2-05-mcp-server.md) | rojgaar MCP server | P1-02, P0-03 | 2 d |
| [P2-06](tasks/phase-2/P2-06-rank-skill-judge.md) | `rojgaar-rank` skill and rubric judge | P2-03, P2-05 | 2 d |
| [P2-07](tasks/phase-2/P2-07-eval-harness.md) | Labeled eval set and `rojgaar eval` | P2-06 | 2 d |

### Phase 3 — Drafting + truthfulness
| ID | Task | Depends on | Effort |
|---|---|---|---|
| [P3-01](tasks/phase-3/P3-01-tailor-skill-writer.md) | `rojgaar-tailor` skill and writer agent | P2-01, P2-05 | 2 d |
| [P3-02](tasks/phase-3/P3-02-truth-checks.md) | Deterministic truth checks | P3-01 | 2 d |
| [P3-03](tasks/phase-3/P3-03-verifier-agent.md) | Verifier agent and `rojgaar-verify` skill | P3-02 | 1 d |
| [P3-04](tasks/phase-3/P3-04-render-pipeline.md) | Render: RenderCV PDF, pandoc DOCX, parse-back | P3-01 | 2 d |
| [P3-05](tasks/phase-3/P3-05-cover-letter.md) | Cover letter generation and lint | P3-01 | 1 d |
| [P3-06](tasks/phase-3/P3-06-fit-report-review.md) | Fit report, review.md, application folder | P3-02, P3-04 | 1.5 d |
| [P3-07](tasks/phase-3/P3-07-pii-placeholders.md) | PII placeholders | P3-04 | 1 d |

### Phase 4 — Daily automation + multi-CLI
| ID | Task | Depends on | Effort |
|---|---|---|---|
| [P4-01](tasks/phase-4/P4-01-run-daily-wrapper.md) | `rojgaar run-daily` wrapper | P1-13, P2-06, P3-06 | 2 d |
| [P4-02](tasks/phase-4/P4-02-schedule-install.md) | `rojgaar schedule install` | P4-01, P0-05 | 1.5 d |
| [P4-03](tasks/phase-4/P4-03-claude-plugin.md) | Claude Code plugin and marketplace | P2-05, P3-03 | 1.5 d |
| [P4-04](tasks/phase-4/P4-04-codex-adapter.md) | Codex adapter | P2-05, P3-03 | 1 d |
| [P4-05](tasks/phase-4/P4-05-muse-adapter.md) | Muse adapter | P2-05, P3-03 | 1 d |
| [P4-06](tasks/phase-4/P4-06-doctor-and-validation.md) | `rojgaar doctor` and CI validation | P4-03…P4-05 | 1 d |
| [P4-07](tasks/phase-4/P4-07-soak-test.md) | 7-day unattended soak test | P4-02, P4-06 | 7 d elapsed |

### Phase 5 — Polish & community
| ID | Task | Depends on | Effort |
|---|---|---|---|
| [P5-01](tasks/phase-5/P5-01-opt-in-sources.md) | Opt-in source tier | P1-13 | 2 d |
| [P5-02](tasks/phase-5/P5-02-alert-email-parser.md) | Job-alert email parser | P1-01 | 2 d |
| [P5-03](tasks/phase-5/P5-03-feedback-loop.md) | Feedback capture and preference diffs | P2-06 | 2 d |
| [P5-04](tasks/phase-5/P5-04-outcome-tracking.md) | Outcome tracking | P3-06 | 1 d |
| [P5-05](tasks/phase-5/P5-05-contributor-guide.md) | Contributor guide and adapter template | P1-04 | 1 d |
| [P5-06](tasks/phase-5/P5-06-more-host-shims.md) | Gemini CLI and OpenCode shims | P4-06 | 1 d |
| [P5-07](tasks/phase-5/P5-07-docs-and-release.md) | Docs and PyPI release | P4-07 | 1.5 d |

## Open questions (each is a 30-minute verification ticket)

- Does SmartRecruiters' public postings endpoint now need a key? → P1-05
- Does Lever's JSON include `createdAt`? → P1-04
- Which ATSs dominate Bay Area hiring? → P1-12
- Does Claude Code read AGENTS.md natively, or only via `CLAUDE.md` import? → P0-04
- Does `--permission-mode dontAsk` work with plugin MCP wildcards in `--allowedTools`? → P0-04
- Do Codex and Muse sandbox MCP stdio servers' network access? → P0-05
- Is scheduled use of a consumer subscription within each provider's terms? → P0-06

## Conventions

- **Branches:** `p<phase>-<id>-<slug>`, e.g. `p1-04-ats-adapters`.
- **Decisions:** one file per decision in `docs/decisions/NNNN-title.md`.
- **Tests:** every adapter ships recorded fixtures; the suite passes offline.
- **Licensing:** never copy code from AGPL projects (AIHawk, ApplyPilot, OpenResume).
