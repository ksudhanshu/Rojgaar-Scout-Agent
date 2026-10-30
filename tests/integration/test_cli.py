"""The command-line interface, end to end, with mocked HTTP."""

import json

import httpx
import pytest
from helpers import make_handler

import rojgaar.cli as cli
import rojgaar.daily as daily
from rojgaar.http import PoliteClient

pytestmark = pytest.mark.integration


@pytest.fixture
def mocked_network(monkeypatch):
    def factory(*args, **kwargs):
        return PoliteClient(
            min_delay=0, jitter=0, transport=httpx.MockTransport(make_handler()), sleep=lambda s: None
        )

    monkeypatch.setattr(cli, "PoliteClient", factory)
    monkeypatch.setattr(daily, "PoliteClient", factory)


def run(*args) -> int:
    return cli.main(list(args))


def test_init_creates_data_folder_and_keeps_existing(tmp_path, capsys):
    home = tmp_path / "RS"
    assert run("--home", str(home), "init") == 0
    for rel in (
        "profile/preferences.yaml",
        "profile/bank.yaml",
        "profile/pii.yaml",
        "config/companies.us.yaml",
        "AGENTS.md",
        ".mcp.json",
        ".claude/skills/rojgaar-rank/SKILL.md",
    ):
        assert (home / rel).exists(), rel
    (home / "profile/preferences.yaml").write_text("schema_version: 1\n")
    assert run("--home", str(home), "init") == 0
    assert (home / "profile/preferences.yaml").read_text() == "schema_version: 1\n"
    assert "kept" in capsys.readouterr().out


def test_fetch_shortlist_report(home, mocked_network, capsys):
    assert run("--home", str(home.root), "fetch") == 0
    out = capsys.readouterr().out
    assert "greenhouse" in out and "new=4" in out
    assert run("--home", str(home.root), "shortlist", "--date", "2026-10-29") == 0
    out = capsys.readouterr().out
    assert "shortlist of" in out and "dropped" in out
    assert run("--home", str(home.root), "report", "--date", "2026-10-29") == 0
    assert (home.reports / "2026-10-29.md").exists()


def test_run_daily_cli(home, mocked_network, capsys):
    assert run("--home", str(home.root), "run-daily", "--host", "none") == 0
    assert "success" in capsys.readouterr().out
    assert run("--home", str(home.root), "run-daily", "--host", "none") == 0
    assert "skipped" in capsys.readouterr().out


def test_check_draft_exit_codes(home, tmp_path, capsys):
    good = tmp_path / "good.json"
    good.write_text(
        json.dumps(
            {
                "job_uid": "x",
                "sections": [
                    {
                        "title": "E",
                        "bullets": [
                            {"text": "Helped move 30 services onto Kubernetes", "src": ["exp.beta.b1"]}
                        ],
                    }
                ],
            }
        )
    )
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "job_uid: x\nsections:\n  - title: E\n    bullets:\n      - {text: Led 50 engineers, src: [exp.beta.b1]}\n"
    )
    assert run("--home", str(home.root), "check-draft", str(good)) == 0
    assert "READY" in capsys.readouterr().out
    assert run("--home", str(home.root), "check-draft", str(bad), "--json") == 1
    findings = json.loads(capsys.readouterr().out)
    assert {f["code"] for f in findings} >= {"NUMBER_MISMATCH"}


def test_schedule_print_does_not_install(home, capsys):
    assert run("--home", str(home.root), "schedule", "print", "--platform", "Linux", "--time", "06:47") == 0
    out = capsys.readouterr().out
    assert "Persistent=true" in out and "06:47:00" in out
    assert "would run: systemctl --user enable --now rojgaar-scout.timer" in out


def test_companies_detect_and_list(home, capsys):
    assert run("--home", str(home.root), "companies", "detect", "https://jobs.lever.co/plaid/123") == 0
    assert capsys.readouterr().out.strip() == "lever plaid"
    assert run("--home", str(home.root), "companies", "list") == 0
    assert "Acme Fintech" in capsys.readouterr().out
    assert run("--home", str(home.root), "companies", "detect") == 2


def test_companies_check(home, mocked_network, capsys):
    assert run("--home", str(home.root), "companies", "check") == 0
    out = capsys.readouterr().out
    assert "OK  4 jobs" in out and "OK  2 jobs" in out


def test_doctor_schema_feedback_setup(home, tmp_path, monkeypatch, capsys):
    assert run("--home", str(home.root), "doctor") == 0
    assert "[ok ] preferences.yaml" in capsys.readouterr().out
    assert run("--home", str(home.root), "schema", "judge") == 0
    assert "judgements" in json.loads(capsys.readouterr().out)["properties"]
    assert run("--home", str(home.root), "feedback", "x:y:1", "down", "--reason", "too-senior") == 0
    monkeypatch.setenv("HOME", str(tmp_path))
    assert run("--home", str(home.root), "setup", "muse") == 0
    assert (tmp_path / ".config/muse/settings.json").exists()


def test_errors_are_friendly(tmp_path, capsys):
    assert run("--home", str(tmp_path / "empty"), "shortlist") == 2
    assert "rojgaar init" in capsys.readouterr().err
