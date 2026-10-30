import pytest

from rojgaar.preferences import (
    Preferences,
    PreferencesError,
    example_preferences_text,
    load_preferences,
    parse_preferences,
)


def test_example_preferences_parse_with_us_defaults():
    prefs = parse_preferences(example_preferences_text())
    assert list(prefs.markets) == ["us"]
    us = prefs.markets["us"]
    assert us.locations == ["San Francisco, CA", "Bay Area, CA", "remote-US"]
    assert us.salary_floor.amount == 150000
    assert "greenhouse" in prefs.enabled_sources()


def test_defaults_without_file_content():
    prefs = parse_preferences("")
    assert prefs.markets["us"].locations[0] == "San Francisco, CA"
    assert prefs.report.top_n == 15
    assert prefs.ranking.weights["must_have"] == 3


def test_disabled_market_is_not_active():
    prefs = Preferences.model_validate({"markets": {"us": {"enabled": False}}})
    assert prefs.active_markets() == {}
    assert prefs.enabled_sources() == []


def test_invalid_yaml_raises_clear_error():
    with pytest.raises(PreferencesError, match="invalid"):
        parse_preferences("markets: [this is: not valid")
    with pytest.raises(PreferencesError):
        parse_preferences("filters: {max_age_days: not-a-number}")


def test_missing_file_points_to_init(tmp_path):
    with pytest.raises(PreferencesError, match="rojgaar init"):
        load_preferences(tmp_path / "nope.yaml")
