# P2-04 · Ghost and scam risk score

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 2 · Profile + ranking | 1 day | P1-02 | todo |

## Why
Ghost jobs and scams waste applications. A deterministic risk score shown as a badge lets you judge, instead of silently hiding jobs.

## What to do
- [ ] `src/rojgaar/risk.py` signals: repeated reposts (from P1-09), age over 45 days, "talent pool"/"evergreen" wording, contact via WhatsApp/Telegram/personal email, upfront fees or equipment purchases, hidden text flagged by P1-08, mismatched company domain in apply URL.
- [ ] Output `risk: low|medium|high` plus `risk_flags[]`.
- [ ] `filters.hide_high_risk` in preferences (default false).

## Done when
- Fixture tests trigger each signal; the report shows the badge and flags.
