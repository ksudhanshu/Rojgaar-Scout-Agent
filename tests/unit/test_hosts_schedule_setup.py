import json
import os
from pathlib import Path

import pytest

from rojgaar.config import Paths
from rojgaar.hosts import FORBIDDEN, HostOptions, assert_safe, build_command, parse_output
from rojgaar.hostsetup import configure_codex, configure_muse, install_workspace
from rojgaar.schedule import launchd_plist, plan_install, systemd_units, windows_task_xml


@pytest.mark.parametrize("host", ["claude", "codex", "muse"])
def test_host_commands_are_safe(host):
    cmd = build_command(host)
    flags = [p for p in cmd if not p.startswith("Use the rojgaar")]
    for bad in FORBIDDEN:
        assert all(bad not in p for p in flags)
    assert "rojgaar-daily" in " ".join(cmd)


def test_claude_command_flags():
    cmd = build_command("claude", HostOptions(budget_usd=1.5, claude_tools="mcp__rojgaar__*"))
    assert cmd[:2] == ["claude", "-p"]
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
    assert cmd[cmd.index("--allowedTools") + 1] == "mcp__rojgaar__*"
    assert cmd[cmd.index("--max-budget-usd") + 1] == "1.5"
    assert cmd[cmd.index("--output-format") + 1] == "json"


def test_codex_and_muse_flags():
    assert build_command("codex")[:5] == ["codex", "exec", "--json", "--sandbox", "workspace-write"]
    muse = build_command("muse", HostOptions(max_steps=50))
    assert muse[:4] == ["muse", "exec", "--json", "--disable-approval"]
    assert muse[muse.index("--max-model-steps") + 1] == "50"


def test_executable_override(monkeypatch):
    monkeypatch.setenv("ROJGAAR_CODEX_BIN", "/opt/codex")
    assert build_command("codex")[0] == "/opt/codex"


def test_unknown_host_and_forbidden_flags():
    with pytest.raises(ValueError):
        build_command("cursor")
    with pytest.raises(ValueError, match="refusing"):
        assert_safe(["claude", "-p", "x", "--dangerously-skip-permissions"])


def test_parse_output_variants():
    assert parse_output('{"result": "ok"}') == {"result": "ok"}
    assert parse_output('{"type":"a"}\n{"type":"done","n":2}\n') == {"type": "done", "n": 2}
    assert parse_output("plain text")["raw"] == "plain text"
    assert parse_output("") == {}
    assert parse_output("[1, 2]") == {"result": [1, 2]}


def test_launchd_plist():
    xml = launchd_plist(
        ["/usr/bin/python3", "-m", "rojgaar", "run-daily"],
        7,
        13,
        Path("/Users/me/RojgaarScout"),
        Path("/tmp/logs"),
    )
    assert "<key>StartCalendarInterval</key>" in xml
    assert "<integer>7</integer>" in xml and "<integer>13</integer>" in xml
    assert "<string>run-daily</string>" in xml
    assert "ROJGAAR_HOME" in xml


def test_systemd_timer_is_persistent():
    service, timer = systemd_units(
        ["python", "-m", "rojgaar", "run-daily"], 7, 13, Path("/home/me/RojgaarScout")
    )
    assert "Persistent=true" in timer
    assert "OnCalendar=*-*-* 07:13:00" in timer
    assert "ExecStart=python -m rojgaar run-daily" in service
    assert "Type=oneshot" in service


def test_windows_task_starts_when_available():
    xml = windows_task_xml(["C:/py/python.exe", "-m", "rojgaar", "run-daily"], 7, 13)
    assert "<StartWhenAvailable>true</StartWhenAvailable>" in xml
    assert "T07:13:00" in xml


@pytest.mark.parametrize("system,suffix", [("Darwin", ".plist"), ("Linux", ".timer"), ("Windows", ".xml")])
def test_plan_install_per_platform(system, suffix, tmp_path):
    plan = plan_install(system, "claude", 7, 13, tmp_path, tmp_path / "logs")
    assert any(str(p).endswith(suffix) for p in plan.files)
    assert plan.commands


def test_plan_install_unsupported():
    with pytest.raises(ValueError):
        plan_install("Plan9", "claude", 7, 13, Path("/x"), Path("/x"))


def test_install_workspace(tmp_path):
    paths = Paths(tmp_path / "home")
    install_workspace(paths)
    assert (paths.root / "AGENTS.md").read_text().startswith("# Rojgaar-Scout workspace")
    assert (paths.root / "CLAUDE.md").read_text().strip() == "@AGENTS.md"
    for d in (".agents/skills", ".claude/skills"):
        assert (paths.root / d / "rojgaar-daily" / "SKILL.md").exists()
    mcp = json.loads((paths.root / ".mcp.json").read_text())
    assert mcp["mcpServers"]["rojgaar"]["args"] == ["-m", "rojgaar", "mcp"]
    assert mcp["mcpServers"]["rojgaar"]["env"]["ROJGAAR_HOME"] == str(paths.root)
    install_workspace(paths)  # idempotent


def test_configure_codex_is_idempotent_and_keeps_other_config(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('model = "gpt-5"\n\n[mcp_servers.other]\ncommand = "x"\n')
    paths = Paths(tmp_path / "home")
    configure_codex(paths, cfg)
    configure_codex(paths, cfg)
    text = cfg.read_text()
    assert text.count("[mcp_servers.rojgaar]") == 1
    assert text.count("[mcp_servers.rojgaar.env]") == 1
    assert 'model = "gpt-5"' in text and "[mcp_servers.other]" in text
    assert (tmp_path / "config.toml.bak").exists()
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        return
    data = tomllib.loads(text)
    assert data["mcp_servers"]["rojgaar"]["args"] == ["-m", "rojgaar", "mcp"]
    assert data["mcp_servers"]["rojgaar"]["env"]["ROJGAAR_HOME"] == str(paths.root)


def test_configure_muse_uses_official_key(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    configure_muse(Paths(tmp_path / "home"), settings)
    data = json.loads(settings.read_text())
    assert data["schema_version"] == 1
    assert "rojgaar" in data["mcp_servers"]
    assert "mcpServers" not in data
    assert data["theme"] == "dark"
    assert os.path.exists(str(settings) + ".bak")
