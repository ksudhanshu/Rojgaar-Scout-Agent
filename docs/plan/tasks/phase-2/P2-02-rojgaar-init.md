# P2-02 · `rojgaar init` onboarding

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 2 · Profile + ranking | 2 days | P2-01, P1-10 | todo |

## Why
Most users have a CV, not a YAML bank. Onboarding turns the CV into a draft bank and a preferences file, but **nothing is trusted until you confirm it**.

## What to do
- [ ] `rojgaar init` creates `~/RojgaarScout/` with `profile/`, `state/`, `reports/`, `applications/`.
- [ ] `/rojgaar-setup` skill: the host model reads your CV and proposes claims for `bank.yaml`, all with `verified_by_user: false`.
- [ ] Interactive review: accept, edit or reject each claim; only accepted ones become `true`.
- [ ] Short preference interview: locations (defaults SF, Bay Area, remote-US), work authorization, salary floor, seniority, target titles, core skills, dealbreakers → `preferences.yaml`.
- [ ] Split personal details into `pii.yaml`.

## Done when
- A new user goes from CV to a valid bank + preferences in under 20 minutes; unverified claims are never used for drafting.
