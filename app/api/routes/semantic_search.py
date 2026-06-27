from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from itertools import chain
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from semantic_search.embedder import EmbedderUnavailableError
from semantic_search.params import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_GAP_SECONDS,
    DEFAULT_MAX_SESSION_MESSAGES,
    DEFAULT_MIN_SESSION_CHARS,
    DEFAULT_RERANK_CANDIDATES,
)
from semantic_search.reranker import Reranker, RerankerUnavailableError
from semantic_search.vector_store import SearchHit, VectorStore

logger = logging.getLogger(__name__)
router = APIRouter()

_MIN_QUERY_LEN = 2


class SemanticSearchHit(BaseModel):
    chat_id: int
    chat_name: str
    timestamp_start: datetime
    timestamp_end: datetime
    text: str
    score: float


class ChatIndexStatus(BaseModel):
    status: Literal["indexed", "partial", "none"]
    session_count: int


@router.get("/semantic-search", response_model=list[SemanticSearchHit])
def semantic_search(
    q: str,
    request: Request,
    limit: int = 10,
    chat_id: int | None = None,
) -> list[SemanticSearchHit]:
    query = q.strip()
    if len(query) < _MIN_QUERY_LEN:
        raise HTTPException(status_code=400, detail=f"Query must be at least {_MIN_QUERY_LEN} characters")

    store = getattr(request.app.state, "vector_store", None)
    embedder = getattr(request.app.state, "embedder", None)
    if store is None or embedder is None:
        raise HTTPException(
            status_code=503,
            detail="Semantic search index not available — run: just index --msgstore <path>",
        )
    reranker: Reranker | None = getattr(request.app.state, "reranker", None)

    logger.info(f"Semantic search: {query!r} (limit={limit}, chat_id={chat_id}, rerank={reranker is not None})")
    try:
        query_vec = embedder.embed([query])[0]
    except EmbedderUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    hits = _retrieve(store=store, reranker=reranker, query=query, query_vec=query_vec, limit=limit, chat_id=chat_id)
    return [
        SemanticSearchHit(
            chat_id=h.chat_id,
            chat_name=h.chat_name,
            timestamp_start=h.timestamp_start,
            timestamp_end=h.timestamp_end,
            text=h.text,
            score=h.score,
        )
        for h in hits
    ]


@router.get("/chats/{chat_id}/index-status", response_model=ChatIndexStatus)
def get_chat_index_status(chat_id: int, request: Request) -> ChatIndexStatus:
    from db.queries.messages import count_messages_for_chat  # noqa: PLC0415

    state_db = getattr(request.app.state, "state_db", None)
    if state_db is None:
        return ChatIndexStatus(status="none", session_count=0)

    max_indexed = state_db.get_max_indexed(chat_id=chat_id)
    session_count = state_db.count_sessions_for_chat(chat_id=chat_id)

    if max_indexed == 0:
        return ChatIndexStatus(status="none", session_count=0)

    msgstore_path = request.app.state.msgstore_path
    with sqlite3.connect(str(msgstore_path)) as conn:
        remaining = count_messages_for_chat(conn=conn, chat_id=chat_id, after_id=max_indexed)

    status: Literal["indexed", "partial", "none"] = "indexed" if remaining == 0 else "partial"
    return ChatIndexStatus(status=status, session_count=session_count)


@router.post("/chats/{chat_id}/index")
def index_chat(
    chat_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    from semantic_search.indexer import run_chat  # noqa: PLC0415

    state_db = getattr(request.app.state, "state_db", None)
    if state_db is None:
        raise HTTPException(status_code=503, detail="Semantic search not available")

    msgstore_path = request.app.state.msgstore_path
    wadb_path = getattr(request.app.state, "wadb_path", None)
    search_dir = getattr(request.app.state, "search_dir", None)
    if search_dir is None:
        raise HTTPException(status_code=503, detail="Search directory not configured")

    background_tasks.add_task(
        run_chat,
        chat_id=chat_id,
        msgstore_path=msgstore_path,
        wadb_path=wadb_path,
        search_dir=search_dir,
        gap_seconds=DEFAULT_GAP_SECONDS,
        batch_size=DEFAULT_BATCH_SIZE,
        chunk_size=DEFAULT_CHUNK_SIZE,
        min_session_chars=DEFAULT_MIN_SESSION_CHARS,
        max_session_messages=DEFAULT_MAX_SESSION_MESSAGES,
    )
    return {"status": "started"}


# ── private helpers ──────────────────────────────────────────────────────────


def _retrieve(
    store: VectorStore,
    reranker: Reranker | None,
    query: str,
    query_vec: list[float],
    limit: int,
    chat_id: int | None,
) -> list[SearchHit]:
    if reranker is None:
        vector_only: list[SearchHit] = store.search(query_vec, limit=limit, chat_id_filter=chat_id)
        return vector_only

    pool = max(DEFAULT_RERANK_CANDIDATES, limit * 5)
    candidates = _gather_candidates(store=store, query=query, query_vec=query_vec, pool=pool, chat_id=chat_id)
    try:
        reranked: list[SearchHit] = reranker.rerank(query=query, candidates=candidates, top_n=limit)
    except RerankerUnavailableError:
        logger.warning("Reranker unavailable — returning vector results", exc_info=True)
        return candidates[:limit]
    return reranked


def _gather_candidates(
    store: VectorStore,
    query: str,
    query_vec: list[float],
    pool: int,
    chat_id: int | None,
) -> list[SearchHit]:
    """Union of dense (semantic) and BM25 (lexical) candidates, deduped by session.

    The lexical leg recovers exact-term matches — names, rare Hebrew words — that a
    single dense vector can miss; the reranker then decides the final order.
    """
    vector_hits = store.search(query_vec, limit=pool, chat_id_filter=chat_id)
    text_hits = store.search_text(query, limit=pool, chat_id_filter=chat_id)
    merged: dict[str, SearchHit] = {}
    for hit in chain(vector_hits, text_hits):
        merged.setdefault(hit.session_id, hit)
    return list(merged.values())
