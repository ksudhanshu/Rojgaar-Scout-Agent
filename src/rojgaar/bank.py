"""The experience bank: every true claim about you, each with a stable ID.

Tailoring may only select, reorder and rephrase these claims. ``bank.yaml`` is the
source of truth; a compact profile view is derived from it for prompts.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from .config import data_text


class Metric(BaseModel):
    value: float
    unit: str


class Claim(BaseModel):
    id: str
    text: str
    metrics: list[Metric] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    qualifiers: list[str] = Field(default_factory=list)
    evidence: str | None = None
    verified_by_user: bool = False
    alt_phrasings: list[str] = Field(default_factory=list)


class Role(BaseModel):
    id: str
    org: str
    title: str
    start: str
    end: str | None = None
    location: str | None = None
    claims: list[Claim] = Field(default_factory=list)

    def end_year(self) -> int | None:
        return int(str(self.end)[:4]) if self.end else None

    def start_year(self) -> int:
        return int(str(self.start)[:4])


class Education(BaseModel):
    id: str
    degree: str
    school: str | None = None
    end: str | None = None
    score: dict | None = None


class Bank(BaseModel):
    schema_version: int = 1
    roles: list[Role] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> Bank:
        seen: set[str] = set()
        for role in self.roles:
            for claim in role.claims:
                if claim.id in seen:
                    raise ValueError(f"duplicate claim id: {claim.id}")
                seen.add(claim.id)
        return self

    def claim_index(self) -> dict[str, tuple[Claim, Role]]:
        return {c.id: (c, r) for r in self.roles for c in r.claims}

    def all_skills(self) -> set[str]:
        out = {s.lower() for s in self.skills}
        for r in self.roles:
            for c in r.claims:
                out |= {s.lower() for s in c.skills}
        return out

    def profile_summary(self) -> dict:
        """A compact, PII-free view for prompts (JSON-Resume-like)."""
        return {
            "work": [
                {
                    "id": r.id,
                    "position": r.title,
                    "organization": r.org,
                    "startDate": r.start,
                    "endDate": r.end,
                    "highlights": [
                        {"id": c.id, "text": c.text, "skills": c.skills, "qualifiers": c.qualifiers}
                        for c in r.claims
                        if c.verified_by_user
                    ],
                }
                for r in self.roles
            ],
            "education": [e.model_dump() for e in self.education],
            "skills": sorted(self.all_skills()),
        }


class BankError(ValueError):
    pass


def parse_bank(text: str) -> Bank:
    try:
        return Bank.model_validate(yaml.safe_load(text) or {})
    except (yaml.YAMLError, ValidationError, ValueError) as exc:
        raise BankError(f"bank.yaml is invalid: {exc}") from exc


def load_bank(path: str | Path) -> Bank:
    p = Path(path)
    if not p.exists():
        raise BankError(f"{p} not found. Run `rojgaar init` and add your claims.")
    return parse_bank(p.read_text(encoding="utf-8"))


def example_bank_text() -> str:
    return data_text("bank.example.yaml")
