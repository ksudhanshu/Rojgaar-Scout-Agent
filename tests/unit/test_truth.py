"""Planted-fabrication tests: every fabrication type must be caught by code."""

import pytest

from rojgaar.bank import example_bank_text, parse_bank
from rojgaar.truth import Draft, check_draft, is_ready

BANK = parse_bank(example_bank_text())


def draft(*bullets, skills=None, cover=None):
    return Draft.model_validate(
        {
            "job_uid": "j1",
            "sections": [{"title": "Experience", "bullets": [{"text": t, "src": s} for t, s in bullets]}],
            "skills": skills or [],
            "cover_letter": cover,
        }
    )


def codes(findings):
    return [f.code for f in findings]


def test_clean_draft_is_ready():
    d = draft(
        (
            "Co-led a 4-person migration of the payments ledger to PostgreSQL, cutting p99 latency 40%",
            ["exp.acme.b1"],
        ),
        ("Built a Python reconciliation service handling 2 million transactions a day", ["exp.acme.b2"]),
        ("Helped move 30 services onto Kubernetes", ["exp.beta.b1"]),
        skills=["Python", "PostgreSQL", "Kubernetes"],
    )
    findings = check_draft(d, BANK)
    assert findings == []
    assert is_ready(findings)


@pytest.mark.parametrize(
    "text,src,expected",
    [
        ("Co-led ledger migration cutting p99 latency 60%", ["exp.acme.b1"], "NUMBER_MISMATCH"),
        ("Led the migration of the payments ledger to PostgreSQL", ["exp.acme.b1"], "QUALIFIER_DROPPED"),
        ("Drove the move of 30 services onto Kubernetes", ["exp.beta.b1"], "QUALIFIER_DROPPED"),
        ("Built a Rust reconciliation service", ["exp.acme.b2"], "UNKNOWN_SKILL"),
        ("Helped move 30 services onto Kubernetes using LangChain agents", ["exp.beta.b1"], "UNKNOWN_SKILL"),
        ("Shipped features", [], "MISSING_SRC"),
        ("Shipped features", ["exp.nope"], "UNKNOWN_SRC"),
    ],
)
def test_planted_fabrications_are_caught(text, src, expected):
    findings = check_draft(draft((text, src)), BANK)
    assert expected in codes(findings)
    assert not is_ready(findings)


def test_unverified_claim_cannot_be_used():
    bank = parse_bank(
        """
roles:
  - {id: r1, org: A, title: T, start: "2019", end: "2021", claims: [{id: c1, text: Wrote docs}]}
"""
    )
    assert "UNVERIFIED_SRC" in codes(check_draft(draft(("Wrote docs", ["c1"])), bank))


def test_timeline_anachronism_caught():
    bank = parse_bank(
        """
skills: [Kubernetes]
roles:
  - {id: r1, org: A, title: T, start: "2010", end: "2012", claims: [{id: c1, text: Ran servers, verified_by_user: true}]}
"""
    )
    findings = check_draft(draft(("Ran servers on Kubernetes", ["c1"])), bank)
    assert "TIMELINE" in codes(findings)


def test_skills_section_only_lists_bank_skills():
    findings = check_draft(
        draft(("Helped move 30 services onto Kubernetes", ["exp.beta.b1"]), skills=["Kubernetes", "Rust"]),
        BANK,
    )
    assert [f.message for f in findings if f.code == "UNKNOWN_SKILL"] == ["'Rust' is not in your bank"]


def test_role_years_are_allowed_numbers():
    findings = check_draft(
        draft(("Since 2022, built a Python service for 2 million transactions a day", ["exp.acme.b2"])), BANK
    )
    assert findings == []


def test_cover_letter_checks():
    cover = {
        "motivation": None,
        "paragraphs": [
            {"text": "I am passionate about payments and built a Python service.", "src": ["exp.acme.b2"]}
        ],
        "closing": "Thanks.",
    }
    findings = check_draft(
        draft(("Helped move 30 services onto Kubernetes", ["exp.beta.b1"]), cover=cover), BANK
    )
    got = codes(findings)
    assert "MOTIVATION_MISSING" in got
    assert "PHRASE_LINT" in got
    assert "LENGTH" in got
    assert is_ready(findings)  # warnings only
