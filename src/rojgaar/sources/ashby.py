"""Ashby public job posting API, including compensation.

Docs: https://developers.ashbyhq.com/docs/public-job-posting-api
"""

from __future__ import annotations

from ..http import PoliteClient
from ..models import Job, Salary, parse_salary_text
from ..registry import Company
from ..sanitize import sanitize_html, sanitize_text
from .base import Source, employment_type, register, remote_from_text

API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
WORKPLACE = {"remote": "remote", "hybrid": "hybrid", "onsite": "onsite", "on-site": "onsite"}
INTERVALS = {"1 YEAR": "year", "1 MONTH": "month", "1 HOUR": "hour"}


@register
class AshbySource(Source):
    name = "ashby"

    def fetch_company(self, client: PoliteClient, company: Company) -> list[Job]:
        data = client.get_json(API.format(slug=company.slug), params={"includeCompensation": "true"})
        return [self.to_job(item, company) for item in data.get("jobs", []) if item.get("isListed", True)]

    @staticmethod
    def _salary(item: dict) -> Salary | None:
        comp = item.get("compensation") or {}
        for part in comp.get("summaryComponents") or []:
            if part.get("compensationType") == "Salary" and (part.get("minValue") or part.get("maxValue")):
                return Salary(
                    min=part.get("minValue"),
                    max=part.get("maxValue"),
                    currency=part.get("currencyCode") or "USD",
                    period=INTERVALS.get(part.get("interval", ""), "year"),  # type: ignore[arg-type]
                )
        return parse_salary_text(comp.get("compensationTierSummary"))

    @classmethod
    def to_job(cls, item: dict, company: Company) -> Job:
        if item.get("descriptionHtml"):
            clean = sanitize_html(item["descriptionHtml"])
        else:
            clean = sanitize_text(item.get("descriptionPlain"))
        locations = [item["location"]] if item.get("location") else []
        locations += [s.get("location") for s in item.get("secondaryLocations") or [] if s.get("location")]
        workplace = WORKPLACE.get((item.get("workplaceType") or "").lower().replace(" ", ""))
        if item.get("isRemote") and not workplace:
            workplace = "remote"
        job_id = str(item["id"])
        return Job(
            uid=f"ashby:{company.slug}:{job_id}",
            source="ashby",
            company=company.name,
            title=(item.get("title") or "").strip(),
            description=clean.text,
            locations=locations,
            remote=workplace or remote_from_text(*locations),  # type: ignore[arg-type]
            apply_url=item.get("jobUrl") or item.get("applyUrl") or "",
            date_posted=item.get("publishedAt"),
            salary=cls._salary(item) or parse_salary_text(clean.text),
            employment_type=employment_type(item.get("employmentType")),
            ats="ashby",
            ats_job_id=job_id,
            risk_flags=clean.flags,
        )
