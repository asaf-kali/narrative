from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionBase(BaseModel):
    session_id: str
    chat_id: int
    timestamp_start: datetime
    timestamp_end: datetime


class SessionMeta(SessionBase):
    """Persisted session metadata stored in state.db."""

    min_message_id: int
    max_message_id: int


class SessionRecord(SessionBase):
    """Session row written to the LanceDB vector store."""

    chat_name: str
    vector: list[float]
