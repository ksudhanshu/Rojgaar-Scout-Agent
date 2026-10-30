# P1-08 · Sanitizer

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 1 · Deterministic core | 0.5 day | P1-01 | todo |

## Why
Job descriptions are untrusted web text that will later reach an LLM. Hidden text and invisible characters are the usual carriers for prompt injection, so strip them before anything else sees the job.

## What to do
- [ ] `src/rojgaar/sanitize.py`: HTML → clean text (keep lists and headings); drop `display:none`/`visibility:hidden`/zero-size/same-colour text; strip zero-width and bidi-control Unicode; collapse whitespace; cap length.
- [ ] Flag (don't silently drop) jobs where sanitizing removed a lot of hidden text: `risk_flags: ["hidden_text"]`.

## Done when
- Tests with planted hidden instructions ("ignore previous instructions…" in hidden spans and zero-width text) show the text removed and the flag set.
