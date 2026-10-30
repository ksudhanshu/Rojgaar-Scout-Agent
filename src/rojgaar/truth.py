"""Deterministic truth checks for tailored CVs and cover letters.

A 2026 study found strict prompts alone still left a fabrication in half of
tailored resumes. These checks are the layer that never gets tired: every
bullet must cite claim IDs from ``bank.yaml``, and numbers, skills, qualifiers
and timeline must agree with those claims. Any ``error`` blocks the draft.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from pydantic import BaseModel, Field

from .bank import Bank, Claim, Role

# Technologies we check for unsupported mentions and anachronisms (first stable/public year).
TECH_FIRST_YEAR: dict[str, int] = {
    "python": 1991, "java": 1995, "javascript": 1995, "typescript": 2012, "golang": 2012,
    "rust": 2015, "kotlin": 2016, "swift": 2014, "scala": 2004, "ruby": 1995, "c#": 2000, "c++": 1985,
    "react": 2013, "vue": 2014, "angular": 2016, "node.js": 2009, "nodejs": 2009, "next.js": 2016,
    "docker": 2013, "kubernetes": 2014, "terraform": 2014, "ansible": 2012, "helm": 2016,
    "aws": 2006, "gcp": 2008, "azure": 2010, "kafka": 2011, "spark": 2014, "airflow": 2015,
    "postgresql": 1996, "postgres": 1996, "mysql": 1995, "mongodb": 2009, "redis": 2009,
    "elasticsearch": 2010, "snowflake": 2014, "dbt": 2016, "graphql": 2015, "grpc": 2016,
    "pytorch": 2016, "tensorflow": 2015, "langchain": 2022, "chatgpt": 2022, "gpt-4": 2023, "llm": 2018,
}  # fmt: skip
STRONG_FORMS = {
    "co-led": ("led",),
    "co-founded": ("founded",),
    "co-authored": ("authored", "wrote"),
    "co-designed": ("designed",),
    "helped": ("led", "drove", "owned", "spearheaded", "built", "moved"),
    "assisted": ("led", "drove", "owned"),
    "contributed": ("led", "built", "owned"),
    "supported": ("led", "owned"),
}
BANNED_PHRASES = [
    "passionate",
    "leverage",
    "delve",
    "i am writing to express",
    "dynamic team",
    "synergy",
    "hit the ground running",
    "results-driven",
    "go-getter",
    "think outside the box",
    "tapestry",
]
NUMBER = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)(\s?%|x\b|k\b|m\b)?", re.I)


class Bullet(BaseModel):
    text: str
    src: list[str] = Field(default_factory=list)


class Section(BaseModel):
    title: str
    bullets: list[Bullet] = Field(default_factory=list)


class CoverLetter(BaseModel):
    motivation: str | None = None
    paragraphs: list[Bullet] = Field(default_factory=list)
    closing: str | None = None


class Draft(BaseModel):
    job_uid: str
    summary: Bullet | None = None
    sections: list[Section] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    cover_letter: CoverLetter | None = None


@dataclass
class Finding:
    location: str
    code: str
    severity: str  # "error" | "warning"
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _numbers(text: str) -> set[float]:
    out = set()
    for m in NUMBER.finditer(text):
        try:
            value = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        suffix = (m.group(2) or "").strip().lower()
        out.add(value)
        if suffix == "k":
            out.add(value * 1000)
        if suffix == "m":
            out.add(value * 1_000_000)
    return out


def _allowed_numbers(claims: list[tuple[Claim, Role]]) -> set[float]:
    allowed: set[float] = set()
    for claim, role in claims:
        allowed |= _numbers(claim.text)
        for alt in claim.alt_phrasings:
            allowed |= _numbers(alt)
        for metric in claim.metrics:
            allowed.add(float(metric.value))
            allowed |= _numbers(metric.unit)
        for q in claim.qualifiers:
            allowed |= _numbers(q)
        allowed.add(float(role.start_year()))
        if role.end_year():
            allowed.add(float(role.end_year()))  # type: ignore[arg-type]
    return allowed


def _mentions(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9+#])", text.lower()) is not None


def check_bullet(bullet: Bullet, where: str, bank: Bank) -> list[Finding]:
    findings: list[Finding] = []
    index = bank.claim_index()
    if not bullet.src:
        return [Finding(where, "MISSING_SRC", "error", "bullet cites no source claim")]
    cited: list[tuple[Claim, Role]] = []
    for cid in bullet.src:
        if cid not in index:
            findings.append(Finding(where, "UNKNOWN_SRC", "error", f"claim id {cid!r} is not in bank.yaml"))
        else:
            claim, role = index[cid]
            if not claim.verified_by_user:
                findings.append(
                    Finding(where, "UNVERIFIED_SRC", "error", f"claim {cid} is not verified_by_user")
                )
            cited.append((claim, role))
    if not cited:
        return findings

    allowed = _allowed_numbers(cited)
    for value in sorted(_numbers(bullet.text)):
        if value not in allowed:
            findings.append(
                Finding(
                    where, "NUMBER_MISMATCH", "error", f"number {value:g} does not appear in the cited claims"
                )
            )

    source_text = " ".join(c.text + " " + " ".join(c.skills + c.alt_phrasings) for c, _ in cited).lower()
    known = bank.all_skills()
    for term in TECH_FIRST_YEAR:
        if _mentions(bullet.text, term) and term not in known and not _mentions(source_text, term):
            findings.append(
                Finding(where, "UNKNOWN_SKILL", "error", f"{term!r} is not in your bank or the cited claims")
            )

    low = bullet.text.lower()
    for claim, _ in cited:
        for q in claim.qualifiers:
            qn = q.lower()
            if qn in STRONG_FORMS and qn not in low and any(_mentions(low, s) for s in STRONG_FORMS[qn]):
                findings.append(
                    Finding(
                        where,
                        "QUALIFIER_DROPPED",
                        "error",
                        f"claim {claim.id} says {q!r}; the bullet overstates it",
                    )
                )

    role = cited[0][1]
    last_year = role.end_year()
    if last_year:
        for term, first in TECH_FIRST_YEAR.items():
            if _mentions(bullet.text, term) and first > last_year:
                findings.append(
                    Finding(
                        where,
                        "TIMELINE",
                        "error",
                        f"{term!r} (from {first}) cannot appear in a role that ended {last_year}",
                    )
                )
    return findings


def check_draft(draft: Draft | dict, bank: Bank) -> list[Finding]:
    d = draft if isinstance(draft, Draft) else Draft.model_validate(draft)
    findings: list[Finding] = []
    if d.summary:
        findings += check_bullet(d.summary, "summary", bank)
    for si, section in enumerate(d.sections):
        for bi, bullet in enumerate(section.bullets):
            findings += check_bullet(bullet, f"sections[{si}].bullets[{bi}]", bank)

    known = bank.all_skills()
    for skill in d.skills:
        if skill.lower() not in known:
            findings.append(Finding("skills", "UNKNOWN_SKILL", "error", f"{skill!r} is not in your bank"))

    if d.cover_letter:
        cl = d.cover_letter
        for pi, para in enumerate(cl.paragraphs):
            findings += check_bullet(para, f"cover_letter.paragraphs[{pi}]", bank)
        if not (cl.motivation or "").strip():
            findings.append(
                Finding(
                    "cover_letter.motivation",
                    "MOTIVATION_MISSING",
                    "warning",
                    "write or confirm the motivation line yourself",
                )
            )
        full = " ".join([cl.motivation or ""] + [p.text for p in cl.paragraphs] + [cl.closing or ""])
        words = len(full.split())
        if words and not 250 <= words <= 350:
            findings.append(Finding("cover_letter", "LENGTH", "warning", f"{words} words; aim for 250–350"))
        for phrase in BANNED_PHRASES:
            if phrase in full.lower():
                findings.append(
                    Finding("cover_letter", "PHRASE_LINT", "warning", f"avoid stock phrase {phrase!r}")
                )
    return findings


def is_ready(findings: list[Finding]) -> bool:
    return not any(f.severity == "error" for f in findings)
