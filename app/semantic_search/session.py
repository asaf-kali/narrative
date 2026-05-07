from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Session(BaseModel):
    """In-memory pipeline object produced by the chunker."""

    session_id: str
    chat_id: int
    chat_name: str
    timestamp_start: datetime
    timestamp_end: datetime
    min_message_id: int
    max_message_id: int
    message_count: int
    embed_text: str  # joined text for embedding only — not stored persistently


class SessionMeta(BaseModel):
    """Persisted session metadata stored in state.db."""

    session_id: str
    chat_id: int
    min_message_id: int
    max_message_id: int
    timestamp_start: datetime
    timestamp_end: datetime


class SessionRecord(BaseModel):
    """Session row written to the LanceDB vector store."""

    session_id: str
    chat_id: int
    chat_name: str
    timestamp_start: datetime
    timestamp_end: datetime
    vector: list[float]
