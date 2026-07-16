from backend.normalizer.sports_normalizer import normalize_league, normalize_period, normalize_player, normalize_team, parse_datetime


def test_team_aliases():
    assert normalize_team("NYY") == "New York Yankees"
    assert normalize_team("LA Dodgers") == "Los Angeles Dodgers"


def test_player_aliases():
    assert normalize_player("Shohei Ohtani Jr") == "Shohei Ohtani"


def test_league_and_period_normalization():
    assert normalize_league("baseball") == "MLB"
    assert normalize_period("regulation only") == "regulation"


def test_parse_datetime_adds_timezone():
    assert parse_datetime("2026-07-16T19:10:00").tzinfo is not None
