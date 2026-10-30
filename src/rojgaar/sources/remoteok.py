"""Remote OK API. The first array element is a legal notice; attribution and a
followed link back to Remote OK are required. Docs: https://remoteok.com/api
"""

from __future__ import annotations

from ..http import PoliteClient
from ..models import Job, Salary
from ..sanitize import sanitize_html
from ..utils import slugify
from .base import FeedSource, register

API = "https://remoteok.com/api"


@register
class RemoteOKSource(FeedSource):
    name = "remoteok"
    max_fetches_per_day = 4

    def fetch_feed(self, client: PoliteClient) -> list[Job]:
        data = client.get_json(API)
        return [
            self.to_job(item)
            for item in data
            if isinstance(item, dict) and "id" in item and "legal" not in item
        ]

    @staticmethod
    def to_job(item: dict) -> Job:
        clean = sanitize_html(item.get("description"))
        lo, hi = item.get("salary_min") or None, item.get("salary_max") or None
        salary = Salary(min=lo, max=hi) if (lo or hi) else None
        company = item.get("company") or "Unknown"
        location = item.get("location") or ""
        return Job(
            uid=f"remoteok:{slugify(company)}:{item['id']}",
            source="remoteok",
            company=company,
            title=(item.get("position") or "").strip(),
            description=clean.text,
            locations=[f"Remote ({location})" if location else "Remote"],
            remote="remote",
            apply_url=item.get("url") or item.get("apply_url") or "",
            date_posted=item.get("date"),
            salary=salary,
            risk_flags=clean.flags,
        )
