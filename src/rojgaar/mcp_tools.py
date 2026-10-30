"""The narrow, typed tools the host model may use. This is the only door between
the model and your data: no network, no shell, no email, no submit, and nothing
from ``pii.yaml`` is ever returned.

The functions are plain Python so they can be unit-tested without an MCP client;
``mcp_server.py`` registers them with the MCP SDK.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime

from pydantic import ValidationError

from .applications import write_application
from .bank import Bank, load_bank
from .config import Paths
from .daily import load_pii, write_daily_report
from .models import Job
from .preferences import Preferences, load_preferences
from .report import _salary
from .rubric import Judgement, weighted_score
from .store import Store
from .truth import Draft, check_draft, is_ready
from .utils import utcnow

MAX_DESC = 3500


class RojgaarTools:
    def __init__(self, paths: Paths, clock: Callable[[], datetime] = utcnow) -> None:
        self.paths = paths
        self.clock = clock
        self.store = Store(paths.db)

    # -- helpers --------------------------------------------------------------
    def _prefs(self) -> Preferences:
        return load_preferences(self.paths.preferences)

    def _bank(self) -> Bank:
        return load_bank(self.paths.bank)

    def _run_date(self, run_date: str | None) -> str:
        return (
            run_date
            or os.environ.get("ROJGAAR_RUN_DATE")
            or self.store.latest_shortlist_date()
            or self.clock().date().isoformat()
        )

    @staticmethod
    def _compact(job: Job, max_desc: int = MAX_DESC) -> dict:
        return {
            "uid": job.uid,
            "title": job.title,
            "company": job.company,
            "locations": job.locations,
            "remote": job.remote,
            "salary": _salary(job),
            "employment_type": job.employment_type,
            "risk": job.risk,
            "risk_flags": job.risk_flags,
            "description": job.description[:max_desc],
        }

    # -- read tools -------------------------------------------------------------
    def get_shortlist(self, run_date: str | None = None, limit: int = 60) -> dict:
        """Today's shortlist (after hard filters and cheap scoring), most relevant first."""
        rd = self._run_date(run_date)
        jobs = []
        for entry in self.store.get_shortlist(rd)[:limit]:
            job = self.store.get_job(entry["uid"])
            if job:
                jobs.append(self._compact(job))
        return {"run_date": rd, "count": len(jobs), "jobs": jobs}

    def get_job(self, uid: str) -> dict:
        """One job with its full (sanitized) description."""
        job = self.store.get_job(uid)
        if not job:
            return {"error": f"unknown job {uid}"}
        return {**self._compact(job, max_desc=20_000), "apply_url": job.apply_url, "source": job.source}

    def get_profile(self) -> dict:
        """Your PII-free profile summary and ranking preferences."""
        prefs = self._prefs()
        market = next(iter(prefs.active_markets().values()))
        return {
            "profile": self._bank().profile_summary(),
            "ranking": prefs.ranking.model_dump(),
            "wanted_locations": market.locations,
            "seniority": prefs.filters.seniority,
            "work_authorization": market.work_authorization,
        }

    def get_bank(self) -> dict:
        """Verified claims with ids — the only facts a CV may use."""
        bank = self._bank()
        return {
            "roles": [
                {
                    "id": r.id,
                    "org": r.org,
                    "title": r.title,
                    "start": r.start,
                    "end": r.end,
                    "claims": [c.model_dump(exclude={"evidence"}) for c in r.claims if c.verified_by_user],
                }
                for r in bank.roles
            ],
            "skills": sorted(bank.all_skills()),
            "education": [e.model_dump() for e in bank.education],
        }

    # -- write tools ------------------------------------------------------------
    def save_rankings(self, judgements: list[dict], run_date: str | None = None) -> dict:
        """Validate rubric judgements, compute weighted scores in code and store them."""
        rd = self._run_date(run_date)
        weights = self._prefs().ranking.weights
        shortlisted = {e["uid"] for e in self.store.get_shortlist(rd)}
        saved, errors = [], []
        for raw in judgements:
            try:
                j = Judgement.model_validate(raw)
            except ValidationError as exc:
                errors.append({"uid": raw.get("uid") if isinstance(raw, dict) else None, "error": str(exc)})
                continue
            if j.uid not in shortlisted:
                errors.append({"uid": j.uid, "error": "not on this run's shortlist"})
                continue
            score = weighted_score(j, weights)
            self.store.save_ranking(rd, j.uid, score, j.model_dump())
            saved.append({"uid": j.uid, "score": score, "verdict": j.verdict})
        saved.sort(key=lambda s: -s["score"])
        return {"run_date": rd, "saved": len(saved), "ranked": saved, "errors": errors}

    def check_draft(self, draft: dict) -> dict:
        """Run the deterministic truth checks on a draft without saving it."""
        try:
            d = Draft.model_validate(draft)
        except ValidationError as exc:
            return {
                "ready": False,
                "findings": [{"code": "SCHEMA", "severity": "error", "message": str(exc)}],
            }
        findings = check_draft(d, self._bank())
        return {"ready": is_ready(findings), "findings": [f.to_dict() for f in findings]}

    def save_application_draft(self, uid: str, draft: dict, run_date: str | None = None) -> dict:
        """Write the per-job application folder. Blocked drafts are saved but marked blocked."""
        rd = self._run_date(run_date)
        job = self.store.get_job(uid)
        if not job:
            return {"error": f"unknown job {uid}"}
        try:
            d = Draft.model_validate({**draft, "job_uid": uid})
        except ValidationError as exc:
            return {"error": f"draft does not match schema: {exc}"}
        judgement = next((r["judgement"] for r in self.store.get_rankings(rd) if r["uid"] == uid), None)
        result = write_application(
            self.paths.applications,
            rd,
            job,
            d,
            self._bank(),
            judgement,
            self.clock(),
            pii=load_pii(self.paths),
        )
        result["folder"] = os.path.relpath(result["folder"], self.paths.root)
        return result

    def finalize_report(self, run_date: str | None = None) -> dict:
        """Write today's report from the saved rankings."""
        rd = self._run_date(run_date)
        path = write_daily_report(self.store, self.paths, self._prefs(), rd)
        top = [{"uid": r["uid"], "score": r["score"]} for r in self.store.get_rankings(rd)[:5]]
        return {"report": os.path.relpath(path, self.paths.root), "top": top}

    def record_feedback(self, uid: str, rating: str, reason: str | None = None) -> dict:
        """Record your thumbs up/down on a job (rating: up | down)."""
        if rating not in ("up", "down"):
            return {"error": "rating must be 'up' or 'down'"}
        self.store.add_feedback(uid, rating, reason, self.clock())
        return {"ok": True}


TOOL_NAMES = (
    "get_shortlist",
    "get_job",
    "get_profile",
    "get_bank",
    "save_rankings",
    "check_draft",
    "save_application_draft",
    "finalize_report",
    "record_feedback",
)
