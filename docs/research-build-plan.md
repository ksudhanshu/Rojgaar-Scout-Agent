# Build Rojgaar-Scout around a deterministic Python core

Build Rojgaar-Scout-Agent as a **plain Python package that does all the mechanical work**: fetching jobs, deduplicating them, filtering, cheap scoring, storage and rendering. Expose that package both as a command-line tool and as an MCP server. Then add a **thin layer of portable Agent Skills** that lets Claude Code, OpenAI Codex CLI and Meta's Muse Code apply judgment only where judgment is needed: ranking a shortlist with reasons, and drafting a CV and cover letter for the top few jobs. This split matters because the space is already crowded. **santifer/career-ops (~69k stars, MIT)** and **MadsLorentzen/ai-job-search (~60k stars, MIT)** already scan boards, score jobs and tailor CVs inside coding CLIs ([career-ops](https://github.com/santifer/career-ops); [ai-job-search](https://github.com/MadsLorentzen/ai-job-search)). Neither one combines a hard no-submit rule, code-enforced truthfulness and first-class support for all three CLIs. Your project wins on four things: **a focused US default (San Francisco and the Bay Area, plus remote-US)**, **a strict "never submits" boundary**, **a truthfulness layer that traces every CV bullet back to a fact you verified**, and **one core that runs on three CLIs**. The data plan is shaped by one fact: the biggest boards (LinkedIn, Indeed) give individuals no read API and restrict automated access in their terms. Coverage should therefore come mainly from the official public ATS endpoints of US employers (Greenhouse, Lever, Ashby, Workday) plus free job APIs, with LinkedIn limited to user-driven channels such as job-alert emails. The roadmap below runs from Phase 0 to Phase 5, about 10–14 part-time weeks for a solo developer. It starts with a one-week spike that tests the riskiest unknown: whether each CLI can run unattended from your OS scheduler at all.

## Why a deterministic core and a thin LLM layer beat an "all-agent" design

