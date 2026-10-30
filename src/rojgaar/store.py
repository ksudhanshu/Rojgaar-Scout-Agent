"""SQLite store: one local file, no server.

``first_seen`` / ``last_seen`` power "new today", staleness and repost detection.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

from .models import Job
from .utils import iso, parse_dt

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  uid TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  company TEXT NOT NULL,
  title TEXT NOT NULL,
  data TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  duplicate_of TEXT
);
CREATE INDEX IF NOT EXISTS jobs_first_seen ON jobs(first_seen);
CREATE INDEX IF NOT EXISTS jobs_company ON jobs(company);
CREATE TABLE IF NOT EXISTS job_keys (
  key TEXT PRIMARY KEY,
  uid TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_date TEXT NOT NULL,
  status TEXT NOT NULL,
  host TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  summary TEXT
);
CREATE TABLE IF NOT EXISTS source_fetches (
  source TEXT NOT NULL,
  at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shortlists (
  run_date TEXT NOT NULL,
  uid TEXT NOT NULL,
  rank INTEGER NOT NULL,
  scores TEXT NOT NULL,
  PRIMARY KEY (run_date, uid)
);
CREATE TABLE IF NOT EXISTS rankings (
  run_date TEXT NOT NULL,
  uid TEXT NOT NULL,
  score REAL NOT NULL,
  judgement TEXT NOT NULL,
  PRIMARY KEY (run_date, uid)
);
CREATE TABLE IF NOT EXISTS reported (
  uid TEXT PRIMARY KEY,
  run_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  uid TEXT NOT NULL,
  rating TEXT NOT NULL,
  reason TEXT,
  at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # The MCP server may call tools from a worker thread; access is serialized per call.
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- jobs ---------------------------------------------------------------
    def get_job(self, uid: str) -> Job | None:
        row = self.conn.execute(
            "SELECT data, first_seen, last_seen, duplicate_of FROM jobs WHERE uid=?", (uid,)
        ).fetchone()
        return self._row_to_job(row) if row else None

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        job = Job.model_validate_json(row["data"])
        job.first_seen = row["first_seen"]
        job.last_seen = row["last_seen"]
        job.duplicate_of = row["duplicate_of"]
        return job

    def upsert_job(
        self, job: Job, now: datetime, keys: Iterable[str] = (), duplicate_of: str | None = None
    ) -> str:
        """Insert or refresh a job. Returns ``"new"`` or ``"seen"``."""
        ts = iso(now)
        existing = self.conn.execute("SELECT first_seen FROM jobs WHERE uid=?", (job.uid,)).fetchone()
        data = job.model_dump_json(exclude={"first_seen", "last_seen", "duplicate_of"})
        if existing:
            self.conn.execute("UPDATE jobs SET data=?, last_seen=? WHERE uid=?", (data, ts, job.uid))
            status = "seen"
        else:
            self.conn.execute(
                "INSERT INTO jobs(uid, source, company, title, data, first_seen, last_seen, duplicate_of) VALUES (?,?,?,?,?,?,?,?)",
                (job.uid, job.source, job.company, job.title, data, ts, ts, duplicate_of),
            )
            status = "new"
        for key in keys:
            self.conn.execute(
                "INSERT OR IGNORE INTO job_keys(key, uid) VALUES (?, ?)", (key, duplicate_of or job.uid)
            )
        self.conn.commit()
        return status

    def touch(self, uid: str, now: datetime) -> None:
        self.conn.execute("UPDATE jobs SET last_seen=? WHERE uid=?", (iso(now), uid))
        self.conn.commit()

    def uid_for_key(self, key: str) -> str | None:
        row = self.conn.execute("SELECT uid FROM job_keys WHERE key=?", (key,)).fetchone()
        return row["uid"] if row else None

    def add_also_on(self, uid: str, source: str) -> None:
        job = self.get_job(uid)
        if job and source != job.source and source not in job.also_on:
            job.also_on.append(source)
            data = job.model_dump_json(exclude={"first_seen", "last_seen", "duplicate_of"})
            self.conn.execute("UPDATE jobs SET data=? WHERE uid=?", (data, uid))
            self.conn.commit()

    def company_jobs(self, company: str, exclude_uid: str | None = None) -> list[Job]:
        rows = self.conn.execute(
            "SELECT data, first_seen, last_seen, duplicate_of FROM jobs WHERE lower(company)=lower(?) AND duplicate_of IS NULL AND uid != ?",
            (company, exclude_uid or ""),
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def candidate_jobs(self, now: datetime, max_age_days: int) -> list[Job]:
        """Canonical (non-duplicate) jobs first seen within the age window."""
        cutoff = iso(now - timedelta(days=max_age_days))
        rows = self.conn.execute(
            "SELECT data, first_seen, last_seen, duplicate_of FROM jobs WHERE duplicate_of IS NULL AND first_seen >= ? ORDER BY first_seen DESC",
            (cutoff,),
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def count_jobs(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    # -- per-source fetch caps ---------------------------------------------
    def record_fetch(self, source: str, now: datetime) -> None:
        self.conn.execute("INSERT INTO source_fetches(source, at) VALUES (?, ?)", (source, iso(now)))
        self.conn.commit()

    def fetches_since(self, source: str, since: datetime) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM source_fetches WHERE source=? AND at >= ?", (source, iso(since))
        ).fetchone()[0]

    # -- runs ---------------------------------------------------------------
    def start_run(self, run_date: str, host: str | None, now: datetime) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs(run_date, status, host, started_at) VALUES (?, 'running', ?, ?)",
            (run_date, host, iso(now)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_run(self, run_id: int, status: str, now: datetime, summary: dict) -> None:
        self.conn.execute(
            "UPDATE runs SET status=?, finished_at=?, summary=? WHERE id=?",
            (status, iso(now), json.dumps(summary), run_id),
        )
        self.conn.commit()

    def has_success(self, run_date: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM runs WHERE run_date=? AND status IN ('success', 'partial')", (run_date,)
        ).fetchone()
        return row is not None

    def last_run(self) -> dict | None:
        row = self.conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    # -- shortlist, rankings, reports --------------------------------------
    def save_shortlist(self, run_date: str, entries: list[dict]) -> None:
        self.conn.execute("DELETE FROM shortlists WHERE run_date=?", (run_date,))
        for i, e in enumerate(entries, 1):
            self.conn.execute(
                "INSERT INTO shortlists(run_date, uid, rank, scores) VALUES (?,?,?,?)",
                (run_date, e["uid"], i, json.dumps(e)),
            )
        self.conn.commit()

    def get_shortlist(self, run_date: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT scores FROM shortlists WHERE run_date=? ORDER BY rank", (run_date,)
        ).fetchall()
        return [json.loads(r["scores"]) for r in rows]

    def latest_shortlist_date(self) -> str | None:
        row = self.conn.execute("SELECT MAX(run_date) AS d FROM shortlists").fetchone()
        return row["d"] if row and row["d"] else None

    def save_ranking(self, run_date: str, uid: str, score: float, judgement: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO rankings(run_date, uid, score, judgement) VALUES (?,?,?,?)",
            (run_date, uid, score, json.dumps(judgement)),
        )
        self.conn.commit()

    def get_rankings(self, run_date: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT uid, score, judgement FROM rankings WHERE run_date=? ORDER BY score DESC", (run_date,)
        ).fetchall()
        return [{"uid": r["uid"], "score": r["score"], "judgement": json.loads(r["judgement"])} for r in rows]

    def mark_reported(self, uids: Iterable[str], run_date: str) -> None:
        for uid in uids:
            self.conn.execute("INSERT OR IGNORE INTO reported(uid, run_date) VALUES (?, ?)", (uid, run_date))
        self.conn.commit()

    def reported_before(self, run_date: str) -> set[str]:
        rows = self.conn.execute("SELECT uid FROM reported WHERE run_date < ?", (run_date,)).fetchall()
        return {r["uid"] for r in rows}

    # -- feedback -----------------------------------------------------------
    def add_feedback(self, uid: str, rating: str, reason: str | None, now: datetime) -> None:
        self.conn.execute(
            "INSERT INTO feedback(uid, rating, reason, at) VALUES (?,?,?,?)", (uid, rating, reason, iso(now))
        )
        self.conn.commit()

    def feedback(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM feedback ORDER BY id").fetchall()]


def age_days(job: Job, now: datetime) -> float | None:
    when = parse_dt(job.date_posted) or parse_dt(job.first_seen)
    if not when:
        return None
    return (now - when).total_seconds() / 86400
