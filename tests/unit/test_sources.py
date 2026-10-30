from helpers import load_fixture

from rojgaar.registry import Company
from rojgaar.sources import (
    REGISTRY,
    AshbySource,
    GreenhouseSource,
    HNWhosHiringSource,
    LeverSource,
    RemoteOKSource,
    RemotiveSource,
)

ACME = Company("Acme Fintech", "greenhouse", "acme")
BETA = Company("Beta Cloud", "lever", "beta")
GAMMA = Company("Gamma", "ashby", "gamma")


def test_registry_contains_all_v01_sources():
    assert set(REGISTRY) == {"greenhouse", "lever", "ashby", "remotive", "remoteok", "hn_whos_hiring"}


def test_greenhouse_mapping(client):
    jobs = GreenhouseSource().fetch_company(client, ACME)
    assert len(jobs) == 4
    j = jobs[0]
    assert j.uid == "greenhouse:acme:4471203"
    assert j.company == "Acme Fintech"
    assert j.locations == ["San Francisco, CA"]
    assert j.salary.min == 180000 and j.salary.max == 220000
    assert "PostgreSQL" in j.description and "<" not in j.description
    assert j.date_posted.startswith("2026-10-27")
    assert jobs[1].remote == "remote"
    hidden = jobs[3]
    assert "hidden_text" in hidden.risk_flags
    assert "ignore previous" not in hidden.description


def test_greenhouse_requests_content(client, request_log):
    GreenhouseSource().fetch_company(client, ACME)
    assert request_log[0].url.params["content"] == "true"


def test_lever_mapping(client):
    jobs = LeverSource().fetch_company(client, BETA)
    j = jobs[0]
    assert j.uid == "lever:beta:b1c2d3e4-0001"
    assert j.remote == "hybrid"
    assert j.employment_type == "full_time"
    assert (j.salary.min, j.salary.max, j.salary.period) == (160000, 200000, "year")
    assert j.locations == ["Oakland, CA"]
    assert "Requirements" in j.description
    assert j.date_posted is not None
    assert jobs[1].remote == "onsite"


def test_ashby_mapping_skips_unlisted(client):
    jobs = AshbySource().fetch_company(client, GAMMA)
    assert [j.uid for j in jobs] == ["ashby:gamma:gm-100", "ashby:gamma:gm-200"]
    j = jobs[0]
    assert j.remote == "remote"
    assert j.locations == ["Remote", "San Francisco, CA"]
    assert (j.salary.min, j.salary.max) == (170000, 210000)
    assert j.employment_type == "full_time"
    assert jobs[1].remote == "onsite"


def test_remotive_mapping(client):
    jobs = RemotiveSource().fetch_feed(client)
    assert len(jobs) == 3
    j = jobs[0]
    assert j.uid == "remotive:delta-health:2001"
    assert j.locations == ["Remote (USA)"]
    assert (j.salary.min, j.salary.max) == (150000, 185000)
    assert j.ats is None


def test_remoteok_skips_legal_notice(client):
    jobs = RemoteOKSource().fetch_feed(client)
    assert len(jobs) == 1
    assert jobs[0].title == "Senior Go Engineer"
    assert jobs[0].salary.max == 170000
    assert jobs[0].locations == ["Remote (Worldwide)"]


def test_hn_parses_pipe_separated_comments(client):
    jobs = HNWhosHiringSource().fetch_feed(client)
    assert len(jobs) == 2  # the chatty non-job comment is skipped
    omega = jobs[0]
    assert omega.company == "Omega Robotics"
    assert omega.title == "Senior Backend Engineer"
    assert omega.locations == ["San Francisco, CA"]  # "ONSITE" is a mode, not a location
    assert omega.remote == "onsite"
    assert omega.apply_url == "https://omega.example/jobs"
    assert omega.salary.min == 190000
    sigma = jobs[1]
    assert sigma.title == "Founding Engineer"
    assert sigma.remote == "remote"
    assert sigma.apply_url.startswith("https://news.ycombinator.com/item?id=")


def test_hn_no_thread_returns_empty(fixtures):
    assert HNWhosHiringSource.parse_comment({"text": "", "author": "x"}) is None
    assert HNWhosHiringSource.parse_comment({"text": "no pipes here", "author": "x", "id": 1}) is None


def test_feed_caps_declared():
    assert RemotiveSource.max_fetches_per_day == 4
    assert HNWhosHiringSource.max_fetches_per_day == 2


def test_fixture_loader_sanity():
    assert load_fixture("remoteok.json")[0]["legal"].startswith("API Terms")
