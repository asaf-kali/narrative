import logging
from pathlib import Path

from fastapi import APIRouter, Request

from narrative.db.loaders import open_connection
from narrative.db.queries.stats import fetch_daily_counts

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats/daily")
def get_daily_counts(request: Request) -> list[dict[str, int | str]]:
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    logger.info("Loading daily message counts across all chats")
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        rows = fetch_daily_counts(db.msgstore)
    return [{"date": str(row["day"]), "count": int(row["count"])} for row in rows]
