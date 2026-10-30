"""One folder per job with everything you need to decide and apply yourself.

applications/<date>_<company>_<role>/
  jd.md · fit-report.md · cv.md · cover-letter.md · review.md · status.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .bank import Bank
from .models import Job
from .render import cover_letter_to_markdown, draft_to_markdown, fill_placeholders
from .truth import Draft, Finding, check_draft, is_ready
from .utils import iso, slugify

STATUS_ICON = {"met": "✔", "partial": "≈", "missing": "✘"}


def folder_for(root: Path, run_date: str, job: Job) -> Path:
    name = f"{run_date}_{slugify(job.company, 24)}_{slugify(job.title, 32)}"
    path = (root / name).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("refusing to write outside the applications folder")
    return path


def fit_report(job: Job, judgement: dict | None) -> str:
    lines = [f"# Fit report — {job.title} at {job.company}", ""]
    if not judgement:
        return "\n".join(lines + ["No ranking yet."]) + "\n"
    lines.append(f"**Verdict:** {judgement.get('verdict')}  ")
    lines.append(f"**Scores:** {judgement.get('scores')}")
    lines.append("")
    reqs = judgement.get("requirements") or []
    if reqs:
        lines += ["| | Requirement | Evidence |", "|---|---|---|"]
        for r in reqs:
            lines.append(
                f"| {STATUS_ICON.get(r['status'], '?')} | {r['text']} | {', '.join(r.get('evidence', [])) or '—'} |"
            )
        lines.append("")
    if judgement.get("gaps"):
        lines += ["## Gaps (never added to your CV)", *[f"- {g}" for g in judgement["gaps"]], ""]
    return "\n".join(lines) + "\n"


def review_markdown(draft: Draft, bank: Bank, findings: list[Finding]) -> str:
    index = bank.claim_index()
    lines = ["# Review — every bullet beside its source", ""]
    ready = is_ready(findings)
    lines.append(f"**Status:** {'READY for your review' if ready else 'BLOCKED — fix the errors below'}")
    lines.append("")
    for section in draft.sections:
        lines.append(f"## {section.title}")
        for b in section.bullets:
            lines.append(f"- **Draft:** {b.text}")
            for cid in b.src:
                if cid in index:
                    claim, _ = index[cid]
                    q = f" _(qualifiers: {', '.join(claim.qualifiers)})_" if claim.qualifiers else ""
                    lines.append(f"  - **Source {cid}:** {claim.text}{q}")
                else:
                    lines.append(f"  - **Source {cid}:** NOT FOUND")
        lines.append("")
    if findings:
        lines += ["## Findings", "| Severity | Where | Check | Detail |", "|---|---|---|---|"]
        for f in findings:
            lines.append(f"| {f.severity} | {f.location} | {f.code} | {f.message} |")
    return "\n".join(lines) + "\n"


def write_application(
    root: Path,
    run_date: str,
    job: Job,
    draft: Draft,
    bank: Bank,
    judgement: dict | None,
    now: datetime,
    pii: dict[str, str] | None = None,
) -> dict:
    findings = check_draft(draft, bank)
    ready = is_ready(findings)
    folder = folder_for(root, run_date, job)
    folder.mkdir(parents=True, exist_ok=True)
    pii = pii or {}
    (folder / "jd.md").write_text(
        f"# {job.title} — {job.company}\n\n{job.location_text()} · {job.remote}\n\n{job.apply_url}\n\n{job.description}\n",
        encoding="utf-8",
    )
    (folder / "fit-report.md").write_text(fit_report(job, judgement), encoding="utf-8")
    (folder / "draft.json").write_text(draft.model_dump_json(indent=2), encoding="utf-8")
    (folder / "cv.md").write_text(fill_placeholders(draft_to_markdown(draft, bank), pii), encoding="utf-8")
    if draft.cover_letter:
        (folder / "cover-letter.md").write_text(
            fill_placeholders(cover_letter_to_markdown(draft), pii), encoding="utf-8"
        )
    (folder / "review.md").write_text(review_markdown(draft, bank, findings), encoding="utf-8")
    status_path = folder / "status.json"
    history = json.loads(status_path.read_text())["history"] if status_path.exists() else []
    state = "ready" if ready else "blocked"
    history.append({"state": state, "at": iso(now), "by": "rojgaar"})
    status = {
        "job_uid": job.uid,
        "state": state,
        "history": history,
        "verdict": (judgement or {}).get("verdict"),
        "submitted_by_user": None,
    }
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return {"folder": str(folder), "ready": ready, "findings": [f.to_dict() for f in findings]}
