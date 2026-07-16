from datetime import datetime
from zoneinfo import ZoneInfo
from backend.normalizer.player_aliases import PLAYER_ALIASES
from backend.normalizer.team_aliases import TEAM_ALIASES

SPORT_ALIASES = {"baseball": "MLB", "mlb": "MLB", "football": "NFL", "nfl": "NFL", "basketball": "NBA", "nba": "NBA", "hockey": "NHL", "nhl": "NHL"}

def _key(value: str) -> str:
    return " ".join(value.strip().lower().replace(".", "").split())

def normalize_team(value: str | None) -> str | None:
    if not value:
        return None
    return TEAM_ALIASES.get(_key(value), value.strip())

def normalize_player(value: str | None) -> str | None:
    if not value:
        return None
    return PLAYER_ALIASES.get(_key(value), value.strip())

def normalize_league(value: str | None) -> str:
    if not value:
        return "UNKNOWN"
    return SPORT_ALIASES.get(_key(value), value.strip().upper())

def normalize_period(value: str | None) -> str:
    if not value:
        return "full_game"
    key = _key(value)
    if key in {"game", "full game", "including overtime", "including extra innings"}:
        return "full_game"
    if key in {"regulation", "regulation only"}:
        return "regulation"
    return key.replace(" ", "_")

def parse_datetime(value: str, default_tz: str = "UTC") -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(default_tz))
    return parsed
