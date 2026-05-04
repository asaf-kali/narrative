from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

_MIN_QUERY_LEN = 2


class SemanticSearchHit(BaseModel):
    chat_id: int
    chat_name: str
    timestamp_start: datetime
    timestamp_end: datetime
    score: float


@router.get("/semantic-search", response_model=list[SemanticSearchHit])
def semantic_search(
    q: str,
    request: Request,
    limit: int = 10,
    chat_id: int | None = None,
) -> list[SemanticSearchHit]:
    if len(q.strip()) < _MIN_QUERY_LEN:
        raise HTTPException(status_code=400, detail=f"Query must be at least {_MIN_QUERY_LEN} characters")

    store = getattr(request.app.state, "vector_store", None)
    embedder = getattr(request.app.state, "embedder", None)
    if store is None or embedder is None:
        raise HTTPException(
            status_code=503,
            detail="Semantic search index not available — run: just index --msgstore <path>",
        )

    from search.embedder import EmbedderUnavailableError  # noqa: PLC0415

    logger.info(f"Semantic search: {q!r} (limit={limit}, chat_id={chat_id})")
    try:
        query_vec = embedder.embed([q.strip()])[0]
    except EmbedderUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    hits = store.search(query_vec, limit=limit, chat_id_filter=chat_id)

    return [
        SemanticSearchHit(
            chat_id=h.chat_id,
            chat_name=h.chat_name,
            timestamp_start=datetime.fromtimestamp(h.timestamp_start / 1000, tz=UTC),
            timestamp_end=datetime.fromtimestamp(h.timestamp_end / 1000, tz=UTC),
            score=h.score,
        )
        for h in hits
    ]
