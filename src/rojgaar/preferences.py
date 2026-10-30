"""Load and validate ``preferences.yaml`` — the single place you control the search."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from .config import data_text

DEFAULT_SOURCES = [
    "greenhouse",
    "lever",
    "ashby",
    "remotive",
    "remoteok",
    "hn_whos_hiring",
]


class SalaryFloor(BaseModel):
    amount: float
    currency: str = "USD"
    period: str = "year"


class Market(BaseModel):
    enabled: bool = True
    locations: list[str] = Field(default_factory=lambda: ["San Francisco, CA", "Bay Area, CA", "remote-US"])
    work_authorization: str = "citizen"
    drop_if_no_sponsorship: bool = False
    salary_floor: SalaryFloor | None = None
    cv_locale: str = "us"
    sources: list[str] = Field(default_factory=lambda: list(DEFAULT_SOURCES))
    company_registry: str | None = None
    alert_email_ingest: bool = False


class Filters(BaseModel):
    remote_modes: list[str] = Field(default_factory=lambda: ["remote", "hybrid", "onsite"])
    employment_types: list[str] = Field(default_factory=lambda: ["full_time"])
    seniority: list[str] = Field(default_factory=list)
    max_age_days: int = 30
    exclude_companies: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    exclude_title_words: list[str] = Field(default_factory=list)
    require_keywords: list[str] = Field(default_factory=list)
    hide_high_risk: bool = False


class Ranking(BaseModel):
    target_titles: list[str] = Field(default_factory=list)
    core_skills: dict[str, int] = Field(default_factory=dict)
    preferred_domains: list[str] = Field(default_factory=list)
    preferred_companies: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(
        default_factory=lambda: {"title": 2, "must_have": 3, "seniority": 2, "logistics": 2, "preference": 1}
    )


class ReportSettings(BaseModel):
    top_n: int = 15
    drafts_per_day: int = 5
    new_only: bool = True
    shortlist_size: int = 40


class Preferences(BaseModel):
    schema_version: int = 1
    markets: dict[str, Market] = Field(default_factory=lambda: {"us": Market()})
    include_remote_global: bool = True
    filters: Filters = Field(default_factory=Filters)
    ranking: Ranking = Field(default_factory=Ranking)
    report: ReportSettings = Field(default_factory=ReportSettings)

    def active_markets(self) -> dict[str, Market]:
        return {name: m for name, m in self.markets.items() if m.enabled}

    def enabled_sources(self) -> list[str]:
        seen: list[str] = []
        for market in self.active_markets().values():
            for s in market.sources:
                if s not in seen:
                    seen.append(s)
        return seen


class PreferencesError(ValueError):
    pass


def parse_preferences(text: str) -> Preferences:
    try:
        data = yaml.safe_load(text) or {}
        return Preferences.model_validate(data)
    except (yaml.YAMLError, ValidationError) as exc:
        raise PreferencesError(f"preferences.yaml is invalid: {exc}") from exc


def load_preferences(path: str | Path) -> Preferences:
    p = Path(path)
    if not p.exists():
        raise PreferencesError(f"{p} not found. Run `rojgaar init` to create it.")
    return parse_preferences(p.read_text(encoding="utf-8"))


def example_preferences_text() -> str:
    return data_text("preferences.example.yaml")
