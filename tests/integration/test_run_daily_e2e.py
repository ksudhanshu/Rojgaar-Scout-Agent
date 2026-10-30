"""``run_daily`` end to end, with a fake host CLI that behaves like an agent:
it uses only the rojgaar MCP tool functions to rank, draft and finalize."""

import json
import stat
import subprocess
import sys
import textwrap

import pytest
from helpers import NOW, RUN_DATE

from rojgaar.daily import run_daily
from rojgaar.store import Store

pytestmark = pytest.mark.integration

FAKE_AGENT = textwrap.dedent(
    """
    #!{python}
    import json, sys
    from rojgaar.config import get_paths
    from rojgaar.mcp_tools import RojgaarTools

    args = sys.argv[1:]
    # The scheduled run must never use permission-bypass flags.
    for bad in ("--dangerously-skip-permissions", "bypassPermissions", "--yolo"):
        assert bad not in args, bad
    assert args[0] == "-p" and "dontAsk" in args, args

    tools = RojgaarTools(get_paths())
    shortlist = tools.get_shortlist()["jobs"]
    judgements = []
    for job in shortlist:
        senior = "senior" in job["title"].lower() or "staff" in job["title"].lower()
        judgements.append({{
            "uid": job["uid"],
            "scores": {{"title": 3 if "backend" in job["title"].lower() else 2, "must_have": 2,
                        "seniority": 3 if senior else 1, "logistics": 3, "preference": 1}},
            "verdict": "strong" if senior else "stretch",
            "reasons": ["Backend + Go match"], "gaps": ["No Kafka at scale"],
            "requirements": [{{"text": "PostgreSQL", "status": "met", "evidence": ["exp.acme.b1"]}}],
        }})
    judgements.append({{"uid": "not:on:shortlist", "scores": judgements[0]["scores"], "verdict": "good"}})
    saved = tools.save_rankings(judgements)
    assert saved["errors"] and saved["errors"][0]["uid"] == "not:on:shortlist"
    top = saved["ranked"][0]["uid"]
    draft = {{
        "summary": {{"text": "Backend engineer who co-led a payments ledger migration to PostgreSQL.", "src": ["exp.acme.b1"]}},
        "sections": [{{"title": "Experience", "bullets": [
            {{"text": "Co-led a 4-person migration of the payments ledger to PostgreSQL, cutting p99 latency 40%", "src": ["exp.acme.b1"]}},
            {{"text": "Built a Python service that reconciles 2 million transactions a day", "src": ["exp.acme.b2"]}}]}}],
        "skills": ["Python", "PostgreSQL", "Go"],
    }}
    assert tools.check_draft({{**draft, "job_uid": top}})["ready"]
    result = tools.save_application_draft(top, draft)
    assert result["ready"], result
    tools.finalize_report()
    print(json.dumps({{"type": "result", "result": "ranked " + str(saved["saved"]) + " jobs"}}))
    """
).lstrip()


def write_exe(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    exe = write_exe(tmp_path, "fake-claude", FAKE_AGENT.format(python=sys.executable))
    monkeypatch.setenv("ROJGAAR_CLAUDE_BIN", str(exe))
    return exe


def test_no_llm_run_then_idempotent_skip(home, client):
    first = run_daily(home, host="none", now=NOW, run_date=RUN_DATE, client=client)
    assert first.status == "success"
    assert first.report_path.exists()
    assert first.summary["new"] == 13 and first.summary["passed_filters"] == 9
    second = run_daily(home, host="none", now=NOW, run_date=RUN_DATE, client=client)
    assert second.status == "skipped"
    assert not home.lock.exists()


def test_host_ranks_drafts_and_finalizes(home, client, fake_claude):
    result = run_daily(home, host="claude", now=NOW, run_date=RUN_DATE, client=client)
    assert result.status == "success", result.message
    assert result.summary["host"]["output"]["result"] == "ranked 9 jobs"

    store = Store(home.db)
    rankings = store.get_rankings(RUN_DATE)
    assert len(rankings) == 9
    assert rankings[0]["score"] >= rankings[-1]["score"]

    report = result.report_path.read_text()
    assert "Best matches (ranked by your rubric)" in report
    assert "Backend + Go match" in report

    folders = list(home.applications.iterdir())
    assert len(folders) == 1
    status = json.loads((folders[0] / "status.json").read_text())
    assert status["state"] == "ready" and status["submitted_by_user"] is None
    cv = (folders[0] / "cv.md").read_text()
    assert cv.startswith("# Priya Example")  # PII filled locally, after the model ran


def test_failing_host_keeps_no_llm_report(home, client, tmp_path, monkeypatch):
    exe = write_exe(tmp_path, "bad-claude", f"#!{sys.executable}\nimport sys\nsys.exit(3)\n")
    monkeypatch.setenv("ROJGAAR_CLAUDE_BIN", str(exe))
    result = run_daily(home, host="claude", now=NOW, run_date=RUN_DATE, client=client)
    assert result.status == "partial"
    assert "exited with 3" in result.message
    assert "cheap scoring only" in result.report_path.read_text()


def test_missing_host_is_reported_not_crashed(home, client, monkeypatch):
    monkeypatch.setenv("ROJGAAR_CODEX_BIN", "/definitely/not/installed/codex")
    result = run_daily(home, host="codex", now=NOW, run_date=RUN_DATE, client=client)
    assert result.status == "partial"
    assert "not installed" in result.message


def test_host_timeout(home, client):
    def slow_runner(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    result = run_daily(
        home, host="muse", now=NOW, run_date=RUN_DATE, client=client, runner=slow_runner, timeout=5
    )
    assert result.status == "partial"
    assert "timed out after 5s" in result.message


def test_force_reruns_and_records_each_run(home, client):
    run_daily(home, host="none", now=NOW, run_date=RUN_DATE, client=client)
    forced = run_daily(home, host="none", now=NOW, run_date=RUN_DATE, client=client, force=True)
    assert forced.status == "success"
    assert forced.summary["new"] == 0
