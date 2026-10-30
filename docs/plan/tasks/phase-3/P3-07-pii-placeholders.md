# P3-07 · PII placeholders

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 3 · Drafting + truthfulness | 1 day | P3-04 | todo |

## Why
The host CLI sends prompts to a cloud model. Your name, phone, email and address don't help tailoring, so they never need to leave your machine.

## What to do
- [ ] `profile/pii.yaml`: name, email, phone, location line, links, current salary.
- [ ] Prompts and drafts use placeholders (`NAME`, `EMAIL`, `PHONE`, …); the renderer substitutes them locally at the last step.
- [ ] MCP tools never return `pii.yaml`.
- [ ] Test: log every prompt during a run and scan for any `pii.yaml` value.

## Done when
- No `pii.yaml` value appears in any logged prompt; rendered PDFs contain the real details.
