"""Stage 3: the LLM judge's output contract and the score computed in code.

The model returns categorical 0–3 scores per dimension with evidence; code
turns them into one number using the weights in ``preferences.yaml``. That keeps
the ranking explainable and tunable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

DIMENSIONS = ("title", "must_have", "seniority", "logistics", "preference")


class Requirement(BaseModel):
    text: str
    status: Literal["met", "partial", "missing"]
    evidence: list[str] = Field(default_factory=list, description="bank claim ids")


class Judgement(BaseModel):
    uid: str
    scores: dict[str, int] = Field(description="0-3 for each of: " + ", ".join(DIMENSIONS))
    verdict: Literal["strong", "good", "stretch", "poor"]
    dealbreaker_hit: bool = False
    reasons: list[str] = Field(default_factory=list, max_length=3)
    gaps: list[str] = Field(default_factory=list, max_length=3)
    risk_flags: list[str] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)

    @field_validator("scores")
    @classmethod
    def _check_scores(cls, v: dict[str, int]) -> dict[str, int]:
        missing = [d for d in DIMENSIONS if d not in v]
        if missing:
            raise ValueError(f"missing dimensions: {missing}")
        for k, s in v.items():
            if k not in DIMENSIONS:
                raise ValueError(f"unknown dimension {k!r}")
            if not 0 <= int(s) <= 3:
                raise ValueError(f"score for {k} must be 0-3")
        return v


class JudgeBatch(BaseModel):
    judgements: list[Judgement]


def weighted_score(j: Judgement, weights: dict[str, float]) -> float:
    if j.dealbreaker_hit:
        return 0.0
    total = sum(weights.get(d, 1.0) for d in DIMENSIONS)
    got = sum(weights.get(d, 1.0) * j.scores[d] / 3 for d in DIMENSIONS)
    return round(got / total, 4) if total else 0.0


def rank(judgements: list[Judgement], weights: dict[str, float]) -> list[tuple[Judgement, float]]:
    scored = [(j, weighted_score(j, weights)) for j in judgements]
    return sorted(scored, key=lambda x: (-x[1], x[0].uid))


def judge_schema() -> dict:
    return JudgeBatch.model_json_schema()
