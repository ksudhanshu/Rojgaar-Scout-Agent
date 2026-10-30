"""``rojgaar doctor``: answer setup questions before you have to ask them."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass

from .bank import BankError, load_bank
from .config import Paths
from .preferences import PreferencesError, load_preferences
from .store import Store


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""


def run_checks(paths: Paths) -> list[Check]:
    checks: list[Check] = []
    v = sys.version_info
    checks.append(Check("python", v >= (3, 11), f"{v.major}.{v.minor}", "install Python 3.11+"))
    checks.append(Check("data folder", paths.root.exists(), str(paths.root), "run `rojgaar init`"))
    try:
        prefs = load_preferences(paths.preferences)
        market = next(iter(prefs.active_markets().values()))
        checks.append(Check("preferences.yaml", True, f"locations: {', '.join(market.locations)}"))
    except PreferencesError as exc:
        checks.append(Check("preferences.yaml", False, str(exc), "run `rojgaar init` or fix the YAML"))
    try:
        bank = load_bank(paths.bank)
        verified = sum(1 for r in bank.roles for c in r.claims if c.verified_by_user)
        checks.append(
            Check(
                "bank.yaml",
                verified > 0,
                f"{verified} verified claims",
                "mark checked claims verified_by_user: true",
            )
        )
    except BankError as exc:
        checks.append(Check("bank.yaml", False, str(exc), "copy your claims into profile/bank.yaml"))
    checks.append(Check("pii.yaml", paths.pii.exists(), str(paths.pii), "run `rojgaar init`"))
    try:
        store = Store(paths.db)
        last = store.last_run()
        store.close()
        detail = f"last run {last['run_date']} → {last['status']}" if last else "no runs yet"
        checks.append(Check("database", True, detail))
    except Exception as exc:  # pragma: no cover - defensive
        checks.append(Check("database", False, str(exc), "check folder permissions"))
    checks.append(
        Check(
            "mcp package",
            importlib.util.find_spec("mcp") is not None,
            "needed for `rojgaar mcp`",
            "pip install 'rojgaar-scout[mcp]'",
        )
    )
    for host in ("claude", "codex", "muse"):
        path = shutil.which(host)
        checks.append(Check(f"host: {host}", True, path or "not installed (optional)"))
    return checks
