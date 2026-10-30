"""``rojgaar run-daily``: the one command the OS scheduler calls.

Idempotent (a second run the same day does nothing), bounded (lock, timeout,
budget cap) and safe (no bypass flags). The no-LLM report is written first, so
a host failure still leaves you a useful report.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from .bank import BankError, load_bank
from .config import Paths
from .hosts import HostOptions, build_command, parse_output
from .http import PoliteClient
from .models import Job
from .pipeline import build_shortlist, fetch_all
from .preferences import Preferences, load_preferences
from .registry import load_companies
from .report import render_report
from .scoring import Embedder
from .store import Store
from .utils import utcnow


class LockedError(RuntimeError):
    pass


class RunLock:
    """Exclusive lock file holding the PID; stale locks from dead processes are cleared."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> RunLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return self
            except FileExistsError:
                if self._stale():
                    self.path.unlink(missing_ok=True)
                    continue
                raise LockedError(f"another run holds {self.path}") from None
        raise LockedError(f"could not acquire {self.path}")

    def _stale(self) -> bool:
        try:
            pid = int(self.path.read_text().strip() or "0")
        except (OSError, ValueError):
            return True
        if pid <= 0:
            return True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        return False

    def __exit__(self, *exc: object) -> None:
        self.path.unlink(missing_ok=True)


def load_pii(paths: Paths) -> dict[str, str]:
    if not paths.pii.exists():
        return {}
    data = yaml.safe_load(paths.pii.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items() if v is not None}


def write_daily_report(
    store: Store, paths: Paths, prefs: Preferences, run_date: str, stats: dict | None = None
) -> Path:
    shortlist = store.get_shortlist(run_date)
    rankings = store.get_rankings(run_date)
    uids = [r["uid"] for r in rankings] or [s["uid"] for s in shortlist]
    jobs: dict[str, Job] = {}
    for uid in uids:
        job = store.get_job(uid)
        if job:
            jobs[uid] = job
    md = render_report(run_date, jobs, shortlist, rankings or None, prefs.report.top_n, stats)
    paths.reports.mkdir(parents=True, exist_ok=True)
    path = paths.reports / f"{run_date}.md"
    path.write_text(md, encoding="utf-8")
    store.mark_reported(uids[: prefs.report.top_n], run_date)
    return path


@dataclass
class RunResult:
    status: str  # success | partial | skipped | failed
    run_date: str
    report_path: Path | None = None
    summary: dict = field(default_factory=dict)
    message: str = ""


def run_daily(
    paths: Paths,
    host: str | None = None,
    now: datetime | None = None,
    run_date: str | None = None,
    client: PoliteClient | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    timeout: float = 1800,
    force: bool = False,
    embedder: Embedder | None = None,
    host_options: HostOptions | None = None,
) -> RunResult:
    paths.ensure()
    now = now or utcnow()
    run_date = run_date or now.astimezone().date().isoformat()
    prefs = load_preferences(paths.preferences)
    try:
        bank_skills = sorted(load_bank(paths.bank).all_skills())
    except BankError:
        bank_skills = []

    store = Store(paths.db)
    own_client = client is None
    client = client or PoliteClient()
    try:
        with RunLock(paths.lock):
            if not force and store.has_success(run_date):
                return RunResult(
                    "skipped", run_date, paths.reports / f"{run_date}.md", message="already ran today"
                )
            run_id = store.start_run(run_date, host, now)
            companies = load_companies(paths.companies)
            fetch = fetch_all(prefs, store, client, companies, now)
            totals = fetch.totals()
            sl = build_shortlist(prefs, store, run_date, now, bank_skills, embedder)
            stats = {**totals, "passed_filters": sl.passed, "shortlist": len(sl.entries)}
            report = write_daily_report(store, paths, prefs, run_date, stats)
            status, message = "success", "report written (no LLM)"

            if host and host != "none" and sl.entries:
                opts = host_options or HostOptions(drafts=prefs.report.drafts_per_day)
                cmd = build_command(host, opts)
                env = {**os.environ, "ROJGAAR_HOME": str(paths.root), "ROJGAAR_RUN_DATE": run_date}
                try:
                    proc = runner(
                        cmd, capture_output=True, text=True, timeout=timeout, cwd=str(paths.root), env=env
                    )
                    out = parse_output(proc.stdout)
                    stats["host"] = {"name": host, "returncode": proc.returncode, "output": out}
                    if proc.returncode != 0:
                        status, message = (
                            "partial",
                            f"{host} exited with {proc.returncode}; no-LLM report kept",
                        )
                    else:
                        message = f"{host} ranked {len(store.get_rankings(run_date))} jobs"
                except FileNotFoundError:
                    status, message = "partial", f"{host} is not installed or not on PATH; no-LLM report kept"
                except subprocess.TimeoutExpired:
                    status, message = "partial", f"{host} timed out after {timeout:.0f}s; no-LLM report kept"
                if store.get_rankings(run_date):
                    report = write_daily_report(store, paths, prefs, run_date, stats)

            stats["sources"] = {
                k: {"new": v.new, "errors": v.errors, "skipped": v.skipped}
                for k, v in fetch.per_source.items()
            }
            store.finish_run(run_id, status, utcnow(), stats)
            return RunResult(status, run_date, report, stats, message)
    finally:
        if own_client:
            client.close()
        store.close()
