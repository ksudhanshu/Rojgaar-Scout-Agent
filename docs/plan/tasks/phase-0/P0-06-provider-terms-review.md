# P0-06 · Review provider terms for scheduled use

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 0 · Setup & spikes | 0.5 day | — | todo |

## Why
Signed-in `claude -p` draws from subscription limits, but whether a scheduled job started by a third-party tool is within consumer terms is not settled by the research. One project (Resume-Matcher) warns it may not be. A public repo should state a clear position rather than leave users exposed.

## What to do
- [ ] Read the current consumer terms and usage policies for Anthropic (Claude), OpenAI (ChatGPT/Codex) and Meta (Muse).
- [ ] Note what each says about automated or scripted use, headless use and third-party wrappers.
- [ ] Decide the default: subscription login, API key, or user's choice with a clear note.
- [ ] Draft the README section "Which login should I use?".

## Done when
- `docs/decisions/0003-provider-terms.md` lists each provider's relevant clause (with link and date read) and the project's position.
- The API-key path is documented as a first-class option.

## Notes
This is not legal advice; record what the terms say and let users decide.
