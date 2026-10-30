"""Headless invocation of the host CLIs (Claude Code, Codex, Muse).

The scheduled run never uses permission-bypass flags. Agents get only the
rojgaar MCP tools; all fetching already happened in Python.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

HOSTS = ("claude", "codex", "muse")
FORBIDDEN = (
    "--yolo",
    "--dangerously-skip-permissions",
    "danger-full-access",
    "bypassPermissions",
    "--full-auto",
)

DAILY_PROMPT = (
    "Use the rojgaar-daily skill. With only the rojgaar MCP tools: get today's shortlist and your profile, "
    "judge every job against the rubric and call save_rankings, then for the top {drafts} jobs draft a "
    "tailored CV and cover letter from bank claims only (every bullet cites src claim ids), check each with "
    "check_draft, save with save_application_draft, and finally call finalize_report. Never submit anything."
)


@dataclass(frozen=True)
class HostOptions:
    budget_usd: float = 2.0
    max_steps: int = 120
    claude_tools: str = "mcp__rojgaar__*"
    drafts: int = 5


def executable(host: str) -> str:
    """Executable name, overridable with ROJGAAR_<HOST>_BIN (used by tests and custom installs)."""
    return os.environ.get(f"ROJGAAR_{host.upper()}_BIN", host)


def build_command(host: str, opts: HostOptions | None = None) -> list[str]:
    opts = opts or HostOptions()
    prompt = DAILY_PROMPT.format(drafts=opts.drafts)
    if host == "claude":
        cmd = [
            executable("claude"), "-p", prompt,
            "--output-format", "json",
            "--permission-mode", "dontAsk",
            "--allowedTools", opts.claude_tools,
            "--max-budget-usd", f"{opts.budget_usd:g}",
        ]  # fmt: skip
    elif host == "codex":
        cmd = [executable("codex"), "exec", "--json", "--sandbox", "workspace-write", prompt]
    elif host == "muse":
        cmd = [
            executable("muse"),
            "exec",
            "--json",
            "--disable-approval",
            "--max-model-steps",
            str(opts.max_steps),
            prompt,
        ]
    else:
        raise ValueError(f"unknown host {host!r}; choose one of {HOSTS}")
    assert_safe(cmd)
    return cmd


def assert_safe(cmd: list[str]) -> None:
    for part in cmd:
        for bad in FORBIDDEN:
            if bad in part and not part.startswith("Use the rojgaar"):
                raise ValueError(f"refusing to run a host with {bad!r}")


def parse_output(stdout: str) -> dict:
    """Best-effort parse of JSON / JSONL output from any host; returns the last JSON object."""
    text = (stdout or "").strip()
    if not text:
        return {}
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {"result": obj}
    except ValueError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return {"raw": text[-2000:]}
