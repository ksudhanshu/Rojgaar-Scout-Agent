# P5-03 · Feedback capture and preference diffs

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 5 · Polish & community | 2 days | P2-06 | todo |

## Why
Your reactions are the best signal for what "good fit" means to you. High-scoring jobs you rejected are the most informative examples.

## What to do
- [ ] `rojgaar feedback <uid> up|down --reason too-senior|wrong-domain|location|salary|other` and a `/rojgaar-feedback` skill.
- [ ] Store in the `feedback` table.
- [ ] Weekly: the host model reads recent feedback and **proposes** diffs to `preferences.yaml` and `preference_memory.md`; you approve or reject each.
- [ ] Use rejected high scorers as few-shot negatives in the judge prompt.

## Done when
- After a week of feedback, the tool proposes at least one sensible diff and only applies it after approval.
