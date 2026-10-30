"""Stage 1 of the funnel: free, deterministic hard filters.

The key rule is FAIL-OPEN: a field the posting doesn't state never drops it.
Every drop records its reason so false drops can be audited.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from . import locations
from .models import Job
from .preferences import Market, Preferences
from .store import age_days

SENIORITY = ["intern", "junior", "mid", "senior", "staff", "principal", "director", "vp"]
NO_SPONSORSHIP = re.compile(
    r"(no|not|unable to|cannot|can't|will not|won't)\s+(offer\s+|provide\s+|be able to\s+)?(visa\s+)?sponsor"
    r"|without (visa )?sponsorship|sponsorship is not available|must be authorized to work .* without",
    re.I,
)


@dataclass
class FilterResult:
    keep: bool
    reason: str | None = None


def infer_seniority(title: str) -> str | None:
    t = title.lower()
    rules = [
        (r"\bintern(ship)?\b", "intern"),
        (r"\b(vp|vice president)\b", "vp"),
        (r"\b(director|head of)\b", "director"),
        (r"\b(principal|distinguished|fellow)\b", "principal"),
        (r"\bstaff\b", "staff"),
        (r"\b(senior|sr\.?)\b|\biii\b|\blevel 3\b", "senior"),
        (r"\b(junior|jr\.?|entry[- ]level|new grad|graduate|associate)\b|\bi\b$", "junior"),
        (r"\bii\b|\blevel 2\b|\bmid[- ]level\b", "mid"),
    ]
    for pattern, level in rules:
        if re.search(pattern, t):
            return level
    return None


def _seniority_ok(level: str | None, wanted: list[str]) -> bool:
    if not wanted or level is None:
        return True
    idx = SENIORITY.index(level)
    return any(abs(idx - SENIORITY.index(w)) <= 1 for w in wanted if w in SENIORITY)


def _contains_any(text: str, words: list[str]) -> str | None:
    low = text.lower()
    for w in words:
        if re.search(r"(?<![a-z0-9])" + re.escape(w.lower()) + r"(?![a-z0-9])", low):
            return w
    return None


def apply_filters(job: Job, prefs: Preferences, market: Market, now: datetime) -> FilterResult:
    f = prefs.filters
    if _contains_any(job.company, f.exclude_companies):
        return FilterResult(False, "excluded_company")
    hit = _contains_any(job.title, f.exclude_title_words)
    if hit:
        return FilterResult(False, f"excluded_title_word:{hit}")
    hit = _contains_any(f"{job.title}\n{job.description}", f.exclude_keywords)
    if hit:
        return FilterResult(False, f"excluded_keyword:{hit}")
    if f.require_keywords and not _contains_any(f"{job.title}\n{job.description}", f.require_keywords):
        return FilterResult(False, "missing_required_keyword")

    loc = locations.matches(job.locations, job.remote, market.locations, prefs.include_remote_global)
    if loc is False:
        return FilterResult(False, "location")

    if job.remote != "unknown" and job.remote not in f.remote_modes:
        return FilterResult(False, f"remote_mode:{job.remote}")
    if job.employment_type and f.employment_types and job.employment_type not in f.employment_types:
        return FilterResult(False, f"employment_type:{job.employment_type}")

    age = age_days(job, now)
    if age is not None and age > f.max_age_days:
        return FilterResult(False, "too_old")

    if not _seniority_ok(infer_seniority(job.title), f.seniority):
        return FilterResult(False, "seniority")

    floor = market.salary_floor
    if floor and job.salary and job.salary.currency.upper() == floor.currency.upper():
        top = job.salary.yearly_max()
        if top is not None and top < floor.amount:
            return FilterResult(False, "salary_below_floor")

    if market.drop_if_no_sponsorship and NO_SPONSORSHIP.search(job.description):
        return FilterResult(False, "no_sponsorship")

    if f.hide_high_risk and job.risk == "high":
        return FilterResult(False, "high_risk")
    return FilterResult(True)
