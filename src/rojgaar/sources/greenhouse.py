"""Greenhouse Job Board API — official, public, no auth for GET.

Docs: https://developers.greenhouse.io/job-board.html
Note: ``updated_at`` is not a posted date; prefer ``first_published`` when present.
"""

from __future__ import annotations

from ..http import PoliteClient
from ..models import Job, parse_salary_text
from ..registry import Company
from ..sanitize import sanitize_html
from .base import Source, register, remote_from_text

API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


@register
class GreenhouseSource(Source):
    name = "greenhouse"

    def fetch_company(self, client: PoliteClient, company: Company) -> list[Job]:
        data = client.get_json(API.format(slug=company.slug), params={"content": "true"})
        return [self.to_job(item, company) for item in data.get("jobs", [])]

    @staticmethod
    def to_job(item: dict, company: Company) -> Job:
        clean = sanitize_html(item.get("content"))
        location = (item.get("location") or {}).get("name") or ""
        offices = [o.get("name") for o in item.get("offices") or [] if o.get("name")]
        locations = [location] if location else offices
        job_id = str(item["id"])
        return Job(
            uid=f"greenhouse:{company.slug}:{job_id}",
            source="greenhouse",
            company=item.get("company_name") or company.name,
            title=(item.get("title") or "").strip(),
            description=clean.text,
            locations=locations,
            remote=remote_from_text(location, item.get("title")),
            apply_url=item.get("absolute_url") or "",
            date_posted=item.get("first_published"),
            salary=parse_salary_text(clean.text),
            ats="greenhouse",
            ats_job_id=job_id,
            risk_flags=clean.flags,
        )
