"""Where Rojgaar-Scout keeps your data.

The tool lives in the repo; your data lives in ``~/RojgaarScout`` (override with
``ROJGAAR_HOME``). Nothing in this folder is ever committed or shipped.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

HOME_ENV = "ROJGAAR_HOME"


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def profile(self) -> Path:
        return self.root / "profile"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def logs(self) -> Path:
        return self.state / "logs"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def applications(self) -> Path:
        return self.root / "applications"

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def db(self) -> Path:
        return self.state / "rojgaar.db"

    @property
    def lock(self) -> Path:
        return self.state / "run.lock"

    @property
    def preferences(self) -> Path:
        return self.profile / "preferences.yaml"

    @property
    def bank(self) -> Path:
        return self.profile / "bank.yaml"

    @property
    def pii(self) -> Path:
        return self.profile / "pii.yaml"

    @property
    def companies(self) -> Path:
        return self.config / "companies.us.yaml"

    def ensure(self) -> Paths:
        for d in (self.profile, self.state, self.logs, self.reports, self.applications, self.config):
            d.mkdir(parents=True, exist_ok=True)
        return self


def get_paths(root: str | Path | None = None) -> Paths:
    if root is None:
        root = os.environ.get(HOME_ENV) or (Path.home() / "RojgaarScout")
    return Paths(Path(root).expanduser().resolve())


def data_text(name: str) -> str:
    """Read a file shipped inside the package (``src/rojgaar/data``)."""
    return resources.files("rojgaar").joinpath("data", name).read_text(encoding="utf-8")
