import logging
from pathlib import Path

from fastapi import APIRouter, Request

from narrative.db import cached
from narrative.db.cached import DailyCount

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats/daily")
def get_daily_counts(request: Request) -> list[dict[str, int | str]]:
    msgstore: Path = request.app.state.msgstore_path
    counts: list[DailyCount] = cached.daily_counts(msgstore_path=msgstore)
    return [{"date": c.day, "count": c.count} for c in counts]
