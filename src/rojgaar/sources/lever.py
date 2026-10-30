"""Lever Postings API — public; "published jobs are publicly viewable and may be scraped".

Docs: https://github.com/lever/postings-api
"""

from __future__ import annotations

from ..http import PoliteClient
from ..models import Job, Salary, parse_salary_text
from ..registry import Company
from ..sanitize import sanitize_text
from ..utils import iso, parse_dt
from .base import Source, employment_type, register, remote_from_text

API = "https://api.lever.co/v0/postings/{slug}"
INTERVALS = {"per-year-salary": "year", "per-month-salary": "month", "per-hour-wage": "hour"}
WORKPLACE = {"remote": "remote", "hybrid": "hybrid", "on-site": "onsite", "onsite": "onsite"}


@register
class LeverSource(Source):
    name = "lever"

    def fetch_company(self, client: PoliteClient, company: Company) -> list[Job]:
        data = client.get_json(API.format(slug=company.slug), params={"mode": "json"})
        return [self.to_job(item, company) for item in data or []]

    @staticmethod
    def to_job(item: dict, company: Company) -> Job:
        cats = item.get("categories") or {}
        parts = [item.get("descriptionPlain") or ""]
        for block in item.get("lists") or []:
            parts.append(f"\n{block.get('text', '')}\n{block.get('content', '')}")
        parts.append(item.get("additionalPlain") or "")
        clean = sanitize_text("\n".join(p for p in parts if p))
        locations = list(cats.get("allLocations") or []) or (
            [cats["location"]] if cats.get("location") else []
        )

        salary = None
        rng = item.get("salaryRange")
        if rng and (rng.get("min") or rng.get("max")):
            salary = Salary(
                min=rng.get("min"),
                max=rng.get("max"),
                currency=rng.get("currency") or "USD",
                period=INTERVALS.get(rng.get("interval", ""), "year"),  # type: ignore[arg-type]
            )
        salary = salary or parse_salary_text(item.get("salaryDescriptionPlain") or clean.text)

        workplace = WORKPLACE.get((item.get("workplaceType") or "").lower())
        created = parse_dt(item.get("createdAt"))
        job_id = str(item["id"])
        return Job(
            uid=f"lever:{company.slug}:{job_id}",
            source="lever",
            company=company.name,
            title=(item.get("text") or "").strip(),
            description=clean.text,
            locations=locations,
            remote=workplace or remote_from_text(*locations),  # type: ignore[arg-type]
            apply_url=item.get("hostedUrl") or item.get("applyUrl") or "",
            date_posted=iso(created) if created else None,
            salary=salary,
            employment_type=employment_type(cats.get("commitment")),
            ats="lever",
            ats_job_id=job_id,
            risk_flags=clean.flags,
        )
