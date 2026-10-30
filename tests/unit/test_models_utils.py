from datetime import UTC, datetime

import pytest

from rojgaar.models import Salary, parse_salary_text
from rojgaar.utils import iso, norm, parse_dt, slugify


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The base salary range is $180,000 - $220,000 per year.", (180000, 220000, "year")),
        ("$150k - $185k", (150000, 185000, "year")),
        ("Comp: $170K – $210K", (170000, 210000, "year")),
        ("$190k-$230k", (190000, 230000, "year")),
        ("Pay: $55 - $70 per hour", (55, 70, "hour")),
        ("Up to $200,000", (200000, 200000, "year")),
    ],
)
def test_parse_salary_text(text, expected):
    s = parse_salary_text(text)
    assert s is not None
    assert (s.min, s.max, s.period) == expected


@pytest.mark.parametrize("text", [None, "", "Competitive salary", "We have 150 employees", "$150 gift card"])
def test_parse_salary_text_never_estimates(text):
    assert parse_salary_text(text) is None


def test_salary_yearly_max_converts_periods():
    assert Salary(min=50, max=60, period="hour").yearly_max() == 60 * 2080
    assert Salary(max=10000, period="month").yearly_max() == 120000
    assert Salary(min=100000, period="year").yearly_max() == 100000
    assert Salary().yearly_max() is None


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-10-27T09:00:00Z", datetime(2026, 10, 27, 9, tzinfo=UTC)),
        ("2026-10-27", datetime(2026, 10, 27, tzinfo=UTC)),
        (1793145600000, datetime.fromtimestamp(1793145600, tz=UTC)),
        (1793145600, datetime.fromtimestamp(1793145600, tz=UTC)),
        ("1793145600", datetime.fromtimestamp(1793145600, tz=UTC)),
    ],
)
def test_parse_dt(value, expected):
    assert parse_dt(value) == expected


def test_parse_dt_bad_values():
    assert parse_dt(None) is None
    assert parse_dt("") is None
    assert parse_dt("Posted 3 Days Ago") is None


def test_iso_is_utc():
    assert iso(datetime(2026, 1, 1, 12, 0)) == "2026-01-01T12:00:00+00:00"


def test_norm_and_slugify():
    assert norm("  Café — São Paulo!! ") == "cafe sao paulo"
    assert slugify("Senior Backend Engineer, Payments (SF)") == "senior-backend-engineer-payments-sf"
    assert slugify("???") == "item"
