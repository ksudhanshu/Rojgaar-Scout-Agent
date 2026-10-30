"""Install a daily OS schedule for ``rojgaar run-daily``.

The CLIs' built-in schedulers don't fit a local daily job (cloud tasks have no
local files, desktop tasks need the app open, /loop expires). OS schedulers can
catch up after the laptop sleeps:
  macOS launchd (coalesces missed runs) · systemd timer Persistent=true ·
  Windows Task Scheduler StartWhenAvailable.
"""

from __future__ import annotations

import platform
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

LABEL = "com.rojgaar-scout.daily"


def run_daily_command(host: str) -> list[str]:
    return [sys.executable, "-m", "rojgaar", "run-daily", "--host", host]


def launchd_plist(cmd: list[str], hour: int, minute: int, home: Path, log_dir: Path) -> str:
    args = "\n".join(f"    <string>{escape(a)}</string>" for a in cmd)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array>
{args}
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>ROJGAAR_HOME</key>
    <string>{escape(str(home))}</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>{hour}</integer>
    <key>Minute</key>
    <integer>{minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{escape(str(log_dir / "launchd.out.log"))}</string>
  <key>StandardErrorPath</key>
  <string>{escape(str(log_dir / "launchd.err.log"))}</string>
</dict>
</plist>
"""


def systemd_units(cmd: list[str], hour: int, minute: int, home: Path) -> tuple[str, str]:
    service = f"""[Unit]
Description=Rojgaar-Scout daily job scan

[Service]
Type=oneshot
Environment=ROJGAAR_HOME={home}
ExecStart={shlex.join(cmd)}
TimeoutStartSec=3600
"""
    timer = f"""[Unit]
Description=Run Rojgaar-Scout daily

[Timer]
OnCalendar=*-*-* {hour:02d}:{minute:02d}:00
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
"""
    return service, timer


def windows_task_xml(cmd: list[str], hour: int, minute: int) -> str:
    exe, *args = cmd
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T{hour:02d}:{minute:02d}:00</StartBoundary>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <StartWhenAvailable>true</StartWhenAvailable>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
  </Settings>
  <Actions>
    <Exec>
      <Command>{escape(exe)}</Command>
      <Arguments>{escape(" ".join(args))}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


@dataclass
class InstallPlan:
    files: dict[Path, str]
    commands: list[list[str]]


def plan_install(system: str, host: str, hour: int, minute: int, home: Path, log_dir: Path) -> InstallPlan:
    cmd = run_daily_command(host)
    if system == "Darwin":
        path = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        return InstallPlan(
            {path: launchd_plist(cmd, hour, minute, home, log_dir)},
            [["launchctl", "unload", str(path)], ["launchctl", "load", "-w", str(path)]],
        )
    if system == "Linux":
        base = Path.home() / ".config" / "systemd" / "user"
        service, timer = systemd_units(cmd, hour, minute, home)
        return InstallPlan(
            {base / "rojgaar-scout.service": service, base / "rojgaar-scout.timer": timer},
            [
                ["systemctl", "--user", "daemon-reload"],
                ["systemctl", "--user", "enable", "--now", "rojgaar-scout.timer"],
            ],
        )
    if system == "Windows":
        path = home / "config" / "rojgaar-scout-task.xml"
        return InstallPlan(
            {path: windows_task_xml(cmd, hour, minute)},
            [["schtasks", "/Create", "/TN", "RojgaarScoutDaily", "/XML", str(path), "/F"]],
        )
    raise ValueError(f"unsupported platform {system!r}")


def install(
    host: str, hour: int, minute: int, home: Path, log_dir: Path, apply: bool, system: str | None = None
) -> InstallPlan:
    plan = plan_install(system or platform.system(), host, hour, minute, home, log_dir)
    if apply:
        for path, content in plan.files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        for cmd in plan.commands:
            subprocess.run(cmd, check=False)
    return plan
