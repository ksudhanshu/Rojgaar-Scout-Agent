"""The MCP surface: registered tools, behaviour through the SDK, and no PII leaks."""

import asyncio
import json
import os
import sys

import pytest
from helpers import NOW, RUN_DATE

from rojgaar.mcp_server import build_server
from rojgaar.mcp_tools import TOOL_NAMES, RojgaarTools
from rojgaar.pipeline import build_shortlist, fetch_all
from rojgaar.preferences import load_preferences
from rojgaar.registry import load_companies
from rojgaar.store import Store

pytestmark = pytest.mark.integration
PII_VALUES = ["Priya Example", "priya@example.com", "+1 555 0199"]


@pytest.fixture
def seeded(home, client):
    prefs = load_preferences(home.preferences)
    store = Store(home.db)
    fetch_all(prefs, store, client, load_companies(home.companies), NOW)
    build_shortlist(prefs, store, RUN_DATE, NOW)
    store.close()
    return home


def text_of(result) -> str:
    return "".join(getattr(c, "text", "") for c in result.content)


def test_server_registers_exactly_the_narrow_tools(seeded):
    server = build_server(seeded)
    names = sorted(t.name for t in asyncio.run(server.list_tools()))
    assert names == sorted(TOOL_NAMES)
    forbidden = ("submit", "apply", "email", "fetch_url", "shell", "browse")
    assert not [n for n in names if any(f in n for f in forbidden)]


def test_call_tools_through_the_sdk(seeded):
    server = build_server(seeded)
    shortlist = json.loads(text_of(asyncio.run(server.call_tool("get_shortlist", {}))))
    assert shortlist["run_date"] == RUN_DATE and shortlist["count"] == 9
    uid = shortlist["jobs"][0]["uid"]
    job = json.loads(text_of(asyncio.run(server.call_tool("get_job", {"uid": uid}))))
    assert job["uid"] == uid and "apply_url" in job


def test_save_rankings_validates_and_scores_in_code(seeded):
    tools = RojgaarTools(seeded)
    uid = tools.get_shortlist()["jobs"][0]["uid"]
    good = {
        "uid": uid,
        "scores": dict.fromkeys(("title", "must_have", "seniority", "logistics", "preference"), 3),
        "verdict": "strong",
    }
    bad = {"uid": uid, "scores": {"title": 9}, "verdict": "strong"}
    out = tools.save_rankings([good, bad])
    assert out["saved"] == 1 and out["ranked"][0]["score"] == 1.0
    assert len(out["errors"]) == 1


def test_blocked_draft_is_saved_but_not_ready(seeded):
    tools = RojgaarTools(seeded)
    uid = tools.get_shortlist()["jobs"][0]["uid"]
    fabricated = {
        "sections": [
            {
                "title": "Experience",
                "bullets": [{"text": "Led a 12-person Rust team", "src": ["exp.acme.b1"]}],
            }
        ]
    }
    out = tools.save_application_draft(uid, fabricated)
    assert out["ready"] is False
    got = {f["code"] for f in out["findings"]}
    assert {"NUMBER_MISMATCH", "UNKNOWN_SKILL", "QUALIFIER_DROPPED"} <= got
    folder = seeded.root / out["folder"]
    assert json.loads((folder / "status.json").read_text())["state"] == "blocked"


def test_tool_errors_are_returned_not_raised(seeded):
    tools = RojgaarTools(seeded)
    assert "error" in tools.get_job("nope")
    assert "error" in tools.save_application_draft("nope", {})
    assert "error" in tools.record_feedback("x", "meh")
    assert tools.check_draft({"sections": "not a list"})["ready"] is False


def test_no_pii_in_any_read_tool_output(seeded):
    tools = RojgaarTools(seeded)
    outputs = [tools.get_shortlist(), tools.get_profile(), tools.get_bank()]
    outputs += [tools.get_job(j["uid"]) for j in tools.get_shortlist()["jobs"]]
    blob = json.dumps(outputs)
    for value in PII_VALUES:
        assert value not in blob


def test_stdio_server_lists_tools(seeded):
    """Start `python -m rojgaar mcp` as a real subprocess and talk MCP over stdio."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "rojgaar", "mcp"],
        env={**os.environ, "ROJGAAR_HOME": str(seeded.root)},
    )

    async def go():
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("get_shortlist", {})
            return [t.name for t in tools.tools], text_of(result)

    names, text = asyncio.run(asyncio.wait_for(go(), timeout=60))
    assert sorted(names) == sorted(TOOL_NAMES)
    assert json.loads(text)["count"] == 9
