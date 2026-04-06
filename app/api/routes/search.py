import logging
from pathlib import Path

from db.loaders import open_connection
from db.queries.search import search_messages
from fastapi import APIRouter, HTTPException, Request
from models.sender import GROUP_SERVER, SenderRegistry
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

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
    registry: SenderRegistry = request.app.state.sender_registry

    logger.info(f"Global search: {q!r} (limit={limit})")
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        rows = list(search_messages(db.msgstore, q.strip(), limit))

    results: list[SearchResult] = []
    for r in rows:
        is_group = r.chat_server == GROUP_SERVER
        chat_name = registry.resolve_chat_name(r.chat_subject, r.chat_server, r.chat_phone or "")
        sender = registry.resolve_sender(
            phone=r.sender_phone,
            from_me=bool(r.from_me),
            chat_phone=r.chat_phone or "",
            is_group=is_group,
        )
        results.append(
            SearchResult(
                chat_id=r.chat_id,
                chat_name=chat_name,
                sender_name=sender.display_name,
                timestamp=r.timestamp,
                text=r.text_data,
            )
        )
    return results
