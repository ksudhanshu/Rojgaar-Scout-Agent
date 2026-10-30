"""Fetch → sanitize → dedup → store → filter → score → shortlist → report, across all six sources."""

import pytest
from helpers import NOW, RUN_DATE

from rojgaar.bank import load_bank
from rojgaar.daily import write_daily_report
from rojgaar.pipeline import build_shortlist, fetch_all
from rojgaar.preferences import load_preferences
from rojgaar.registry import load_companies
from rojgaar.store import Store

pytestmark = pytest.mark.integration

EXPECTED_SHORTLIST = {
    "greenhouse:acme:4471203",  # Senior Backend, SF, $180–220k
    "greenhouse:acme:4471300",  # Staff Platform, Remote - US
    "greenhouse:acme:4471500",  # Senior SWE, Mountain View (Bay Area) — flagged hidden text
    "lever:beta:b1c2d3e4-0001",  # Backend Engineer, Oakland hybrid
    "ashby:gamma:gm-100",  # Senior SWE Platform, Remote + SF
    "remotive:delta-health:2001",  # Senior Python, Remote (USA)
    "remoteok:zeta-labs:330001",  # Senior Go, Worldwide remote — WhatsApp scam signal
    "hn:omega-robotics:45800101",  # Senior Backend, SF onsite
    "hn:sigma-ai:45800102",  # Founding Engineer, Remote (US)
}


@pytest.fixture
def ctx(home, client):
    prefs = load_preferences(home.preferences)
    store = Store(home.db)
    companies = load_companies(home.companies)
    yield prefs, store, companies, client
    store.close()


def test_fetch_all_sources_with_cross_board_dedup(ctx):
    prefs, store, companies, client = ctx
    summary = fetch_all(prefs, store, client, companies, NOW)
    totals = summary.totals()
    assert totals == {"fetched": 14, "new": 13, "duplicates": 1, "seen": 0, "errors": 0}
    assert summary.per_source["remotive"].duplicates == 1

    canonical = store.get_job("greenhouse:acme:4471300")
    assert canonical.also_on == ["remotive"]
    dup = store.get_job("remotive:acme-fintech:2002")
    assert dup.duplicate_of == "greenhouse:acme:4471300"


def test_second_fetch_same_day_inserts_nothing(ctx):
    prefs, store, companies, client = ctx
    fetch_all(prefs, store, client, companies, NOW)
    again = fetch_all(prefs, store, client, companies, NOW).totals()
    assert again["new"] == 0 and again["duplicates"] == 0
    assert again["seen"] == 14


def test_daily_fetch_caps_are_enforced(ctx):
    prefs, store, companies, client = ctx
    for _ in range(3):
        fetch_all(prefs, store, client, companies, NOW)
    summary = fetch_all(prefs, store, client, companies, NOW)
    assert summary.per_source["hn_whos_hiring"].skipped == "daily fetch cap (2) reached"
    assert summary.per_source["greenhouse"].skipped is None


def test_one_failing_source_does_not_stop_the_others(ctx, home):
    import httpx
    from helpers import ROUTES, make_handler

    from rojgaar.http import PoliteClient

    prefs, store, companies, _ = ctx
    routes = {k: v for k, v in ROUTES.items() if k[0] != "api.lever.co"}  # lever → 404
    broken = PoliteClient(
        min_delay=0, jitter=0, transport=httpx.MockTransport(make_handler(routes)), sleep=lambda s: None
    )
    summary = fetch_all(prefs, store, broken, companies, NOW)
    assert summary.per_source["lever"].errors and "HTTP 404" in summary.per_source["lever"].errors[0]
    assert summary.per_source["greenhouse"].new == 4


def test_shortlist_applies_sf_bay_area_remote_us_defaults(ctx, home):
    prefs, store, companies, client = ctx
    fetch_all(prefs, store, client, companies, NOW)
    skills = sorted(load_bank(home.bank).all_skills())
    result = build_shortlist(prefs, store, RUN_DATE, NOW, skills)
    assert {e["uid"] for e in result.entries} == EXPECTED_SHORTLIST
    assert len(result.dropped["location"]) == 4  # NY ×2, London, Europe-only remote
    # BM25 puts the Go/Python/PostgreSQL backend roles above the generic ones
    top3 = [e["uid"] for e in result.entries[:3]]
    assert "greenhouse:acme:4471203" in top3
    # Risk badges survived into the store
    assert store.get_job("remoteok:zeta-labs:330001").risk == "high"
    assert store.get_job("greenhouse:acme:4471500").risk == "high"


def test_report_and_new_only_on_the_next_day(ctx, home):
    from datetime import timedelta

    prefs, store, companies, client = ctx
    fetch_all(prefs, store, client, companies, NOW)
    build_shortlist(prefs, store, RUN_DATE, NOW)
    report = write_daily_report(store, home, prefs, RUN_DATE, {"fetched": 14, "new": 13})
    text = report.read_text()
    assert report.name == "2026-10-29.md"
    assert "New matches (cheap scoring only, no LLM)" in text
    assert "Senior Backend Engineer, Payments — Acme Fintech" in text
    assert "Software Engineer, Growth" not in text  # New York, filtered out
    assert "[apply on the employer's site](" in text
    assert "gh_src" not in text  # tracking parameters stripped from apply links

    tomorrow = NOW + timedelta(days=1)
    next_day = build_shortlist(prefs, store, "2026-10-30", tomorrow)
    assert next_day.entries == []  # everything was already reported yesterday
    assert len(next_day.dropped["already_reported"]) == 9
