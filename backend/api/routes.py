from fastapi import APIRouter
from backend.config import settings

router = APIRouter()

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/config/public")
def public_config() -> dict[str, float | int]:
    return {
        "minimum_roi": settings.minimum_roi,
        "minimum_match_confidence": settings.minimum_match_confidence,
        "stale_after_seconds": settings.stale_after_seconds,
    }

@router.get("/markets")
def markets() -> list[dict]:
    return []

@router.get("/matches")
def matches() -> list[dict]:
    return []

@router.get("/opportunities")
def opportunities() -> list[dict]:
    return []
