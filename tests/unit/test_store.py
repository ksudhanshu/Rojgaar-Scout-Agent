from datetime import timedelta

from helpers import NOW, make_job

from rojgaar.store import Store, age_days


def test_upsert_new_then_seen_keeps_first_seen():
    s = Store()
    job = make_job()
    assert s.upsert_job(job, NOW, keys=["k1"]) == "new"
    later = NOW + timedelta(days=1)
    assert s.upsert_job(job, later) == "seen"
    stored = s.get_job(job.uid)
    assert stored.first_seen.startswith("2026-10-29")
    assert stored.last_seen.startswith("2026-10-30")
    assert s.uid_for_key("k1") == job.uid
    assert s.count_jobs() == 1


def test_duplicate_rows_point_keys_at_canonical():
    s = Store()
    s.upsert_job(make_job(uid="a"), NOW, keys=["ka"])
    s.upsert_job(make_job(uid="b", source="remotive"), NOW, keys=["kb"], duplicate_of="a")
    assert s.uid_for_key("kb") == "a"
    s.add_also_on("a", "remotive")
    assert s.get_job("a").also_on == ["remotive"]
    assert [j.uid for j in s.candidate_jobs(NOW, 30)] == ["a"]


def test_candidate_jobs_respects_age_window():
    s = Store()
    s.upsert_job(make_job(uid="old"), NOW - timedelta(days=40))
    s.upsert_job(make_job(uid="new"), NOW)
    assert [j.uid for j in s.candidate_jobs(NOW, 30)] == ["new"]


def test_runs_and_idempotency_marker():
    s = Store()
    rid = s.start_run("2026-10-29", "claude", NOW)
    assert not s.has_success("2026-10-29")
    s.finish_run(rid, "success", NOW, {"new": 3})
    assert s.has_success("2026-10-29")
    assert s.last_run()["status"] == "success"


def test_fetch_caps():
    s = Store()
    for _ in range(3):
        s.record_fetch("remotive", NOW)
    s.record_fetch("remotive", NOW - timedelta(days=2))
    assert s.fetches_since("remotive", NOW - timedelta(days=1)) == 3


def test_shortlist_rankings_reported_feedback():
    s = Store()
    s.save_shortlist("2026-10-29", [{"uid": "a", "fused": 0.1}, {"uid": "b", "fused": 0.05}])
    assert [e["uid"] for e in s.get_shortlist("2026-10-29")] == ["a", "b"]
    assert s.latest_shortlist_date() == "2026-10-29"
    s.save_ranking("2026-10-29", "b", 0.9, {"verdict": "strong"})
    s.save_ranking("2026-10-29", "a", 0.4, {"verdict": "stretch"})
    assert [r["uid"] for r in s.get_rankings("2026-10-29")] == ["b", "a"]
    s.mark_reported(["a"], "2026-10-28")
    assert s.reported_before("2026-10-29") == {"a"}
    assert s.reported_before("2026-10-28") == set()
    s.add_feedback("a", "down", "too-senior", NOW)
    assert s.feedback()[0]["reason"] == "too-senior"


def test_file_backed_store_persists(tmp_path):
    path = tmp_path / "state" / "x.db"
    s = Store(path)
    s.upsert_job(make_job(), NOW)
    s.close()
    assert Store(path).count_jobs() == 1


def test_age_days_prefers_date_posted():
    job = make_job(date_posted="2026-10-19T15:00:00+00:00")
    assert round(age_days(job, NOW)) == 10
    assert age_days(make_job(date_posted=None), NOW) is None
