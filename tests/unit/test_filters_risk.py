import pytest
from helpers import NOW, make_job

from rojgaar.filters import apply_filters, infer_seniority
from rojgaar.models import Salary
from rojgaar.preferences import example_preferences_text, parse_preferences
from rojgaar.risk import assess


@pytest.fixture
def prefs():
    return parse_preferences(example_preferences_text())


def run(job, prefs):
    return apply_filters(job, prefs, prefs.markets["us"], NOW)


def test_good_job_passes(prefs):
    assert run(make_job(salary=Salary(min=180000, max=220000)), prefs).keep


def test_fail_open_on_unknowns(prefs):
    job = make_job(
        locations=[],
        remote="unknown",
        salary=None,
        title="Backend Engineer",
        date_posted=None,
        employment_type=None,
    )
    assert run(job, prefs).keep


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"locations": ["New York, NY"]}, "location"),
        ({"salary": Salary(min=90000, max=120000)}, "salary_below_floor"),
        ({"salary": Salary(min=40, max=50, period="hour")}, "salary_below_floor"),
        ({"title": "Junior Backend Engineer"}, "seniority"),
        ({"title": "Backend Engineering Intern"}, "excluded_title_word:intern"),
        ({"description": "This is an unpaid role"}, "excluded_keyword:unpaid"),
        ({"date_posted": "2026-09-01T00:00:00+00:00"}, "too_old"),
        ({"employment_type": "contract"}, "employment_type:contract"),
    ],
)
def test_drops_with_reasons(prefs, overrides, reason):
    result = run(make_job(**overrides), prefs)
    assert not result.keep
    assert result.reason == reason


def test_salary_floor_ignores_other_currencies(prefs):
    assert run(make_job(salary=Salary(min=50000, max=60000, currency="EUR")), prefs).keep


def test_sponsorship_only_drops_when_user_needs_it(prefs):
    job = make_job(description="We are unable to sponsor visas for this role.")
    assert run(job, prefs).keep
    prefs.markets["us"].drop_if_no_sponsorship = True
    assert run(job, prefs).reason == "no_sponsorship"


def test_excluded_company_and_required_keywords(prefs):
    prefs.filters.exclude_companies = ["Acme"]
    assert run(make_job(), prefs).reason == "excluded_company"
    prefs.filters.exclude_companies = []
    prefs.filters.require_keywords = ["Rust"]
    assert run(make_job(), prefs).reason == "missing_required_keyword"


def test_remote_mode_filter(prefs):
    prefs.filters.remote_modes = ["remote"]
    assert run(make_job(remote="onsite"), prefs).reason == "remote_mode:onsite"


def test_high_risk_hidden_only_when_asked(prefs):
    job = make_job(risk="high")
    assert run(job, prefs).keep
    prefs.filters.hide_high_risk = True
    assert run(job, prefs).reason == "high_risk"


@pytest.mark.parametrize(
    "title,level",
    [
        ("Senior Backend Engineer", "senior"),
        ("Sr. Software Engineer", "senior"),
        ("Staff Platform Engineer", "staff"),
        ("Principal Engineer", "principal"),
        ("Software Engineer I", "junior"),
        ("Software Engineer II", "mid"),
        ("Software Engineer III", "senior"),
        ("New Grad Software Engineer", "junior"),
        ("Director of Engineering", "director"),
        ("Head of Platform", "director"),
        ("Backend Engineer", None),
        ("Founding Engineer", None),
    ],
)
def test_infer_seniority(title, level):
    assert infer_seniority(title) == level


def test_risk_levels():
    assert assess(make_job(), NOW) == ("low", [])
    level, flags = assess(make_job(description="Message our recruiter on WhatsApp"), NOW)
    assert level == "high" and "messaging_app_contact" in flags
    level, flags = assess(make_job(description="Join our talent community"), NOW)
    assert level == "medium" and flags == ["talent_pool"]
    level, flags = assess(make_job(risk_flags=["hidden_text"]), NOW)
    assert level == "high"
    level, flags = assess(make_job(date_posted="2026-08-01T00:00:00+00:00"), NOW)
    assert "stale_over_45_days" in flags
    level, _ = assess(make_job(description="A $50 registration fee is required"), NOW)
    assert level == "high"
