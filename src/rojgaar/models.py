"""The normalized job record every source maps into.

Field names follow schema.org ``JobPosting`` where possible so we don't invent a
vocabulary. ``first_seen`` is our own timestamp and the only date we fully trust.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

RemoteMode = Literal["remote", "hybrid", "onsite", "unknown"]


class Salary(BaseModel):
    min: float | None = None
    max: float | None = None
    currency: str = "USD"
    period: Literal["year", "month", "hour"] = "year"

    def yearly_max(self) -> float | None:
        top = self.max if self.max is not None else self.min
        if top is None:
            return None
        return {"year": 1, "month": 12, "hour": 2080}[self.period] * top


class Job(BaseModel):
    uid: str
    source: str
    company: str
    title: str
    description: str = ""
    locations: list[str] = Field(default_factory=list)
    remote: RemoteMode = "unknown"
    apply_url: str = ""
    date_posted: str | None = None
    salary: Salary | None = None
    employment_type: str | None = None
    ats: str | None = None
    ats_job_id: str | None = None
    first_seen: str | None = None
    last_seen: str | None = None
    risk: Literal["low", "medium", "high"] = "low"
    risk_flags: list[str] = Field(default_factory=list)
    duplicate_of: str | None = None
    also_on: list[str] = Field(default_factory=list)

    def location_text(self) -> str:
        return "; ".join(self.locations) if self.locations else "Location not stated"


_MONEY = r"\$\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?([kK])?"


def _amount(num: str, k: str | None) -> float:
    value = float(num.replace(",", ""))
    return value * 1000 if k else value


def parse_salary_text(text: str | None) -> Salary | None:
    """Extract a USD salary range such as ``$150,000 - $200,000`` or ``$150k–$200k/yr``.

    Returns ``None`` unless an actual figure is stated; we never estimate.
    """
    if not text:
        return None
    m = re.search(_MONEY + r"\s?(?:-|–|—|to)\s?" + _MONEY, text)
    if m:
        lo = _amount(m.group(1), m.group(2))
        hi = _amount(m.group(3), m.group(4) or m.group(2))
    else:
        m = re.search(_MONEY, text)
        if not m:
            return None
        lo = hi = _amount(m.group(1), m.group(2))
    tail = text[m.end() : m.end() + 24].lower()
    if "hour" in tail or "/hr" in tail or "an hr" in tail:
        period = "hour"
    elif "month" in tail:
        period = "month"
    else:
        period = "year"
    if period == "year" and hi < 10_000:  # e.g. "$150" with no k is not an annual salary
        return None
    return Salary(min=lo, max=hi, currency="USD", period=period)