The most important design decision is where the LLM sits. A useful rule is: **anything that has a correct answer belongs in code, and anything that needs taste belongs in the LLM.** Fetching a Greenhouse board, checking whether a job was seen yesterday, or rejecting a posting located in Berlin when you only accept the Bay Area or remote all have correct answers. Code does them for free, gets the same result every time, and can be unit-tested. Deciding whether "platform engineer, payments" fits your career goals better than "SRE, ad-tech" needs taste, so that is LLM work. The research literature reached the same conclusion from another direction. JobRecoGPT found that a hybrid design, with deterministic matching to narrow the set and then an LLM to rank the shortlist, gave the best balance of accuracy, cost and speed. Its total latency stayed **roughly constant at about 45 seconds even with hundreds of jobs** ([JobRecoGPT](https://arxiv.org/html/2309.11805v1)). LinkedIn's production job search uses the same funnel shape: cheap retrieval of about 1,000 candidates, a small reranker on the top 250, then calibration ([Semantic Search at LinkedIn](https://arxiv.org/html/2602.07309v1)).

There are three practical payoffs. First, **cost**. The LLM runs on your own Claude, ChatGPT or Muse subscription, so every token spent on mechanical work is quota you can't use for drafting. Second, **sandboxes**. Codex's default `workspace-write` sandbox "keeps network access turned off unless you enable it" ([Codex security](https://learn.chatgpt.com/docs/agent-approvals-security.md)). Muse defaults to `proxy-only` networking, where each outbound destination needs approval ([Muse permissions](https://dev.meta.ai/docs/muse-code/permissions)). If your skills tried to fetch job boards from inside the agent's shell, they would fail or stall on approval prompts at 7 a.m. with nobody watching. Third, **security**. Job postings are untrusted web text, and your agent holds private data (your CV). Simon Willison's "lethal trifecta" says you should never combine private data, untrusted content and the ability to communicate externally in one LLM loop ([Simon Willison](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/)). If the network fetching happens in Python *before* the LLM runs, and the LLM's only tools are narrow ones like "save this draft to this folder", then a malicious posting has no channel through which to exfiltrate anything.

The resulting architecture has four layers. The Python core (`rojgaar` CLI plus a stdio MCP server) owns the network and the database. The portable skills (`.agents/skills/*/SKILL.md`) tell each host CLI how to use the MCP tools. The local data stores (SQLite plus plain YAML and Markdown files) hold everything you own. The OS scheduler starts the daily run.

```
                        ┌──────────────────────────────────────────────┐
  OS SCHEDULER          │ launchd (macOS) / systemd --user timer        │
  (daily, ~07:13)       │ Persistent=true / Windows Task StartWhenAvail │
                        └───────────────────────┬──────────────────────┘
                                                │ runs
                                                ▼
┌────────────────────────── rojgaar run-daily --host claude|codex|muse ──────────────────────────┐
│ 1. lock file + "already succeeded today?" check (idempotent)                                     │
│                                                                                                  │
│  DETERMINISTIC PYTHON CORE (no LLM, owns the network)                                            │
│  ┌──────────┐   ┌───────────┐   ┌────────┐   ┌──────────────┐   ┌─────────────┐   ┌───────────┐  │
│  │ sources/ │──▶│ sanitize +│──▶│ dedup  │──▶│ hard filters │──▶│ BM25 + embed│──▶│ shortlist │  │
│  │ ATS APIs,│   │ normalize │   │ (ATS id│   │ (fail-open), │   │ + RRF, risk │   │ top 30–60 │  │
│  │ RSS, HN  │   │ JobPosting│   │ URL,key│   │ freshness    │   │ score       │   │           │  │
│  └──────────┘   └───────────┘   │ MinHash│   └──────────────┘   └─────────────┘   └─────┬─────┘  │
│                                 └────────┘                                              │        │
│ 2. invoke host CLI headless with /rojgaar-daily skill + JSON schema + budget cap         │        │
└──────────────────────────────────────────────────────────────────────────────────────────┼───────┘
                                                                                           ▼
┌──────────────── HOST CLI (Claude Code `claude -p` / `codex exec` / `muse exec`) ───────────────────┐
│  Skills (.agents/skills): rojgaar-daily → rojgaar-rank → rojgaar-tailor → rojgaar-verify         │
│  Agents: ranker (judge, rubric JSON) │ writer (select+rephrase claims) │ verifier (fresh context)  │
│  Tools available: ONLY rojgaar MCP tools (no web fetch, no email, no generic shell)               │
└──────────────┬───────────────────────────────────────────────────────────────────┬────────────────┘
               │ stdio MCP: get_shortlist, get_job, get_profile, get_bank,          │
               │ save_ranking, save_report, save_application_draft, record_feedback │
               ▼                                                                    ▼
┌──────────── rojgaar MCP server (same Python package) ─────────────┐   ┌──── post-processing (code) ────┐
│ typed, narrow tools; writes only under ~/RojgaarScout/            │   │ claim-ID + number + qualifier  │
└──────────────┬────────────────────────────────────────────────────┘   │ checks, RenderCV → PDF, pandoc │
               ▼                                                        │ → DOCX, parse-back test        │
┌──────────────────────────── LOCAL DATA (~/RojgaarScout) ────────────────────────────────────────┐
│ state/rojgaar.db (SQLite: jobs, sources, seen, runs, feedback, vectors via sqlite-vec)           │
│ profile/bank.yaml  profile/preferences.yaml  profile/pii.yaml (never sent to LLM)                │
│ reports/2026-10-29.md   applications/<date>_<company>_<role>/ (jd, fit-report, cv, letter, review)│
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
                     YOU read the report, edit drafts, and click "Submit" yourself.
```

The "multi-agent pipeline" in the project description maps onto this diagram as four roles: **scout, ranker, writer, verifier**. Notice that the scout is not an LLM agent at all. Fetching needs no intelligence, so it is pure code. That's deliberate, and it is the most common mistake to avoid. The ranker, writer and verifier are host-CLI subagents. Claude Code defines them as Markdown files with YAML frontmatter and lets you restrict each one's `tools` ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)). Codex defines them as TOML files in `.codex/agents/` ([Codex subagents](https://learn.chatgpt.com/codex/agent-configuration/subagents)). Muse spawns child agents from skill instructions but doesn't publish a definition file format ([Muse extending](https://dev.meta.ai/docs/muse-code/extending)). The verifier must run in a *fresh* context that sees only your source claims and the draft. ai-job-search uses the same drafter/reviewer pattern, with a reviewer in a fresh context ([ai-job-search](https://github.com/MadsLorentzen/ai-job-search)).

### How one skill set reaches three CLIs

Three shared standards make portability cheap. The first is the **Agent Skills standard**. A `SKILL.md` with only `name` and `description` frontmatter (plus optional `license`, `compatibility`, `metadata`, `allowed-tools`) is valid everywhere. The spec asks you to keep each file under 500 lines ([agentskills.io spec](https://agentskills.io/specification)). Claude-only extensions such as `context: fork` are rejected outside Claude Code, so leave them out of the shared skills ([Claude Code skills](https://code.claude.com/docs/en/skills)). The second is **AGENTS.md**. Codex reads it natively ([Codex AGENTS.md](https://learn.chatgpt.com/codex/agent-configuration/agents-md)). Muse checks `AGENTS.md`, `CLAUDE.md`, `.agents/AGENTS.md` and `.claude/CLAUDE.md` at each directory level ([Muse configuration](https://dev.meta.ai/docs/muse-code/configuration)). For Claude Code, add a one-line `CLAUDE.md` that imports it. The third is **MCP over stdio**, which all three support, although each uses a different config file. Claude uses `.mcp.json` with `mcpServers` ([Claude MCP](https://code.claude.com/docs/en/mcp)). Codex uses TOML `[mcp_servers.<id>]` ([Codex config](https://learn.chatgpt.com/codex/config-file/config-reference)). Muse uses JSON `mcp_servers` in `~/.config/muse/settings.json` with `"schema_version": 1` ([Muse extending](https://dev.meta.ai/docs/muse-code/extending)).

Skill discovery paths also line up. Codex scans `.agents/skills` ([Codex skills](https://learn.chatgpt.com/docs/build-skills)). Muse scans `.agents/skills`, `.claude/skills` and `.codex/skills` ([Muse extending](https://dev.meta.ai/docs/muse-code/extending)). Claude Code needs `.claude/skills/` or a plugin's `skills/` folder ([Claude Code skills](https://code.claude.com/docs/en/skills)). One `.agents/skills/` tree plus a Claude plugin wrapper therefore covers all three. obra/superpowers already ships exactly this multi-host layout, including a `.muse-plugin` directory ([obra/superpowers](https://github.com/obra/superpowers)). The only per-host work left is writing an MCP config entry, which a `rojgaar setup --hosts claude,codex,muse` command can merge into each file idempotently.

### Why use the OS scheduler instead of the CLIs' built-in schedulers

Claude Code offers three schedulers, and none of them fits. Cloud scheduled tasks run on a fresh repo clone **with no access to local files**. Desktop local tasks need the app open and the machine awake. `/loop` tasks expire after 7 days ([Claude Code scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks)). A desktop task whose scheduled time passes while the laptop sleeps is skipped, with only one catch-up run on wake ([Desktop scheduled tasks](https://code.claude.com/docs/en/desktop-scheduled-tasks)). The OS schedulers handle this better. launchd "will start the job the next time the computer wakes up" and coalesces missed runs into one ([launchd docs](https://mynixos.com/home-manager/option/launchd.agents.%3Cname%3E.config.StartCalendarInterval)). systemd timers with `Persistent=true` fire missed runs after downtime ([systemd.timer](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html)). Windows needs `StartWhenAvailable`, which defaults to False ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-startwhenavailable)). Plain cron skips runs while the machine sleeps, so avoid it on laptops.

The wrapper `rojgaar run-daily` must be **idempotent**: running it twice in a day should be harmless. It takes a lock file, and it exits immediately if the `runs` table already has a success row for today. It fetches and upserts, then calls the host CLI headlessly with a time limit and a budget cap. It validates the JSON the host returns against a schema, and it writes the report. For Claude, use `claude -p "/rojgaar-scout:daily" --output-format json --permission-mode dontAsk --allowedTools "mcp__plugin_rojgaar-scout_rojgaar__*"`. `--json-schema` places schema-conforming output in a `structured_output` field, and `--max-budget-usd` caps spend ([Claude headless](https://code.claude.com/docs/en/headless)). For Codex, use `codex exec --json --output-schema … --sandbox workspace-write`; exec runs read-only by default ([Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode)). For Muse, use `muse exec --json --disable-approval --max-model-steps N`. Muse documents exit codes 0/1/2/130/143 ([Muse extending](https://dev.meta.ai/docs/muse-code/extending)). Never use `--yolo`, `danger-full-access` or `bypassPermissions` in the scheduled run. The Muse docs reserve `--yolo` for "a disposable CI container" ([Muse permissions](https://dev.meta.ai/docs/muse-code/permissions)).

## Two 60k-star rivals exist, so the differentiation must be sharp

Prior-art research protects you from building something that already exists. Here it shows a niche that is crowded at the top but has a clear opening. **career-ops** has about 69.1k stars and 13.1k forks. It routes subcommands (scan, pdf, cover, batch, tracker, apply) through markdown "modes", runs on nine-plus CLIs, ships 55+ provider modules covering Greenhouse, Ashby, Lever, Wellfound and company pages, and scores jobs holistically on a 1–5 scale ([career-ops](https://github.com/santifer/career-ops)). It is moving fast. v1.30.0 (Aug 27, 2026) added Vietnamese and Latin American boards, and later releases added outcome calibration and a hidden-Unicode cleaner ([newreleases.io](https://newreleases.io/project/github/santifer/career-ops/release/career-ops-v1.30.0)). Its README says it "never submits an application", yet it also ships a form-filling `/career-ops apply` ([career-ops](https://github.com/santifer/career-ops)). **ai-job-search** has about 60.5k stars, is Claude Code-first, and focuses on Danish portals. It checks claims against your profile, reports unsupported keywords as "gaps", and strips hidden text from postings. It openly admits that these defenses are "instruction-level, not a sandbox" ([ai-job-search](https://github.com/MadsLorentzen/ai-job-search)). One article headline put ai-job-search at "23K stars", so treat all star counts as approximate ([dailyaiworld](https://dailyaiworld.com/blogs/ai-job-search-claude-code-workflow-2026)).

The auto-apply generation is a warning, not a model. LinkedIn deleted the posts of AIHawk's author and restricted his account for "repeatedly sharing content that facilitates access to tools that automate activity on LinkedIn" ([Semafor](https://semafor.com/article/09/12/2024/linkedins-have-nots-and-have-bots)). AIHawk has since pivoted away from job applications ([AIHawk](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk)). During ApplyPilot's "1,000 applications in 2 days" run, its agent reset an expired LinkedIn password on its own and emailed resumes the user never asked it to send ([dev.to](https://dev.to/picklepixel/i-built-an-ai-agent-to-apply-to-1000-jobs-while-i-kept-building-things-3j64)). JobFunnel was archived in December 2025 because "job boards now use anti-automation and bot detection" ([JobFunnel](https://github.com/PaulMcInnis/JobFunnel)). On the other side is career-ops' own self-reported data for quality over volume. Of 740 evaluated listings, **68 applications (9.2%) led to 12 interview processes (17.6%)**, and tailoring gave an estimated 3x or better response rate. Mass-generated cover letters did worse ([career-ops blog](https://career-ops-docs-seven.vercel.app/blog/job-search-data-from-740-listings)).

| Dimension | career-ops | ai-job-search | Rojgaar-Scout (proposed) |
|---|---|---|---|
| Market / ATS seeds | Global boards | Danish portals | US only: San Francisco + Bay Area + remote-US; curated US company registry, alert-email ingest |
| Submission | "Never submits", but ships `apply` | Human applies | No submit, no form-fill tool exists at all |
| Truthfulness | Holistic score, legitimacy block | Claim check + gaps | Claim-ID ledger, deterministic checks, fresh-context verifier, diff review |
| Hosts | 9+ CLIs | Claude-first, AGENTS.md for others | Claude, Codex, Muse as first-class, CI-tested |
| Daily schedule | Not documented | Unclear | OS scheduler wrapper, idempotent |

There are four differentiators, and each one needs a reason it will hold up. **A focused US default** keeps the first version small and testable: one market, one CV convention, and a location filter tuned to San Francisco and the Bay Area. **Strict no-submit** is a product promise that is also a safety property. If no tool can submit, no prompt injection can make the agent submit. **The truthfulness layer** draws on the evidence in the CV section below. **Multi-CLI including Muse** is cheap, because Muse reads Claude and Codex conventions. Two cautions apply. career-ops releases quickly and can copy any adapter list, so your moat is the truthfulness checks, the evaluation harness and a well-curated Bay Area company registry, not a list of adapters. And licenses matter for reuse. AIHawk, ApplyPilot and OpenResume are **AGPL-3.0**, so don't copy their code into an MIT project. career-ops, ai-job-search, JobSpy, RenderCV and Reactive Resume are MIT, and Resume-Matcher is Apache-2.0 ([prior-art license survey: JobSpy](https://github.com/speedyapply/JobSpy); [RenderCV](https://github.com/rendercv/rendercv); [Resume-Matcher](https://github.com/srbhr/Resume-Matcher)).

## Market scope: US only

**Decision (Oct 29, 2026):** Rojgaar-Scout searches **US jobs only**, with **San Francisco, CA and the Bay Area, CA** as the default locations, plus remote-US. The choice is saved in `preferences.yaml` under `markets.us`, alongside the other job filters (see the file formats section).

- **Default sources** are the US-relevant safe tier: Greenhouse, Lever, Ashby and Workable boards from `companies.us.yaml`, plus Himalayas, Remotive, RemoteOK, We Work Remotely, HN "Who is hiring", The Muse and USAJOBS.
- **CV convention** is US only: Letter size, 1–2 pages, no photo or personal data.
- The `markets` block keeps room for other markets later without restructuring the file, but none ships now.

## Employer ATS APIs, not board scraping, carry coverage

The data strategy follows from one legal lesson. In the US, after *hiQ v. LinkedIn*, the Ninth Circuit held that scraping public, no-login pages likely does not violate the CFAA, because a public site has "erected no gates to lift or lower" ([Fenwick](https://www.fenwick.com/insights/publications/hiq-labs-scrapes-by-again-the-ninth-circuit-reaffirms-that-data-scraping-does-not-violate-the-cfaa-1)). **hiQ still lost on breach of contract**, partly through logged-in and fake accounts, and settled with a **$500,000 consent judgment** and a permanent injunction ([ZwillGen](https://www.zwillgen.com/alternative-data/hiq-v-linkedin-wrapped-up-web-scraping-lessons-learned/)). The lesson is that **the law tolerates reading public pages, while contracts and account bans are the real risk**. So use official public endpoints, never log in on the user's behalf, and never evade anti-bot measures.

The best fit is the public ATS endpoints. **Greenhouse** states that "Job Board data is publicly available, so authentication is not required for any GET endpoints" ([Greenhouse](https://developers.greenhouse.io/job-board.html)). **Lever's** README says "Published jobs are publicly viewable and may be scraped" ([Lever postings-api](https://github.com/lever/postings-api)). **Ashby** documents a public posting API that includes compensation ([Ashby](https://developers.ashbyhq.com/docs/public-job-posting-api)). These endpoints give you the employer's own full description, often with salary and workplace type, at negligible request volume. A single user scanning 50–300 companies once a day makes only hundreds of GET requests. Their main weakness is that **no ATS publishes its customer list**, so you must discover company "slugs" yourself. Start from a seed list of target companies, scan their careers pages for patterns like `jobs.lever.co/{slug}` and `{tenant}.wdN.myworkdayjobs.com`, then cache the results in `companies.yaml`. Workday matters for large US enterprises, many of which hire in the Bay Area. Its undocumented `cxs` JSON caps pages at 20 results, and asking for more silently returns an empty list ([dev.to Workday](https://dev.to/udaninn/workday-job-boards-have-a-json-api-too-its-just-better-hidden-23fl)). Wellfound has no API and sits behind Cloudflare. Its startups mostly run on Ashby, Greenhouse, Lever and Workable, so read those boards directly instead ([JobsPipe Wellfound](https://jobspipe.dev/blog/wellfound-api.md)).

| Tier | Sources | Why this tier |
|---|---|---|
| **Safe default** (on out of the box) | Greenhouse, Lever, Ashby, Workable widget, SmartRecruiters*, Himalayas, Remotive (≤4 fetches/day), RemoteOK, We Work Remotely RSS, Arbeitnow, Jobicy, HN "Who is hiring" via Algolia, The Muse, USAJOBS (US federal, free key) | Official or documented public endpoints; personal use fits their terms; attribution kept in reports |
| **Opt-in** (user enables, sees warning or supplies key) | Workday `cxs` (undocumented), Recruitee/Breezy, Adzuna (free key; ToS names "personal job search"), Jooble (keyed), SerpApi/JSearch Google Jobs (paid), JobSpy for Indeed (ToS/robots risk), job-alert email ingest (LinkedIn and Indeed alerts you already receive) | Works but is undocumented, keyed, paid, or legally grey |
| **Avoid** (no headless adapter ships) | LinkedIn, Glassdoor, Wellfound site, BambooHR widget | Explicit ToS bans, logins, Cloudflare, or unstable endpoints; ship at most a documented "you browse, agent reads" mode |

*SmartRecruiters sources conflict on whether a key is now needed ([SmartRecruiters docs](https://developers.smartrecruiters.com/docs/posting-api) vs [dev.to](https://dev.to/freshactors/how-to-scrape-smartrecruiters-jobs-data-with-python-no-api-key-needed-166g)). Verify this before enabling it by default.

Each tier placement has a cited reason. Adzuna's ToS explicitly permits "personal job search" with a free key, but requires credit to "The Adzuna API" for research use and prohibits multiple accounts ([Adzuna ToS](https://developer.adzuna.com/docs/terms_of_service)). Remotive asks for **at most about 4 fetches a day** and blocks above 2 requests per minute ([Remotive](https://github.com/remotive-com/remote-jobs-api)). RemoteOK puts a legal notice in the first array element of every response that requires a followed link back ([RemoteOK](https://remoteok.com/api)). Indeed has had no read API since its Publisher Program died, and its robots.txt disallows `/viewjob` for generic agents ([JobsPipe Indeed](https://jobspipe.dev/blog/indeed-publisher-api.md); [indeed.com/robots.txt](https://www.indeed.com/robots.txt)). JobSpy is MIT-licensed and maintained (v1.4.1, Oct 23, 2026) and ships LinkedIn, Indeed, Glassdoor and ZipRecruiter scrapers, but its own docs warn that all of them block aggressively ([PyPI python-jobspy](https://pypi.org/project/python-jobspy)). **Bundling a LinkedIn scraper in the default install of a public repo would invite takedown requests against the project itself**, which is why LinkedIn sits in Avoid even though the code exists. The cleanest channel for logged-in boards is parsing the job-alert emails the user already receives. This is an inference: no source assessed alert-email terms. It avoids scraping entirely, because those emails are first-party messages sent to the user.

The guardrails become code, not policy text. Send an honest User-Agent, for example `RojgaarScout/0.x (+repo URL; personal job search)`. USAJOBS requires your email address as the UA anyway ([USAJOBS](https://developer.usajobs.gov/general/quick-start)). Keep per-host concurrency at 1 with 1–3 s delays, honor `Retry-After` on 429/403 responses, respect robots.txt for HTML fetches, and never use CAPTCHA solvers, stealth browsers or rotating proxies. Store a `tos_url`, `tier` and `last_reviewed` field for each source in `sources.yaml`, and show the source attribution in every report. All of this data stays local and is never redistributed.

Normalization and dedup also run in code. Map every source onto a schema.org JobPosting-shaped record. Google's required properties (`title`, `description`, `datePosted`, `hiringOrganization`, `jobLocation`) and recommended ones (`baseSalary` with `unitText`, `employmentType`, `jobLocationType: TELECOMMUTE`, `applicantLocationRequirements`) give you a vocabulary you don't have to invent ([Google JobPosting](https://developers.google.com/search/docs/appearance/structured-data/job-posting)). Watch the date traps. Greenhouse's list `updated_at` is not a posted date ([Greenhouse](https://developers.greenhouse.io/job-board.html)), and Workday's `postedOn` is a phrase like "Posted 3 Days Ago" ([dev.to Workday](https://dev.to/udaninn/workday-job-boards-have-a-json-api-too-its-just-better-hidden-23fl)). Record your own `first_seen` timestamp, because that is the only date you can trust. Deduplicate with a cascade of exact keys: first ATS type plus job ID, then the canonical apply URL with tracking parameters stripped, then normalized `company|title|city-or-remote`. **Do not merge on fuzzy title similarity.** One practitioner found that 92% similarity merged Dubai with Abu Dhabi, and 95% merged "Analyst I" with "Analyst II" ([dev.to dedup](https://dev.to/get_anything/the-same-job-is-posted-on-three-boards-heres-how-to-deduplicate-job-listings-properly-2862)). For reposts with lightly edited descriptions, run MinHash-LSH on description shingles at a threshold of about 0.8 within the same company, then confirm with exact Jaccard similarity ([Kashnitsky](https://yorko.github.io/2023/practical-near-dup-detection)).

## A four-stage funnel spends LLM tokens only on 30–60 jobs

Ranking is a funnel because each stage is about ten times more expensive than the one before. Expensive judgment should only see what cheap filters let through. **Stage 1 (hard filters, free)** drops jobs that are already seen, blacklisted, outside your allowed locations or remote modes, or more than about 30 days old. The key rule is **fail-open on unknowns**. Many good postings omit salary or visa information. Drop a job for sponsorship only if it explicitly says "no sponsorship" *and* you need it, and drop it for salary only if the stated maximum is below your floor. Allow ±1 seniority level. These rules come from the matching research's recommendations. **Stage 2 (cheap scoring, local CPU)** fuses two retrieval methods. The first is BM25 over title and skills, which SQLite's FTS5 provides for free. The second is cosine similarity from a small local embedding model. fastembed runs ONNX on CPU and defaults to `bge-small-en-v1.5`, with Qwen3-Embedding, bge-m3 and multilingual-e5 available ([fastembed](https://docs.rs/crate/fastembed/5.17.0/source/README.md)). Qwen3-Embedding-0.6B is Apache-2.0, has a 32K context and supports Matryoshka truncation ([HF model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)). Fuse the two rankings with **Reciprocal Rank Fusion**: score = Σ 1/(60 + rank). It needs no score calibration ([BigData Boutique](https://bigdataboutique.com/blog/reciprocal-rank-fusion-how-it-works-and-when-to-use-it)). sqlite-vec keeps the vectors in the same SQLite file as everything else ([sqlite-vec](https://github.com/asg017/sqlite-vec)). At this scale, though, brute-force cosine in numpy is just as fast.

One trick is worth learning here. Your CV and a job description use different vocabularies, so match job descriptions against job descriptions. Have the LLM write one to three "ideal job descriptions" from your profile once, embed them, and use them as search queries. This is the job-side version of GIRL's generated-JD representation, which raised AUC from 0.6258 to 0.6436 ([GIRL](https://arxiv.org/html/2307.02157v1)), and of ConFit v2's hypothetical-resume trick ([ConFit v2](https://arxiv.org/html/2502.12361v1)). It's an extrapolation: neither paper tested a single-user setup. Run a deterministic **ghost/scam risk score** in parallel and show it as a badge instead of silently dropping jobs. Signals include repeated reposts, age over 45 days, "talent pool" wording, contact via WhatsApp or Telegram, and fees. Greenhouse's analysis put ghost jobs at 18–22% of postings, though its methodology is unpublished ([FOX/Greenhouse](https://www.fox29.com/news/ghost-jobs-greenhouse-analysis)). FTC-reported job-scam losses more than tripled from 2020 to 2023 ([IBJ/AP](https://www.ibj.com/articles/job-scams-are-on-the-rise-and-more-people-are-falling-for-them-ftc-says)).

**Stage 3 (LLM rubric judge on the top 30–60)** is where the host CLI earns its keep. It should not ask the model for "a score out of 100". Instead it asks for **categorical per-dimension scores** with evidence, and code computes the final number. LinkedIn's LANTERN uses Low/Medium/High fit with line-by-line requirement explanations and greedy decoding. Its main failure mode was rationales the profile did not support ([LANTERN](https://arxiv.org/html/2510.05490v1)). The proposed rubric scores five dimensions 0–3 each: title alignment, must-have skill coverage (each requirement marked met, partial or missing, with the profile item that satisfies it), seniority/YOE fit, logistics, and preference fit. It then returns a verdict (strong, good, stretch or poor) plus `dealbreaker_hit`, ≤3 reasons, ≤3 gaps and `risk_flags`. Weights live in `preferences.yaml`, so you can see and change why job A beat job B. Batch 5–10 compact job summaries per call behind a constant profile prefix, so the host can reuse its prompt cache. LLM judges have a **systematic position bias**. Position consistency ranged from about 0.57 to 0.82 across judges ([Shi et al.](https://arxiv.org/html/2406.07791v5)). A 2026 study of 21 judges found that high test-retest stability can coexist with position bias above 0.10 ([arXiv 2606.19544](https://arxiv.org/pdf/2606.19544)). So shuffle input order, and for an optional listwise pass over the top 20, run it twice with reversed order and average the ranks. Be modest about how much the LLM adds. In ConFit v3, prompted frontier models improved on an embedding retriever on one dataset, but GPT-5 prompting did *worse* than the retriever on another (74.81 vs 80.28 nDCG@10) ([ConFit v3](https://arxiv.org/pdf/2605.09760)). This is why you need your own evaluation set.

**Stage 4 is feedback.** Record thumbs up/down with a reason tag ("too senior", "wrong domain", "location"), whether you applied, and the outcome. Once a week, an LLM reads the recent feedback and *proposes* diffs to `preferences.yaml` and a `preference_memory.md` file, and you approve them. Use the jobs that scored high but that you rejected as few-shot negatives, because these "runner-up" examples are the most informative. ConFit v2's runner-up mining rests on the same insight ([ConFit v2](https://arxiv.org/html/2502.12361v1)). For **evaluation**, label about 150 postings from your own feed on a 0–3 scale: 50 from the stage-3 top, 50 from the middle of stage 2, and 50 random. Measure the false-drop rate of stage 1 (it should be close to zero for label ≥2), recall@K for stage 2, NDCG@10 and precision@10 for stage 3, and Cohen's κ between the judge and your labels rather than raw agreement, since raw agreement overstated reliability by 33.8–41.2 points in one study ([arXiv 2606.19544](https://arxiv.org/pdf/2606.19544)). Freeze this as `rojgaar eval` and run it whenever a prompt or model changes.

## Truthfulness must be enforced in code, because prompts cut fabrication only in half

This section is your strongest differentiator, and the evidence for it is recent and stark. A July 2026 study generated tailored resumes with claude-sonnet-4-6 across 180 runs. **With no guardrail, 96.7% of outputs contained at least one fabrication.** A strict factual-rule prompt cut findings per output by 86% but **still left 50% of outputs with a fabrication**. A human checkpoint alone left 75% ([arXiv 2608.26171](https://arxiv.org/pdf/2608.26171)). A newer model with no guardrail still fabricated in 90% of outputs. Reviewers mostly missed *dropped qualifiers* (for example, "co-led" becoming "led") and *plausible new claims*. Risk rose with the distance between the candidate's background and the job, so career changers face the most danger. The authors concluded that "prompt-level mitigation alone therefore does not yield a deployable safety property." A second paper used layered defenses: timeline checks, deterministic detection of borrowed terminology, structural rules, prompt grounding and a separate evaluator. These cut hallucinations from **2.48–5.36 per resume to 0.04–0.24** ([arXiv 2607.01457](https://arxiv.org/abs/2607.01457)). Both papers are unreviewed preprints built on synthetic data. Even so, the direction is clear: **layers beat any single defense.**

The design follows from that. Keep one **experience bank** (`profile/bank.yaml`) where every atomic claim has a stable ID, its text, its metrics with units, its dates, skills, qualifiers, optional evidence, and `verified_by_user: true`. Tailoring may only *select, reorder and rephrase* claims, and every output bullet must carry a `src:` claim ID. Then code checks the result:

| Check | What it catches |
|---|---|
| Every bullet has a valid `src` ID | Invented bullets |
| Every number and date in the output appears in the cited claim | Inflated metrics |
| Every skill term exists somewhere in the bank | Absorbed JD "trap" skills (47% baseline in the study) |
| Qualifier words are preserved | "Co-led" quietly becoming "led" |
| The timeline is consistent | Technologies appearing before they existed |

After the code checks, a **verifier subagent in a fresh context** sees only the source claims and the draft. Finally, a `review.md` shows each bullet next to its source with qualifier changes highlighted, because diff-aided review targets exactly what humans miss.

ATS myths need correcting too, so the tool doesn't optimize for fiction. The "75% auto-rejected" claim lacks support. In a small vendor survey (n=25), 92% of recruiters said their systems don't auto-reject on formatting or keywords; the filters they do use cover work authorization, minimum qualifications and location ([IT Brief](https://itbrief.co.uk/story/study-reveals-ats-rarely-auto-rejects-cvs-debunks-75-myth)). Parsing still matters. Generic parsers read text in file order, so two-column layouts interleave, and tables in PDFs parsed worse in one author's test ([ATS Verification](https://atsverification.com/blog/greenhouse-vs-workday-ats-parsing/)). Default to a single-column, text-based PDF with standard headings, and add a **parse-back test** (extract the text with pdftotext and confirm every bullet survives). **Never offer white-text keywords or hidden prompt injections.** Greenhouse reports that 22% of US hiring managers have caught hidden injections ([Greenhouse](https://www.greenhouse.com/newsroom/an-ai-trust-crisis-70-of-hiring-managers-trust-ai-to-make-faster-and-better-hiring-decisions-only-8-of-job-seekers-call-it-fair)).

Render with **RenderCV**. It is MIT-licensed, installs with pip, takes YAML input with a JSON Schema, uses Typst so no LaTeX install is needed, and ships an official agent skill ([RenderCV](https://github.com/rendercv/rendercv)). Its 2.8 release is from March 2026 ([PyPI](https://pypi.org/project/rendercv/)). Produce DOCX with `pandoc --reference-doc`, because some portals want editable files. The JSON Resume reference CLI was archived in June 2026, and `resumed` is now the recommended client ([resume-cli](https://github.com/jsonresume/resume-cli)). So use JSON Resume only as an export format, not as your source of truth.

CVs follow US conventions: Letter size, one page for early-career and up to two for experienced candidates, no photo, date of birth or other personal data, and GPA only if recent and strong. A `locale` field stays in the schema (default `us`) so other conventions could be added later without a format change.

Cover letters should be short, at 250–350 words: one company-specific hook *that you confirm*, two evidence paragraphs tied to claim IDs, and a logistics close covering start date or relocation. The reason comes from Tilburg economists. Recruiters rated AI-assisted letters higher, **but that did not translate into more interview invitations**, because AI improved the standard parts and not the motivation section recruiters value most ([IO+](https://ioplus.nl/en/posts/ai-improves-cover-letters-not-hiring-chances)). So `motivation` is a field you must write or confirm, and a lint step bans "passionate", "leverage", "delve" and similar filler.

For privacy, keep name, phone, email, address and current salary in `profile/pii.yaml`, which the model never sees. Prompts use `{{NAME}}`-style placeholders that the renderer fills locally. The two 2026 papers built their benchmarks without real identities, which shows the tailoring task works with pseudonymized input ([arXiv 2608.26171](https://arxiv.org/pdf/2608.26171)).

## Repo layout and file formats keep your data separate from the tool

The guiding idea is that **the tool lives in a git repo anyone can clone, and your data lives in `~/RojgaarScout/`, which never ships**. Claude plugins reinforce this split. `${CLAUDE_PLUGIN_ROOT}` changes on update, so state must not live there, while `${CLAUDE_PLUGIN_DATA}` persists ([Claude plugin reference](https://code.claude.com/docs/en/plugins-reference)). Ship the core as a Python package runnable with `uvx rojgaar-scout mcp`, so a Claude-only user can install with `/plugin marketplace add` and nothing else. Codex can read the same `.claude-plugin/marketplace.json` as a legacy-compatible marketplace ([Codex plugins](https://developers.openai.com/codex/plugins/build.md)).

```
Rojgaar-Scout-Agent/                     # MIT, public
├── LICENSE  pyproject.toml  README.md
├── AGENTS.md                            # canonical instructions (Codex, Muse read natively)
├── CLAUDE.md                            # one line: @AGENTS.md
├── src/rojgaar/
│   ├── cli.py                           # init | fetch | rank-candidates | report | draft | eval | doctor | setup | schedule | run-daily
│   ├── mcp_server.py                    # stdio MCP: narrow typed tools only
│   ├── sources/                         # greenhouse, lever, ashby, workable, smartrecruiters, workday,
│   │                                    # himalayas, remotive, remoteok, wwr, arbeitnow, jobicy, hn, usajobs,
│   │                                    # themuse, adzuna*, jooble*, jobspy_optin*, jsonld, alert_email*
│   ├── sanitize.py  normalize.py  dedup.py  filters.py  risk.py
│   ├── retrieve.py                      # FTS5 BM25 + fastembed + RRF
│   ├── rubric.py                        # judge schema + weighted score in code
│   ├── truth/                           # claim checks, qualifier/number/skill/timeline checks, phrase lint
│   ├── render/                          # bank → RenderCV YAML → PDF; pandoc DOCX; parse-back
│   ├── store.py                         # SQLite (+ sqlite-vec)
│   └── schedule.py                      # launchd plist / systemd unit+timer / schtasks XML
├── schemas/                             # job, judge_output, draft_output, bank, preferences (JSON Schema)
├── config/companies.us.yaml  metros.yaml  sources.yaml   # US company registry; Bay Area alias table; tier, tos_url, last_reviewed per source
├── .agents/skills/rojgaar-{daily,rank,tailor,verify,setup,feedback}/SKILL.md   # standard fields only
├── plugins/claude/.claude-plugin/plugin.json  agents/{ranker,writer,verifier}.md  .mcp.json
├── .claude-plugin/marketplace.json      # also read by Codex
├── .codex/agents/{ranker,writer,verifier}.toml
├── templates/  eval/  tests/fixtures/   # recorded API responses, planted-fabrication drafts
└── .github/workflows/ci.yml             # pytest, claude plugin validate --strict, skills-ref validate

~/RojgaarScout/                          # private, never committed upstream (optionally its own git repo)
├── profile/bank.yaml  preferences.yaml  pii.yaml  preference_memory.md  profile.json (derived)
├── state/rojgaar.db  run.lock  logs/2026-10-29.jsonl
├── reports/2026-10-29.md
└── applications/2026-10-29_acme_backend-sde/
    ├── jd.md  fit-report.md  cv.yaml  cv.pdf  cv.docx
    ├── cover-letter.md  cover-letter.pdf  review.md  status.json
```

(* = opt-in)

The research produced two candidate "profile" formats, and they need reconciling. The ranking research recommends JSON Resume as `profile.json` ([JSON Resume schema](https://docs.jsonresume.org/schema)). The CV research says JSON Resume lacks claim IDs, qualifiers and evidence fields. The resolution: **`bank.yaml` is the single source of truth, and `profile.json` is generated from it** as a compact JSON Resume view for the judge prompt and for export. Keep the raw CV text alongside it as well. JobRecoGPT found that purely structured matching lost information and scored lowest (84.00% vs 89.66% for an unguided LLM) ([JobRecoGPT](https://arxiv.org/html/2309.11805v1)). Abridged examples of the key formats:

```yaml
# profile/bank.yaml  (source of truth; every claim user-verified)
schema_version: 1
roles:
  - id: exp.acme
    org: Acme Fintech Inc
    title: Senior Backend Engineer
    start: 2022-04
    end: null            # current
    location: San Francisco, CA
    claims:
      - id: exp.acme.b3
        text: Co-led migration of payments ledger from MySQL to PostgreSQL
        metrics: [{value: 40, unit: "% p99 latency reduction"}]
        skills: [PostgreSQL, MySQL, Go]
        qualifiers: [co-led, team of 4]
        evidence: "internal design doc; ask manager"
        verified_by_user: true
        alt_phrasings: ["Co-led a 4-person ledger migration to PostgreSQL"]
education:
  - id: edu.bs
    degree: B.S. Computer Science
    score: {value: 3.7, scale: 4.0}      # GPA; omit if not recent/strong
```

```yaml
# profile/preferences.yaml  (abridged; full commented version: preferences.example.yaml)
schema_version: 1
markets:                                  # US only
  us:
    enabled: true
    locations: ["San Francisco, CA", "Bay Area, CA", remote-US]   # default
    work_authorization: citizen
    salary_floor: {amount: 150000, currency: USD, period: year}
    cv_locale: us
    sources: [greenhouse, lever, ashby, workable, himalayas, remotive,
              remoteok, weworkremotely, hn_whos_hiring, themuse, usajobs]
    company_registry: config/companies.us.yaml
include_remote_global: true
filters:                                  # fail-open on unknowns
  remote_modes: [remote, hybrid, onsite]
  employment_types: [full_time]
  seniority: [senior, staff]              # ±1 allowed
  max_age_days: 30
  exclude_companies: []
  exclude_keywords: [unpaid, "commission only"]
  exclude_title_words: [intern, manager]
ranking:                                  # soft preferences: score, never drop
  target_titles: [Backend Engineer, Platform Engineer, Senior Software Engineer]
  core_skills: {Go: 3, PostgreSQL: 3, Kubernetes: 2}
  preferred_domains: [fintech, devtools]
  weights: {title: 2, must_have: 3, seniority: 2, logistics: 2, preference: 1}
report: {top_n: 15, drafts_per_day: 5, new_only: true}
```

Location, work authorization, salary floor, sources and company registry live under `markets.us`. Metro names like "Bay Area, CA" need a small alias table in `filters.py` (`config/metros.yaml`) that expands them to the cities postings actually use (San Jose, Oakland, Palo Alto, Mountain View, Sunnyvale, Santa Clara, Fremont, Redwood City, San Mateo and so on), because few postings write "Bay Area" literally.

```json
// applications/<job>/status.json
{"job_uid": "greenhouse:acme:4471203", "state": "draft",
 "history": [{"state": "draft", "at": "2026-10-29T07:31:00+05:30", "by": "rojgaar"}],
 "verdict": "strong", "score": 0.82, "risk_flags": [], "submitted_by_user": null}
```

Every CV bullet in `cv.yaml` carries a trailing `# src: exp.acme.b3` comment. `review.md` lists each bullet beside its source text, with qualifier changes and verifier findings.

## The roadmap front-loads the riskiest unknowns

The ordering rule is **validate what could kill the project before building what is merely work**. Three things could kill it: headless authentication under a scheduler, the sandbox's network behavior, and Muse's undocumented formats. All three are tested in Phase 0. Effort figures are rough planning estimates for one developer working part-time (about 10–15 hours a week). They are not sourced numbers.

| Phase | Concrete tasks | Acceptance criteria | Rough effort |
|---|---|---|---|
| **0. Setup & spikes** | Repo, MIT license, `uv` package skeleton, CI; spike `claude -p`, `codex exec`, `muse exec` each calling a toy stdio MCP tool that does an HTTPS GET, launched from launchd *and* a systemd user timer; write `docs/decisions/` notes | For each host × OS: documented pass/fail for auth without a GUI session and for network from inside the MCP server; a chosen fallback (API key env var) where it fails | 1 week |
| **1. Deterministic core** | Greenhouse, Lever, Ashby, Workable, Himalayas, Remotive, RemoteOK, WWR, HN adapters with recorded-fixture tests; JobPosting-shaped normalizer; SQLite store with `first_seen`/`last_seen`; exact-key dedup + MinHash; hard filters; `markets.us` block in `preferences.yaml` with SF/Bay Area locations and `metros.yaml` alias table; slug discovery into `companies.us.yaml` (seed 50 US companies you'd apply to); `rojgaar fetch` and `rojgaar report --no-llm`; per-host rate limiting, robots, UA | A second run on the same day inserts 0 duplicates; `report --no-llm` lists only new jobs since yesterday with source attribution; no adapter exceeds 1 concurrent request per host; tests pass offline | 2–3 weeks |
| **2. Profile + ranking** | `rojgaar init` (CV → draft bank via LLM, then interactive review; preference interview); BM25 + fastembed + RRF; risk score; MCP server tools; `rojgaar-rank` skill with judge JSON schema; weighted score in code; label 150 jobs; `rojgaar eval` | Stage 1 drops 0 jobs you labeled ≥2; stage 2 recall@40 for label ≥2 meets a target you set after a baseline run; judge output 100% schema-valid; κ reported; order-swap test runs | 2–3 weeks |
| **3. Drafting + truthfulness** | `rojgaar-tailor` and `rojgaar-verify` skills; writer/verifier subagents; deterministic checks (src ID, numbers, skills, qualifiers, timeline); phrase lint; RenderCV PDF + pandoc DOCX; parse-back; US `locale`; fit-report with ✔/≈/✘ gaps; `review.md` diff; PII placeholders | A fixture set of drafts with planted fabrications (invented metric, dropped "co-", JD trap skill, anachronism) is caught 100% by code checks; every shipped bullet has a src ID; parse-back recovers every bullet; `pii.yaml` contents never appear in any logged prompt | 2–3 weeks |
| **4. Daily automation + multi-CLI** | `run-daily` wrapper (lock, idempotency, timeout, budget cap, schema validation, JSONL log, desktop notification); `rojgaar schedule install` for macOS/Linux/Windows; Claude plugin + marketplace; Codex TOML agents + config writer; Muse `mcp_servers` writer; `rojgaar doctor` | 7 consecutive unattended daily runs on your machine, including one across a sleep; same daily skill produces a valid report under each of the three hosts; `claude plugin validate --strict` and `skills-ref validate` pass in CI | 2 weeks |
| **5. Polish & community** | opt-in tier (Adzuna, Jooble, JobSpy Indeed with warning, alert-email parser); feedback capture + weekly preference-diff proposals; outcome tracking; adapter contributor guide + template; Gemini/OpenCode shims; PyPI release; docs on ToS posture and provider data flow | A new contributor adds an ATS adapter using only the guide; feedback loop produces an approved `preferences.yaml` diff; `sources.yaml` shows tier and ToS link for every source | 2+ weeks, ongoing |

### Your first week

| Day | Do this | You're done when |
|---|---|---|
| 1 | Create the GitHub repo with MIT LICENSE, `pyproject.toml` (Python ≥3.11), `src/rojgaar/__init__.py`, `AGENTS.md` stub, `CLAUDE.md` containing `@AGENTS.md`, and a CI job running `pytest` | CI is green on an empty test |
| 2 | Write Greenhouse, Lever and Ashby fetchers for 5 companies you'd actually apply to; save raw responses as test fixtures | `python -m rojgaar fetch` prints normalized titles, locations and URLs from all three |
| 3 | Create the SQLite schema (`jobs`, `sources`, `runs`) with `first_seen`/`last_seen` and the exact-key dedup | Running fetch twice reports "0 new" the second time |
| 4 | **The critical spike.** Build a 20-line stdio MCP server with one tool that fetches a Greenhouse board. Call it from `claude -p`, `codex exec` and `muse exec` interactively, then from a systemd user timer or launchd agent | A written table of what worked, what needed an API key, and whether Codex/Muse blocked the MCP server's network |
| 5 | Hand-write 15–20 claims of your own into `bank.yaml` with IDs and qualifiers, plus a first `preferences.yaml` | Files validate against a draft JSON Schema |
| 6 | Add `get_shortlist` and `get_profile` MCP tools; write a minimal `rojgaar-rank` SKILL.md; run it manually in Claude Code | You get JSON verdicts with reasons for 10 real jobs |
| 7 | Read the verdicts critically, label them yourself, and note where the judge was wrong | A `docs/decisions/0001-week1.md` recording surprises, and an updated Phase 1 task list |

## Six risks could invalidate parts of this plan

**Subscription terms for automated CLI use** are the risk that most needs a clear answer. Resume-Matcher warns that driving a consumer Claude subscription through the CLI from an app "may violate Anthropic's terms" ([Resume-Matcher](https://github.com/srbhr/Resume-Matcher)). Anthropic's support article confirms that signed-in `claude -p` "still draws from subscription limits". It also notes that Max and Team plans now include monthly API credits usable with an API key from a linked Console org ([Claude Support](https://support.claude.com/en/articles/15036540)). The billing behavior is documented. Whether a scheduled job that a third-party tool starts on your own machine is within the consumer terms is **not** settled by anything in this research. Read the current consumer terms for all three providers. Make the API-key path a first-class option, and state your position in the README.

**Headless authentication under launchd/systemd is untested.** Login-keychain and OAuth credentials may not be available to a job that runs without a GUI session. Claude's `--bare` mode never reads OAuth and requires `ANTHROPIC_API_KEY` ([Claude headless](https://code.claude.com/docs/en/headless)). Codex recommends `CODEX_API_KEY` for automation ([Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode)), and Muse supports `META_API_KEY` for CI ([Muse docs](https://dev.meta.ai/docs/muse-code/)). This is why the Phase 0 spike exists. **Codex MCP sandboxing is uncertain.** The plan assumes MCP stdio servers run outside the shell sandbox and so can reach the network. The research couldn't confirm this, because the Codex sandboxing page failed to load. The documented fallback is `-c sandbox_workspace_write.network_access=true` ([Codex security](https://learn.chatgpt.com/docs/agent-approvals-security.md)). A cleaner alternative avoids the question entirely: `run-daily` does all fetching *before* it invokes any host, so the MCP server only reads SQLite.

**Muse's formats are partly undocumented.** It is closed source ([Layer3Labs](https://www.layer3labs.io/guides/muse-code-explained)). Its subagent definition format and official plugin manifest aren't published. A third-party article uses `mcpServers` where the official docs say `mcp_servers` ([withone.ai](https://www.withone.ai/blog/muse-code-skills-not-mcp/md) vs [Muse extending](https://dev.meta.ai/docs/muse-code/extending)). And committed project memory loads even in untrusted workspaces ([Muse configuration](https://dev.meta.ai/docs/muse-code/configuration)). Rely only on AGENTS.md, `.agents/skills` and the documented `mcp_servers` key, and pin a tested Muse version in CI.

**LinkedIn and Indeed terms** limit coverage by design, and enforcement hits the user's real account first. **Competitive velocity**: career-ops ships fast and could copy any feature, so invest in the parts that are hard to copy, namely the truthfulness checks, the evaluation harness and the curated company registry. **Provider data retention**: the host CLI sends prompt content to a cloud model, and the retention terms of the three providers weren't researched. Hence the PII placeholder design, and an optional local-model path for strict users.

Several factual questions remain open:

- Does SmartRecruiters' public postings endpoint now need a key?
- Does Lever's JSON include `createdAt`?
- Which ATSs dominate Bay Area startup and enterprise hiring? This decides your Phase 1 adapter order.
- Does Claude Code now read AGENTS.md natively?
- Does `--permission-mode dontAsk` combine correctly with plugin MCP wildcards in `--allowedTools`?

Treat each one as a ticket with a 30-minute verification task, not as a blocker.

## How this research was done

It's worth seeing the method, because you'll reuse it. The question "how should I build this?" was too big to research as one blob, so it was **split along the pipeline's own seams into five independent streams**, each run in parallel by a separate researcher. **Prior art** asked what already exists and where the gap is. **CLI integration** asked how Claude Code, Codex and Muse load skills, agents, MCP servers and headless runs, and how to schedule them. **Job data sources** asked what can be fetched legally and reliably. **Matching and ranking** asked how to turn thousands of postings into a defensible top 10. **CV generation** asked how to draft truthfully and in an ATS-safe way. The split works because each stream can be answered without the others' results. That independence is what makes parallel work possible. The synthesis step (this report) then resolves the places where streams touch, such as the profile.json-versus-bank conflict and the Codex network question that bears on both architecture and data sourcing.

Source choice followed a simple hierarchy. **Primary documentation first**: official API docs (Greenhouse, Lever, Ashby, Adzuna's ToS), official CLI docs (code.claude.com, learn.chatgpt.com, dev.meta.ai), legal texts (court rulings, site terms), and the repos themselves. **Research papers next** (arXiv for ranking and fabrication), with the note that several are unreviewed 2026 preprints on synthetic data. **Vendor and secondary sources last, and flagged.** Jobscan, Enhancv, Greenhouse, JobsPipe and TheirStack all sell something related to their claims, so their figures appear here only with that caveat. Claims with no source URL were dropped. Where sources conflicted (star counts, SmartRecruiters auth, Muse's MCP key name), the conflict is stated rather than resolved by guesswork. Each stream also recorded its **gaps**: GitHub's API was blocked, so star counts and recency are approximate; LinkedIn's legal pages couldn't be fetched; and no study covers single-user job ranking directly. Those gaps became the open-questions list above. The repeatable lesson: **decompose by independent sub-questions, prefer primary sources, label vendor bias, and turn every unknown into a cheap verification task.**

## Conclusion

The research changes what the hard part of this project is. It isn't the "multi-agent" piece. The host CLIs already supply subagents, skills and headless modes, and they converge on shared standards that make three-host support nearly free. The hard parts are mundane: building a registry of which Bay Area employers use which ATS, so that coverage comes from sources you're allowed to read, and designing a truthfulness layer strong enough that a recruiter could trust a CV your tool helped write. Both are moats precisely because they are tedious. A competitor can copy a scraper in an afternoon, but not a curated, verified company registry or a fabrication test suite.

The second takeaway is about evidence. Two 2026 studies show that prompting alone halves fabrication at best, and the Tilburg result shows that AI polish doesn't buy interviews. So the product's value lies less in *writing* and more in *selecting, verifying and refusing*: choosing the five jobs worth your evening, proving every bullet traces to something you did, and never pressing Submit. Measure that with your own labeled evaluation set from week two onward. That will tell you what is working sooner than adding more sources or more agents.
