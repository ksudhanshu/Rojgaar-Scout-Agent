"""Adapter interface and registry.

* ``Source`` (ATS adapters) fetch one company's board at a time.
* ``FeedSource`` (aggregators) fetch a whole feed and declare a daily fetch cap.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ..http import PoliteClient
from ..models import Job
from ..registry import Company


class Source(ABC):
    name: ClassVar[str]
    kind: ClassVar[str] = "ats"
    max_fetches_per_day: ClassVar[int | None] = None

    @abstractmethod
    def fetch_company(self, client: PoliteClient, company: Company) -> list[Job]: ...


class FeedSource(ABC):
    name: ClassVar[str]
    kind: ClassVar[str] = "feed"
    max_fetches_per_day: ClassVar[int | None] = 4

    @abstractmethod
    def fetch_feed(self, client: PoliteClient) -> list[Job]: ...


REGISTRY: dict[str, type[Source] | type[FeedSource]] = {}


def register(cls):  # type: ignore[no-untyped-def]
    REGISTRY[cls.name] = cls
    return cls


def get_source(name: str) -> Source | FeedSource | None:
    cls = REGISTRY.get(name)
    return cls() if cls else None


def remote_from_text(*texts: str | None) -> str:
    joined = " ".join(t or "" for t in texts).lower()
    if "hybrid" in joined:
        return "hybrid"
    if "remote" in joined:
        return "remote"
    if "on-site" in joined or "onsite" in joined or "in office" in joined or "in-office" in joined:
        return "onsite"
    return "unknown"


def employment_type(value: str | None) -> str | None:
    if not value:
        return None
    v = value.lower().replace("-", "").replace("_", "").replace(" ", "")
    mapping = {
        "fulltime": "full_time",
        "permanent": "full_time",
        "parttime": "part_time",
        "contract": "contract",
        "contractor": "contract",
        "temporary": "contract",
        "intern": "internship",
        "internship": "internship",
    }
    for key, out in mapping.items():
        if key in v:
            return out
    return None
