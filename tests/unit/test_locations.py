import pytest

from rojgaar.locations import expand_wanted, matches, remote_scope

DEFAULT = ["San Francisco, CA", "Bay Area, CA", "remote-US"]


@pytest.mark.parametrize(
    "locs,remote",
    [
        (["San Francisco, CA"], "onsite"),
        (["Mountain View, CA"], "onsite"),
        (["Oakland, CA"], "hybrid"),
        (["Sunnyvale, California"], "unknown"),
        (["SF Bay Area"], "unknown"),
        (["Remote - US"], "remote"),
        (["Remote (USA)"], "remote"),
        (["United States (Remote)"], "remote"),
        (["Remote"], "remote"),  # remote anywhere, included by default
    ],
)
def test_default_locations_match(locs, remote):
    assert matches(locs, remote, DEFAULT) is True


@pytest.mark.parametrize(
    "locs,remote",
    [
        (["New York, NY"], "onsite"),
        (["Austin, TX"], "hybrid"),
        (["London, UK"], "onsite"),
        (["Remote (Europe)"], "remote"),
        (["Remote - Canada"], "remote"),
    ],
)
def test_other_locations_do_not_match(locs, remote):
    assert matches(locs, remote, DEFAULT) is False


def test_unknown_location_returns_none_so_caller_fails_open():
    assert matches([], "unknown", DEFAULT) is None


def test_remote_global_can_be_excluded():
    assert matches(["Remote"], "remote", DEFAULT, include_remote_global=False) is False
    assert matches(["Remote - US"], "remote", DEFAULT, include_remote_global=False) is True


def test_remote_flag_with_us_city_counts_as_us_remote():
    assert matches(["Seattle, WA"], "remote", ["remote-US"]) is True


def test_bay_area_expands_to_cities():
    cities = expand_wanted("Bay Area, CA")
    for city in ("San Jose", "Palo Alto", "Oakland", "San Ramon"):
        assert city in cities
    assert expand_wanted("Austin, TX") == ["Austin"]


def test_word_boundaries_avoid_false_matches():
    # "SF" must not match inside words; "Dublin" (CA) is in the Bay Area list but needs a whole word.
    assert matches(["SFTP Services, TX"], "onsite", DEFAULT) is False


def test_remote_scope():
    assert remote_scope(["Remote - US"]) == "us"
    assert remote_scope(["Remote"]) == "global"
    assert remote_scope(["Remote, EMEA"]) == "non-us"
    assert remote_scope(["San Francisco, CA"]) is None
