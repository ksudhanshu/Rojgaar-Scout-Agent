import pytest

from rojgaar.registry import detect_ats, discover, dump_companies, load_companies, parse_companies


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://boards.greenhouse.io/stripe/jobs/123", ("greenhouse", "stripe")),
        ("https://job-boards.greenhouse.io/anthropic", ("greenhouse", "anthropic")),
        ("https://boards.greenhouse.io/embed/job_board?for=figma", ("greenhouse", "figma")),
        ("https://boards-api.greenhouse.io/v1/boards/acme/jobs", ("greenhouse", "acme")),
        ("https://jobs.lever.co/plaid/abc-123", ("lever", "plaid")),
        ("https://jobs.ashbyhq.com/openai/xyz", ("ashby", "openai")),
        ("https://apply.workable.com/acme-co/j/ABC/", ("workable", "acme-co")),
        (
            "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site",
            ("workday", "salesforce/External_Career_Site"),
        ),
    ],
)
def test_detect_ats(url, expected):
    assert detect_ats(url) == expected


def test_detect_unknown():
    assert detect_ats("https://careers.example.com/jobs") is None


def test_discover_in_careers_page():
    html = """
    <a href="https://boards.greenhouse.io/acme/jobs/1">Job</a>
    <a href='https://boards.greenhouse.io/acme/jobs/2'>Job 2</a>
    <script src="https://jobs.ashbyhq.com/acme/embed.js"></script>
    """
    assert discover(html) == [("greenhouse", "acme"), ("ashby", "acme")]


def test_parse_and_dump_round_trip():
    text = "companies:\n  - {name: X, ats: lever, slug: x, verified: true}\n"
    companies = parse_companies(text)
    assert companies[0].verified is True
    assert parse_companies(dump_companies(companies)) == companies


def test_load_falls_back_to_bundled_seed(tmp_path):
    seed = load_companies(tmp_path / "missing.yaml")
    assert len(seed) >= 5
    assert all(not c.verified for c in seed)
