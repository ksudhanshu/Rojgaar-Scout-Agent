---
name: rojgaar-verify
description: Independently verify a Rojgaar-Scout draft against its cited source claims and flag anything that says more than the sources support. Use after drafting and before saving.
---

# Verify a draft (fresh eyes)

If your host supports subagents, run this as a separate agent that sees **only** the cited claims
(`get_bank`) and the draft — not the job description and not the writer's reasoning. A reviewer that
saw the writer's reasoning tends to agree with it.

For every bullet and cover-letter paragraph, compare it with the claims in its `src` list and flag:

- **Overstatement:** stronger verbs or scope than the claim ("co-led" → "led", "helped" → "drove").
- **New facts:** numbers, tools, team sizes, outcomes, employers or dates not in the claims.
- **Merged claims** that imply something neither claim says on its own.
- **Missing qualifiers** such as "team of 4", "part of", "contributed to".

Then call `check_draft` for the deterministic checks. Report findings as:

```json
{"location": "sections[0].bullets[2]", "code": "OVERSTATEMENT", "severity": "error", "message": "..."}
```

Fix each error by **rewording down or deleting** the bullet, never by adding facts, and re-run
`check_draft` until it returns `ready: true`.
