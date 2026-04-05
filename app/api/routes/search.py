import logging
from pathlib import Path

from db.loaders import open_connection
from db.queries.search import search_messages
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

_GROUP_SERVER = "g.us"
_MIN_QUERY_LEN = 2


class SearchResult(BaseModel):
    chat_id: int
    chat_name: str
    sender_name: str
    timestamp: str
    text: str


@router.get("/search", response_model=list[SearchResult])
def global_search(q: str, request: Request, limit: int = 50) -> list[SearchResult]:
    if len(q.strip()) < _MIN_QUERY_LEN:
        raise HTTPException(status_code=400, detail=f"Query must be at least {_MIN_QUERY_LEN} characters")

    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    contact_names: dict[str, str] = request.app.state.contact_names or {}

    logger.info(f"Global search: {q!r} (limit={limit})")
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        rows = search_messages(db.msgstore, q.strip(), limit)

    results: list[SearchResult] = []
    for row in rows:
        r = dict(row)
        chat_name = _resolve_chat_name(r, contact_names)
        sender_name = _resolve_sender(r, contact_names)
        results.append(
            SearchResult(
                chat_id=int(r["chat_id"]),
                chat_name=chat_name,
                sender_name=sender_name,
                timestamp=str(r["timestamp"]),
                text=str(r["text_data"]),
            )
        )
    return results


# ── private helpers (same logic as day.py) ────────────────────────────────────


def _resolve_chat_name(r: dict[str, object], contact_names: dict[str, str]) -> str:
    subject = str(r.get("chat_subject") or "")
    server = str(r.get("chat_server") or "")
    phone = str(r.get("chat_phone") or "")
    if subject:
        return subject
    if server == _GROUP_SERVER:
        return f"Group ({phone})"
    return contact_names.get(phone) or phone or "Unknown"


def _resolve_sender(r: dict[str, object], contact_names: dict[str, str]) -> str:
    if r.get("from_me") == 1:
        return "Me"
    phone = str(r.get("sender_phone") or "")
    chat_server = str(r.get("chat_server") or "")
    if not phone and chat_server != _GROUP_SERVER:
        chat_phone = str(r.get("chat_phone") or "")
        return contact_names.get(chat_phone) or chat_phone or "Unknown"
    return contact_names.get(phone) or phone or "Unknown"
