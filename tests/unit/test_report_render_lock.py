import os
from pathlib import Path

import pytest
from helpers import NOW, make_job

from rojgaar.applications import folder_for, write_application
from rojgaar.bank import example_bank_text, parse_bank
from rojgaar.daily import LockedError, RunLock
from rojgaar.models import Salary
from rojgaar.render import cover_letter_to_markdown, draft_to_markdown, draft_to_rendercv, fill_placeholders
from rojgaar.report import render_report
from rojgaar.truth import Draft

BANK = parse_bank(example_bank_text())
DRAFT = Draft.model_validate(
    {
        "job_uid": "greenhouse:acme:1",
        "summary": {"text": "Backend engineer who co-led a ledger migration.", "src": ["exp.acme.b1"]},
        "sections": [
            {
                "title": "Experience",
                "bullets": [{"text": "Helped move 30 services onto Kubernetes", "src": ["exp.beta.b1"]}],
            }
        ],
        "skills": ["Kubernetes"],
        "cover_letter": {
            "motivation": None,
            "paragraphs": [{"text": "I built a Python service.", "src": ["exp.acme.b2"]}],
        },
    }
)


def test_report_with_rankings():
    job = make_job(salary=Salary(min=180000, max=220000), also_on=["remotive"])
    md = render_report(
        "2026-10-29",
        {job.uid: job},
        [{"uid": job.uid}],
        [
            {
                "uid": job.uid,
                "score": 0.91,
                "judgement": {"verdict": "strong", "reasons": ["Go match"], "gaps": ["No Rust"]},
            }
        ],
    )
    assert "Best matches" in md
    assert "Senior Backend Engineer — Acme Fintech" in md
    assert "$180k–$220k/yr" in md
    assert "score 0.91" in md and "Go match" in md and "No Rust" in md
    assert "also on remotive" in md
    assert "never submits" in md


def test_report_without_llm_and_empty():
    job = make_job(risk="high", risk_flags=["hidden_text"])
    md = render_report(
        "2026-10-29", {job.uid: job}, [{"uid": job.uid, "bm25_rank": 1}], None, stats={"fetched": 5, "new": 2}
    )
    assert "cheap scoring only" in md
    assert "high risk" in md and "hidden_text" in md
    assert "Fetched 5 postings" in md
    assert "No new matching jobs" in render_report("2026-10-29", {}, [], None)


def test_placeholders_are_filled_locally():
    assert fill_placeholders("Hi {{NAME}} {{UNKNOWN}}", {"NAME": "Priya"}) == "Hi Priya {{UNKNOWN}}"
    md = draft_to_markdown(DRAFT, BANK)
    assert md.startswith("# {{NAME}}")
    assert "- Helped move 30 services onto Kubernetes" in md
    assert "B.S. Computer Science" in md
    assert "[WRITE OR CONFIRM YOUR MOTIVATION LINE]" in cover_letter_to_markdown(DRAFT)


def test_rendercv_document_shape():
    doc = draft_to_rendercv(DRAFT, BANK, {"NAME": "Priya Example", "EMAIL": "p@example.com"})
    assert doc["cv"]["name"] == "Priya Example"
    assert doc["cv"]["sections"]["experience"][0]["bullet"].startswith("Helped")
    assert doc["design"]["theme"] == "classic"


def test_write_application_folder(tmp_path):
    job = make_job()
    result = write_application(
        tmp_path,
        "2026-10-29",
        job,
        DRAFT,
        BANK,
        {"verdict": "strong", "requirements": [{"text": "Go", "status": "met", "evidence": ["exp.acme.b1"]}]},
        NOW,
        pii={"NAME": "Priya"},
    )
    folder = Path(result["folder"])
    assert result["ready"] is True
    for name in (
        "jd.md",
        "fit-report.md",
        "cv.md",
        "cover-letter.md",
        "review.md",
        "status.json",
        "draft.json",
    ):
        assert (folder / name).exists(), name
    assert (folder / "cv.md").read_text().startswith("# Priya")
    assert "✔ | Go" in (folder / "fit-report.md").read_text()
    assert "Source exp.beta.b1" in (folder / "review.md").read_text()


def test_folder_names_are_safe(tmp_path):
    job = make_job(company="../../etc", title="passwd")
    assert folder_for(tmp_path, "2026-10-29", job).parent == tmp_path.resolve()


def test_lock_is_exclusive_and_released(tmp_path):
    lock = tmp_path / "run.lock"
    with RunLock(lock), pytest.raises(LockedError), RunLock(lock):
        pass
    assert not lock.exists()


def test_stale_lock_is_cleared(tmp_path):
    lock = tmp_path / "run.lock"
    lock.write_text("999999999")  # no such process
    with RunLock(lock):
        assert lock.read_text() == str(os.getpid())
