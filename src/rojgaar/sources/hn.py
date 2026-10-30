"""Hacker News "Ask HN: Who is hiring?" via the public Algolia HN API (no key).

Each top-level comment is one employer. The first line is conventionally
``Company | Role | Location | REMOTE/ONSITE | Salary | URL`` but formats vary,
so parsing is best-effort and the raw text is kept.
"""

from __future__ import annotations

import re

from ..http import PoliteClient
from ..models import Job, parse_salary_text
from ..sanitize import sanitize_html
from ..utils import slugify
from .base import FeedSource, register, remote_from_text

SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
ITEM = "https://hn.algolia.com/api/v1/items/{id}"
ROLE_WORDS = re.compile(
    r"engineer|developer|scientist|designer|manager|architect|sre|devops|analyst|researcher|lead|"
    r"product|programmer|founding|full[- ]?stack|backend|frontend|ml|data",
    re.I,
)
LOCATION_WORDS = re.compile(
    r"remote|onsite|on-site|hybrid|san francisco|sf\b|bay area|new york|nyc|seattle|austin|boston|"
    r"london|berlin|toronto|los angeles|palo alto|mountain view|oakland|san jose|, [A-Z]{2}\b|usa|us only",
    re.I,
)


MODE_ONLY = re.compile(r"\s*(remote|onsite|on-site|hybrid|in[- ]office)\s*", re.I)


@register
class HNWhosHiringSource(FeedSource):
    name = "hn_whos_hiring"
    max_fetches_per_day = 2

    def fetch_feed(self, client: PoliteClient) -> list[Job]:
        hits = client.get_json(SEARCH, params={"tags": "story,author_whoishiring", "query": "who is hiring"})
        story = next(
            (h for h in hits.get("hits", []) if "who is hiring" in (h.get("title") or "").lower()), None
        )
        if not story:
            return []
        thread = client.get_json(ITEM.format(id=story["objectID"]))
        jobs = []
        for child in thread.get("children") or []:
            job = self.parse_comment(child)
            if job:
                jobs.append(job)
        return jobs

    @staticmethod
    def parse_comment(child: dict) -> Job | None:
        raw = child.get("text") or ""
        if not raw or child.get("author") in (None, "whoishiring"):
            return None
        clean = sanitize_html(raw)
        lines = [ln.strip() for ln in clean.text.splitlines() if ln.strip()]
        if not lines or "|" not in lines[0]:
            return None
        parts = [p.strip() for p in lines[0].split("|") if p.strip()]
        company = re.sub(r"\(.*?\)", "", parts[0]).strip() or "Unknown"
        rest = parts[1:]
        title = next((p for p in rest if ROLE_WORDS.search(p) and not LOCATION_WORDS.fullmatch(p)), None)
        loc_parts = [p for p in rest if LOCATION_WORDS.search(p) and p != title]
        # Pure work-mode tags ("ONSITE", "Hybrid") set the remote mode but are not locations.
        locs = [p for p in loc_parts if not MODE_ONLY.fullmatch(p)]
        urls = re.findall(r'href="([^"]+)"', raw)
        hn_link = f"https://news.ycombinator.com/item?id={child.get('id')}"
        return Job(
            uid=f"hn:{slugify(company)}:{child.get('id')}",
            source="hn_whos_hiring",
            company=company,
            title=title or "Multiple roles",
            description=clean.text,
            locations=locs,
            remote=remote_from_text(*loc_parts),  # type: ignore[arg-type]
            apply_url=(urls[0].replace("&#x2F;", "/") if urls else hn_link),
            date_posted=child.get("created_at"),
            salary=parse_salary_text(lines[0]),
            risk_flags=clean.flags + ([] if title else ["parse_low_confidence"]),
        )
