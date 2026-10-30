"""Match job locations against your wanted locations.

Wanted locations are city/metro names ("San Francisco, CA", "Bay Area, CA") or
remote scopes ("remote-US"). Metro names expand through ``data/metros.yaml``.
Matching returns ``None`` when the posting gives no usable location, so the
caller can fail open.
"""

from __future__ import annotations

import re
from functools import lru_cache

import yaml

from .config import data_text

US_HINTS = [
    "us",
    "u.s.",
    "u.s",
    "usa",
    "united states",
    "america",
    "us only",
    "us-based",
    "within the us",
    "anywhere in the us",
    "north america",
]
NON_US_HINTS = [
    "canada",
    "uk",
    "united kingdom",
    "europe",
    "emea",
    "eu",
    "germany",
    "france",
    "spain",
    "netherlands",
    "poland",
    "portugal",
    "ireland",
    "india",
    "apac",
    "asia",
    "australia",
    "latam",
    "latin america",
    "mexico",
    "brazil",
    "argentina",
    "philippines",
    "singapore",
    "japan",
    "israel",
]
GLOBAL_HINTS = ["anywhere", "worldwide", "global", "remote"]

US_STATE_ABBR = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", "il", "in", "ia", "ks",
    "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny",
    "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy", "dc",
}  # fmt: skip


@lru_cache(maxsize=1)
def metros() -> dict[str, list[str]]:
    return yaml.safe_load(data_text("metros.yaml")) or {}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("–", "-").replace("—", "-")).strip()


def _has_word(haystack: str, needle: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(needle.lower()) + r"(?![a-z])", haystack) is not None


def expand_wanted(wanted: str) -> list[str]:
    """``"Bay Area, CA"`` → its alias city names; a plain ``"Austin, TX"`` → ``["Austin"]``."""
    table = metros()
    for key, names in table.items():
        if _norm(key) == _norm(wanted):
            return names
    return [wanted.split(",")[0].strip()]


def is_remote_text(text: str) -> bool:
    t = _norm(text)
    return _has_word(t, "remote") or _has_word(t, "anywhere") or _has_word(t, "distributed")


def remote_scope(texts: list[str]) -> str | None:
    """Classify a remote posting as ``"us"``, ``"global"``, ``"non-us"`` or ``None`` (not remote)."""
    joined = _norm(" | ".join(texts))
    if not joined or not is_remote_text(joined):
        return None
    us = any(_has_word(joined, h) for h in US_HINTS)
    us = us or any(re.search(rf",\s*{abbr}\b", joined) for abbr in US_STATE_ABBR)
    non_us = any(_has_word(joined, h) for h in NON_US_HINTS)
    if us:
        return "us"
    if non_us:
        return "non-us"
    return "global"


def matches(
    job_locations: list[str],
    job_remote: str,
    wanted: list[str],
    include_remote_global: bool = True,
) -> bool | None:
    """True/False when the posting states a location; None when it gives nothing usable."""
    texts = [t for t in job_locations if t and t.strip()]
    if not texts and job_remote in ("unknown", ""):
        return None
    joined = _norm(" | ".join(texts))

    scope = remote_scope(texts) if texts else None
    if job_remote == "remote" and scope is None:
        scope = "global" if not texts else remote_scope(texts + ["remote"])

    for w in wanted:
        if _norm(w) in ("remote-us", "remote us", "remote (us)"):
            if scope == "us" or (scope == "global" and include_remote_global):
                return True
            continue
        if _norm(w) in ("remote", "remote-global", "remote-anywhere"):
            if scope in ("us", "global"):
                return True
            continue
        for city in expand_wanted(w):
            if _has_word(joined, city):
                return True
    return False
