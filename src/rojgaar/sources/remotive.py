"""Remotive remote-jobs API.

Terms: at most ~4 fetches a day, never more than 2 requests a minute, 24 h data
delay, keep attribution and a link back. Docs: https://github.com/remotive-com/remote-jobs-api
"""

from __future__ import annotations

from ..http import PoliteClient
from ..models import Job, parse_salary_text
from ..sanitize import sanitize_html
from ..utils import slugify
from .base import FeedSource, employment_type, register

API = "https://remotive.com/api/remote-jobs"


@register
class RemotiveSource(FeedSource):
    name = "remotive"
    max_fetches_per_day = 4

    def __init__(self, category: str | None = "software-dev") -> None:
        self.category = category

    def fetch_feed(self, client: PoliteClient) -> list[Job]:
        params = {"category": self.category} if self.category else None
        data = client.get_json(API, params=params)
        return [self.to_job(item) for item in data.get("jobs", [])]

    @staticmethod
    def to_job(item: dict) -> Job:
        clean = sanitize_html(item.get("description"))
        region = item.get("candidate_required_location") or ""
        company = item.get("company_name") or "Unknown"
        return Job(
            uid=f"remotive:{slugify(company)}:{item['id']}",
            source="remotive",
            company=company,
            title=(item.get("title") or "").strip(),
            description=clean.text,
            locations=[f"Remote ({region})" if region else "Remote"],
            remote="remote",
            apply_url=item.get("url") or "",
            date_posted=item.get("publication_date"),
            salary=parse_salary_text(item.get("salary")),
            employment_type=employment_type(item.get("job_type")),
            risk_flags=clean.flags,
        )
