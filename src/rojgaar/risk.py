"""Deterministic ghost-job and scam signals, shown as a badge rather than silently hidden."""

from __future__ import annotations

import re
from datetime import datetime

from .models import Job
from .store import age_days

SIGNALS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "talent_pool",
        re.compile(
            r"talent (pool|community|network)|evergreen|future opportunities|general application", re.I
        ),
        "medium",
    ),
    ("messaging_app_contact", re.compile(r"\b(whatsapp|telegram|signal app|wechat)\b", re.I), "high"),
    (
        "upfront_fee",
        re.compile(
            r"(registration|training|starter kit|equipment) fee|pay (for|a fee)|deposit (a|the) check|purchase (your own )?equipment",
            re.I,
        ),
        "high",
    ),
    (
        "personal_email_contact",
        re.compile(r"[\w.+-]+@(gmail|yahoo|hotmail|outlook|aol)\.com", re.I),
        "medium",
    ),
    (
        "too_good",
        re.compile(
            r"no experience (needed|required).{0,40}\$\d{3,}|earn \$\d+[kK]? (a|per) (week|day)", re.I
        ),
        "high",
    ),
]
INHERITED = {
    "hidden_text": "high",
    "injection_phrase": "high",
    "invisible_unicode": "medium",
    "repost": "medium",
}


def assess(job: Job, now: datetime) -> tuple[str, list[str]]:
    flags = [f for f in job.risk_flags if f in INHERITED or f.startswith("parse_")]
    levels = [INHERITED[f] for f in flags if f in INHERITED]
    text = f"{job.title}\n{job.description}"
    for name, pattern, level in SIGNALS:
        if pattern.search(text):
            flags.append(name)
            levels.append(level)
    age = age_days(job, now)
    if age is not None and age > 45:
        flags.append("stale_over_45_days")
        levels.append("medium")
    if "high" in levels or levels.count("medium") >= 3:
        return "high", flags
    if levels:
        return "medium", flags
    return "low", flags
