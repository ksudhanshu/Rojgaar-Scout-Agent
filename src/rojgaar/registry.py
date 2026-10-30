"""Company registry: which employer uses which ATS, under which board slug.

No ATS publishes its customer list, so the registry is curated. ``detect_ats``
recognises ATS board URLs; ``discover`` scans a careers page for them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import data_text


@dataclass(frozen=True)
class Company:
    name: str
    ats: str
    slug: str
    hq: str | None = None
    verified: bool = False
    tenant: str | None = None  # Workday only
    site: str | None = None  # Workday only


ATS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "greenhouse",
        re.compile(
            r"https?://(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)"
        ),
    ),
    ("greenhouse", re.compile(r"https?://boards-api\.greenhouse\.io/v1/boards/([A-Za-z0-9_-]+)")),
    ("lever", re.compile(r"https?://jobs(?:\.eu)?\.lever\.co/([A-Za-z0-9_.-]+)")),
    ("lever", re.compile(r"https?://api(?:\.eu)?\.lever\.co/v0/postings/([A-Za-z0-9_.-]+)")),
    ("ashby", re.compile(r"https?://jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)")),
    ("ashby", re.compile(r"https?://api\.ashbyhq\.com/posting-api/job-board/([A-Za-z0-9_.%-]+)")),
    ("workable", re.compile(r"https?://apply\.workable\.com/([A-Za-z0-9_-]+)")),
    (
        "workday",
        re.compile(
            r"https?://([A-Za-z0-9-]+)\.wd\d+\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)"
        ),
    ),
]
_IGNORED_SLUGS = {"embed", "api", "v1", "jobs", "careers", "job_board"}


def detect_ats(url: str) -> tuple[str, str] | None:
    """Return ``(ats, slug)`` for an ATS board or job URL, else ``None``."""
    for ats, pattern in ATS_PATTERNS:
        m = pattern.search(url)
        if not m:
            continue
        if ats == "workday":
            return ats, f"{m.group(1)}/{m.group(2)}"
        slug = m.group(1)
        if slug.lower() not in _IGNORED_SLUGS:
            return ats, slug
    return None


def discover(html: str) -> list[tuple[str, str]]:
    """Find every distinct ATS board referenced in a careers page."""
    found: list[tuple[str, str]] = []
    for url in re.findall(r"https?://[^\s\"'<>)]+", html):
        hit = detect_ats(url)
        if hit and hit not in found:
            found.append(hit)
    return found


def parse_companies(text: str) -> list[Company]:
    data = yaml.safe_load(text) or {}
    out = []
    for item in data.get("companies", []):
        out.append(
            Company(
                name=item["name"],
                ats=item["ats"],
                slug=item["slug"],
                hq=item.get("hq"),
                verified=bool(item.get("verified", False)),
                tenant=item.get("tenant"),
                site=item.get("site"),
            )
        )
    return out


def load_companies(path: str | Path | None) -> list[Company]:
    if path and Path(path).exists():
        return parse_companies(Path(path).read_text(encoding="utf-8"))
    return parse_companies(data_text("companies.us.yaml"))


def dump_companies(companies: list[Company]) -> str:
    rows = []
    for c in companies:
        row = {"name": c.name, "ats": c.ats, "slug": c.slug, "hq": c.hq, "verified": c.verified}
        rows.append({k: v for k, v in row.items() if v is not None})
    return yaml.safe_dump({"companies": rows}, sort_keys=False)
