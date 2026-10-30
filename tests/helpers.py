"""Shared test constants and helpers (importable as `helpers`)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 29, 15, 0, tzinfo=UTC)
RUN_DATE = "2026-10-29"

TEST_COMPANIES = """
companies:
  - {name: Acme Fintech, ats: greenhouse, slug: acme, hq: "San Francisco, CA", verified: true}
  - {name: Beta Cloud,   ats: lever,      slug: beta, hq: "Oakland, CA",       verified: true}
  - {name: Gamma,        ats: ashby,      slug: gamma, hq: "San Francisco, CA", verified: true}
"""

ROUTES = {
    ("boards-api.greenhouse.io", "/v1/boards/acme/jobs"): "greenhouse_acme.json",
    ("api.lever.co", "/v0/postings/beta"): "lever_beta.json",
    ("api.ashbyhq.com", "/posting-api/job-board/gamma"): "ashby_gamma.json",
    ("remotive.com", "/api/remote-jobs"): "remotive.json",
    ("remoteok.com", "/api"): "remoteok.json",
    ("hn.algolia.com", "/api/v1/search_by_date"): "hn_search.json",
    ("hn.algolia.com", "/api/v1/items/45800000"): "hn_item.json",
}


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def make_handler(routes: dict | None = None, log: list | None = None):
    routes = routes or ROUTES

    def handler(request: httpx.Request) -> httpx.Response:
        if log is not None:
            log.append(request)
        key = (request.url.host, request.url.path)
        if key in routes:
            return httpx.Response(200, json=load_fixture(routes[key]))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(404, json={"error": "not found"})

    return handler


def make_job(**overrides):
    """Build a Job with sensible defaults for unit tests."""
    from rojgaar.models import Job

    data = {
        "uid": "greenhouse:acme:1",
        "source": "greenhouse",
        "company": "Acme Fintech",
        "title": "Senior Backend Engineer",
        "description": "Python Go PostgreSQL services",
        "locations": ["San Francisco, CA"],
        "remote": "onsite",
        "apply_url": "https://boards.greenhouse.io/acme/jobs/1",
        "date_posted": "2026-10-27T09:00:00+00:00",
        "ats": "greenhouse",
        "ats_job_id": "1",
    }
    data.update(overrides)
    return Job(**data)
