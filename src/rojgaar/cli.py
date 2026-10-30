"""Command-line interface: ``rojgaar <command>``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from . import __version__
from .bank import BankError, load_bank
from .config import data_text, get_paths
from .daily import LockedError, run_daily, write_daily_report
from .doctor import run_checks
from .hostsetup import configure_codex, configure_muse, install_workspace
from .http import FetchError, PoliteClient
from .pipeline import build_shortlist, fetch_all
from .preferences import PreferencesError, example_preferences_text, load_preferences
from .registry import detect_ats, discover, load_companies
from .rubric import judge_schema
from .schedule import install as schedule_install
from .sources.base import REGISTRY, Source
from .store import Store
from .truth import Draft, check_draft, is_ready
from .utils import utcnow


def _paths(args: argparse.Namespace):  # type: ignore[no-untyped-def]
    return get_paths(args.home)


def cmd_init(args: argparse.Namespace) -> int:
    paths = _paths(args).ensure()
    files = {
        paths.preferences: example_preferences_text(),
        paths.bank: data_text("bank.example.yaml"),
        paths.pii: data_text("pii.example.yaml"),
        paths.companies: data_text("companies.us.yaml"),
    }
    for path, text in files.items():
        if path.exists() and not args.force:
            print(f"kept     {path}")
            continue
        path.write_text(text, encoding="utf-8")
        print(f"created  {path}")
    install_workspace(paths)
    print(f"\nYour data folder is {paths.root}")
    print(
        "Next: edit profile/bank.yaml (your real claims) and profile/preferences.yaml, then `rojgaar fetch`."
    )
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    paths = _paths(args).ensure()
    prefs = load_preferences(paths.preferences)
    store = Store(paths.db)
    with PoliteClient() as client:
        summary = fetch_all(prefs, store, client, load_companies(paths.companies), utcnow(), only=args.source)
    for name, s in summary.per_source.items():
        line = f"{name:16} fetched={s.fetched:<4} new={s.new:<4} dup={s.duplicates:<4} seen={s.seen:<4}"
        if s.skipped:
            line += f" skipped: {s.skipped}"
        if s.errors:
            line += f" errors={len(s.errors)} ({s.errors[0]})"
        print(line)
    print("total:", summary.totals())
    return 0


def cmd_shortlist(args: argparse.Namespace) -> int:
    paths = _paths(args).ensure()
    prefs = load_preferences(paths.preferences)
    store = Store(paths.db)
    now = utcnow()
    try:
        skills = sorted(load_bank(paths.bank).all_skills())
    except BankError:
        skills = []
    run_date = args.date or now.astimezone().date().isoformat()
    result = build_shortlist(prefs, store, run_date, now, skills, None, args.n)
    print(f"{result.passed} jobs passed the filters; shortlist of {len(result.entries)} saved for {run_date}")
    for reason, uids in sorted(result.dropped.items(), key=lambda x: -len(x[1])):
        print(f"  dropped {len(uids):4} · {reason}")
    for i, e in enumerate(result.entries[:20], 1):
        job = store.get_job(e["uid"])
        if job:
            print(f"{i:3}. {job.title} — {job.company} · {job.location_text()}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    paths = _paths(args).ensure()
    prefs = load_preferences(paths.preferences)
    store = Store(paths.db)
    run_date = args.date or store.latest_shortlist_date()
    if not run_date:
        print("No shortlist yet. Run `rojgaar shortlist` first.")
        return 1
    print(write_daily_report(store, paths, prefs, run_date))
    return 0


def cmd_run_daily(args: argparse.Namespace) -> int:
    try:
        result = run_daily(_paths(args), host=args.host, timeout=args.timeout, force=args.force)
    except LockedError as exc:
        print(f"skipped: {exc}")
        return 0
    print(f"{result.status}: {result.message}")
    if result.report_path:
        print(f"report: {result.report_path}")
    return 0 if result.status in ("success", "partial", "skipped") else 1


def cmd_check_draft(args: argparse.Namespace) -> int:
    paths = _paths(args)
    text = Path(args.file).read_text(encoding="utf-8")
    data = json.loads(text) if args.file.endswith(".json") else yaml.safe_load(text)
    findings = check_draft(Draft.model_validate(data), load_bank(args.bank or paths.bank))
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        for f in findings:
            print(f"{f.severity.upper():7} {f.code:18} {f.location:32} {f.message}")
        print("READY" if is_ready(findings) else "BLOCKED")
    return 0 if is_ready(findings) else 1


def cmd_companies(args: argparse.Namespace) -> int:
    paths = _paths(args)
    if args.action == "detect":
        hit = detect_ats(args.url)
        print(f"{hit[0]} {hit[1]}" if hit else "no known ATS in that URL")
        return 0 if hit else 1
    if args.action == "discover":
        with PoliteClient() as client:
            html = client.get_text(args.url)
        found = discover(html)
        for ats, slug in found:
            print(f"{ats:12} {slug}")
        return 0 if found else 1
    companies = load_companies(paths.companies)
    if args.action == "list":
        for c in companies:
            print(f"{c.name:20} {c.ats:11} {c.slug:20} {'verified' if c.verified else 'unverified'}")
        return 0
    # check: call each board once and report the job count
    failures = 0
    with PoliteClient() as client:
        for c in companies:
            cls = REGISTRY.get(c.ats)
            if not cls or not issubclass(cls, Source):
                print(f"{c.name:20} {c.ats:11} adapter not implemented")
                continue
            try:
                n = len(cls().fetch_company(client, c))
                print(f"{c.name:20} {c.ats:11} OK  {n} jobs")
            except FetchError as exc:
                failures += 1
                print(f"{c.name:20} {c.ats:11} FAIL {exc}")
    return 1 if failures else 0


def cmd_schedule(args: argparse.Namespace) -> int:
    paths = _paths(args).ensure()
    hour, minute = (int(x) for x in args.time.split(":"))
    plan = schedule_install(
        args.host, hour, minute, paths.root, paths.logs, apply=args.action == "install", system=args.platform
    )
    for path, content in plan.files.items():
        print(f"# {path}\n{content}")
    for cmd in plan.commands:
        print(("ran: " if args.action == "install" else "would run: ") + " ".join(cmd))
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    paths = _paths(args)
    for p in install_workspace(paths):
        print(f"workspace  {p}")
    if args.host == "codex":
        print(f"codex      {configure_codex(paths)}")
    elif args.host == "muse":
        print(f"muse       {configure_muse(paths)}")
    else:
        print(
            "claude     uses the workspace .mcp.json (or install the plugin: /plugin marketplace add <repo>)"
        )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = run_checks(_paths(args))
    for c in checks:
        mark = "ok " if c.ok else "FIX"
        print(f"[{mark}] {c.name:18} {c.detail}" + (f"  → {c.fix}" if not c.ok and c.fix else ""))
    return 0 if all(c.ok for c in checks) else 1


def cmd_feedback(args: argparse.Namespace) -> int:
    paths = _paths(args).ensure()
    Store(paths.db).add_feedback(args.uid, args.rating, args.reason, utcnow())
    print("saved")
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    schema = judge_schema() if args.name == "judge" else Draft.model_json_schema()
    print(json.dumps(schema, indent=2))
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    from .mcp_server import build_server

    build_server(_paths(args)).run("stdio")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rojgaar", description="Local-first job scout for AI coding CLIs. Never submits."
    )
    p.add_argument("--version", action="version", version=f"rojgaar-scout {__version__}")
    p.add_argument("--home", help="data folder (default: $ROJGAAR_HOME or ~/RojgaarScout)")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="create your data folder and starter files")
    s.add_argument("--force", action="store_true", help="overwrite existing files")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("fetch", help="fetch new postings from enabled sources")
    s.add_argument("--source", action="append", help="limit to a source (repeatable)")
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("shortlist", help="apply hard filters and cheap scoring")
    s.add_argument("--n", type=int, default=None)
    s.add_argument("--date")
    s.set_defaults(func=cmd_shortlist)

    s = sub.add_parser("report", help="write the daily markdown report")
    s.add_argument("--date")
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("run-daily", help="fetch, shortlist, report, then let a host CLI rank and draft")
    s.add_argument("--host", choices=["claude", "codex", "muse", "none"], default="none")
    s.add_argument("--timeout", type=float, default=1800)
    s.add_argument("--force", action="store_true", help="run even if today already succeeded")
    s.set_defaults(func=cmd_run_daily)

    s = sub.add_parser("check-draft", help="run truth checks on a draft (JSON or YAML)")
    s.add_argument("file")
    s.add_argument("--bank")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_check_draft)

    s = sub.add_parser("companies", help="manage the company registry")
    s.add_argument("action", choices=["list", "check", "detect", "discover"])
    s.add_argument("url", nargs="?")
    s.set_defaults(func=cmd_companies)

    s = sub.add_parser("schedule", help="print or install the daily OS schedule")
    s.add_argument("action", choices=["print", "install"])
    s.add_argument("--host", choices=["claude", "codex", "muse", "none"], default="claude")
    s.add_argument("--time", default="07:13", help="HH:MM local time")
    s.add_argument("--platform", choices=["Darwin", "Linux", "Windows"], default=None)
    s.set_defaults(func=cmd_schedule)

    s = sub.add_parser("setup", help="wire the MCP server and skills into a host CLI")
    s.add_argument("host", choices=["claude", "codex", "muse"])
    s.set_defaults(func=cmd_setup)

    s = sub.add_parser("doctor", help="check your setup")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("feedback", help="thumbs up/down on a job")
    s.add_argument("uid")
    s.add_argument("rating", choices=["up", "down"])
    s.add_argument("--reason")
    s.set_defaults(func=cmd_feedback)

    s = sub.add_parser("schema", help="print a JSON schema (judge | draft)")
    s.add_argument("name", choices=["judge", "draft"])
    s.set_defaults(func=cmd_schema)

    s = sub.add_parser("mcp", help="start the stdio MCP server")
    s.set_defaults(func=cmd_mcp)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s"
    )
    if args.command == "companies" and args.action in ("detect", "discover") and not args.url:
        print("a URL is required", file=sys.stderr)
        return 2
    try:
        return int(args.func(args))
    except (PreferencesError, BankError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
