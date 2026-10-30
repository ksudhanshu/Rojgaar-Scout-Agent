# P5-02 · Job-alert email parser

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 5 · Polish & community | 2 days | P1-01 | todo |

## Why
LinkedIn and Indeed have no read API and restrict scraping, but you already receive their job-alert emails. Parsing first-party emails sent to you avoids scraping entirely. (This is an inference: no source assessed alert-email terms.)

## What to do
- [ ] Input: a local mailbox export (`.mbox`/`.eml` folder) the user points to; no email credentials stored by the tool.
- [ ] Parsers for LinkedIn and Indeed alert formats → `Job` with source `alert:linkedin` / `alert:indeed`; resolve to the employer's ATS posting when the company is in the registry.
- [ ] Off by default (`markets.us.alert_email_ingest: false`).

## Done when
- Fixture emails from both senders parse into valid jobs; jobs that match a registry company dedup against the ATS record.
