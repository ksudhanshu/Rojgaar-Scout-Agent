"""The deterministic pipeline: fetch → sanitize → dedup → store → filter → score → shortlist.

No LLM is involved here. All network access happens in this stage, before any
host CLI runs, so agents never need web access.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import risk
from .dedup import dedup_keys, find_duplicate
from .filters import apply_filters
from .http import FetchError, PoliteClient
from .models import Job
from .preferences import Preferences
from .registry import Company
from .scoring import Embedder, shortlist
from .sources.base import REGISTRY, FeedSource, Source

log = logging.getLogger("rojgaar.pipeline")


@dataclass
class SourceStats:
    fetched: int = 0
    new: int = 0
    duplicates: int = 0
    seen: int = 0
    errors: list[str] = field(default_factory=list)
    skipped: str | None = None


@dataclass
class FetchSummary:
    per_source: dict[str, SourceStats] = field(default_factory=dict)

    def totals(self) -> dict:
        t = {"fetched": 0, "new": 0, "duplicates": 0, "seen": 0, "errors": 0}
        for s in self.per_source.values():
            t["fetched"] += s.fetched
            t["new"] += s.new
            t["duplicates"] += s.duplicates
            t["seen"] += s.seen
            t["errors"] += len(s.errors)
        return t


def ingest(job: Job, store, now: datetime, stats: SourceStats) -> str:  # type: ignore[no-untyped-def]
    """Risk-score, dedup and store one job. Returns new / seen / duplicate."""
    stats.fetched += 1
    if store.get_job(job.uid):
        store.upsert_job(job, now)
        stats.seen += 1
        return "seen"
    decision = find_duplicate(job, store)
    if decision.reason == "repost":
        job.risk_flags.append("repost")
    job.risk, job.risk_flags = risk.assess(job, now)
    keys = dedup_keys(job)
    if decision.duplicate_of:
        store.upsert_job(job, now, keys=keys, duplicate_of=decision.duplicate_of)
        store.add_also_on(decision.duplicate_of, job.source)
        stats.duplicates += 1
        return "duplicate"
    store.upsert_job(job, now, keys=keys)
    stats.new += 1
    return "new"


def fetch_all(
    prefs: Preferences,
    store,  # type: ignore[no-untyped-def]
    client: PoliteClient,
    companies: list[Company],
    now: datetime,
    only: list[str] | None = None,
) -> FetchSummary:
    summary = FetchSummary()
    for name in prefs.enabled_sources():
        if only and name not in only:
            continue
        stats = summary.per_source.setdefault(name, SourceStats())
        cls = REGISTRY.get(name)
        if cls is None:
            stats.skipped = "not implemented yet"
            continue
        source = cls()
        cap = getattr(cls, "max_fetches_per_day", None)
        if cap is not None and store.fetches_since(name, now - timedelta(days=1)) >= cap:
            stats.skipped = f"daily fetch cap ({cap}) reached"
            continue
        if isinstance(source, FeedSource):
            try:
                jobs = source.fetch_feed(client)
                store.record_fetch(name, now)
            except (FetchError, KeyError, ValueError, TypeError) as exc:
                stats.errors.append(str(exc))
                log.warning("source %s failed: %s", name, exc)
                continue
            for job in jobs:
                ingest(job, store, now, stats)
        elif isinstance(source, Source):
            targets = [c for c in companies if c.ats == name]
            if not targets:
                stats.skipped = "no companies registered for this ATS"
                continue
            for company in targets:
                try:
                    jobs = source.fetch_company(client, company)
                except (FetchError, KeyError, ValueError, TypeError) as exc:
                    stats.errors.append(f"{company.slug}: {exc}")
                    log.warning("%s/%s failed: %s", name, company.slug, exc)
                    continue
                for job in jobs:
                    ingest(job, store, now, stats)
            store.record_fetch(name, now)
    return summary


@dataclass
class ShortlistResult:
    entries: list[dict]
    passed: int
    dropped: dict[str, list[str]]  # reason -> uids


def build_shortlist(
    prefs: Preferences,
    store,  # type: ignore[no-untyped-def]
    run_date: str,
    now: datetime,
    bank_skills: list[str] | None = None,
    embedder: Embedder | None = None,
    n: int | None = None,
) -> ShortlistResult:
    market = next(iter(prefs.active_markets().values()))
    candidates = store.candidate_jobs(now, prefs.filters.max_age_days)
    already = store.reported_before(run_date) if prefs.report.new_only else set()
    kept: list[Job] = []
    dropped: dict[str, list[str]] = {}
    for job in candidates:
        if job.uid in already:
            dropped.setdefault("already_reported", []).append(job.uid)
            continue
        result = apply_filters(job, prefs, market, now)
        if result.keep:
            kept.append(job)
        else:
            dropped.setdefault(result.reason or "unknown", []).append(job.uid)
    scored = shortlist(kept, prefs, n or prefs.report.shortlist_size, bank_skills, embedder)
    entries = [s.to_dict() for s in scored]
    store.save_shortlist(run_date, entries)
    return ShortlistResult(entries=entries, passed=len(kept), dropped=dropped)
