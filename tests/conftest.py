"""Shared test fixtures. All HTTP is mocked; nothing touches the network."""

from __future__ import annotations

from datetime import datetime

import httpx
import pytest
from helpers import NOW, TEST_COMPANIES, load_fixture, make_handler

from rojgaar.config import Paths, data_text
from rojgaar.http import PoliteClient


@pytest.fixture
def fixtures():
    return load_fixture


@pytest.fixture
def request_log() -> list:
    return []


@pytest.fixture
def client(request_log) -> PoliteClient:
    c = PoliteClient(
        min_delay=0,
        jitter=0,
        transport=httpx.MockTransport(make_handler(log=request_log)),
        sleep=lambda s: None,
    )
    yield c
    c.close()


@pytest.fixture
def home(tmp_path, monkeypatch) -> Paths:
    """A fresh ROJGAAR_HOME with example preferences, bank, pii and a test company registry."""
    paths = Paths(tmp_path / "RojgaarScout").ensure()
    paths.preferences.write_text(data_text("preferences.example.yaml"), encoding="utf-8")
    paths.bank.write_text(data_text("bank.example.yaml"), encoding="utf-8")
    paths.pii.write_text(
        'NAME: "Priya Example"\nEMAIL: "priya@example.com"\nPHONE: "+1 555 0199"\nLOCATION: "San Francisco, CA"\n',
        encoding="utf-8",
    )
    paths.companies.write_text(TEST_COMPANIES, encoding="utf-8")
    monkeypatch.setenv("ROJGAAR_HOME", str(paths.root))
    monkeypatch.setenv("ROJGAAR_NO_EMBED", "1")
    return paths


@pytest.fixture
def now() -> datetime:
    return NOW
