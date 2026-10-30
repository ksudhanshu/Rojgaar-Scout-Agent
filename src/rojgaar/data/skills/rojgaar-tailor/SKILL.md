---
name: rojgaar-tailor
description: Draft a tailored, truthful CV and cover letter for one job using only verified claims from the user's experience bank. Use when drafting application materials in Rojgaar-Scout.
---

# Tailor a CV and cover letter (truthfully)

Inputs: `get_job(uid)` and `get_bank()`.

Your only allowed moves are **select, reorder, rephrase**. Never add a fact, number, skill, title,
employer or date that is not in the cited claims.

## Draft format (pass to `check_draft`, then `save_application_draft`)

```json
{
  "job_uid": "<uid>",
  "summary": {"text": "...", "src": ["exp.acme.b1", "exp.acme.b2"]},
  "sections": [
    {"title": "Experience — Senior Backend Engineer, Acme Fintech Inc (2022–present)",
     "bullets": [{"text": "...", "src": ["exp.acme.b1"]}]}
  ],
  "skills": ["Python", "PostgreSQL"],
  "cover_letter": {
    "motivation": null,
    "paragraphs": [{"text": "...", "src": ["exp.acme.b2"]}],
    "closing": "I can start in [START DATE] and am based in {{LOCATION}}."
  }
}
```

Rules:
- Every bullet and cover-letter paragraph cites at least one `src` claim id.
- Keep qualifiers: "co-led" stays "co-led", "helped" stays "helped", "team of 4" is not "the team".
- Numbers must appear in the cited claim exactly (40% stays 40%).
- `skills` lists only skills in the bank. Missing requirements are gaps, never additions.
- Use the job's vocabulary only where the claim genuinely supports it.
- Leave `motivation` as `null`: the user writes or confirms it. Use `{{NAME}}`-style placeholders for
  personal details; never invent contact information.
- Cover letter: 250–350 words, no stock phrases ("passionate", "leverage", "synergy", "dynamic team").
- US CV conventions: 1–2 pages, single column, standard headings, no photo or date of birth.
