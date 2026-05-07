from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

from db.loaders import IndexMessage
from models.message import MessageType


@dataclass
class Session:
    session_id: str
    chat_id: int
    chat_name: str
    timestamp_start: datetime
    timestamp_end: datetime
    min_message_id: int
    max_message_id: int
    message_count: int
    embed_text: str  # joined text for embedding only — not stored persistently


def iterate_sessions(
    messages: Iterator[IndexMessage],
    chat_id: int,
    chat_name: str,
    gap_seconds: int,
) -> Iterator[Session]:
    gap_ms = gap_seconds * 1000
    buffer: list[IndexMessage] = []

    for msg in messages:
        if buffer and msg.timestamp - buffer[-1].timestamp > gap_ms:
            session = _build_session(chat_id=chat_id, chat_name=chat_name, rows=buffer)
            if session is not None:
                yield session
            buffer = []
        buffer.append(msg)

    if buffer:
        session = _build_session(chat_id=chat_id, chat_name=chat_name, rows=buffer)
        if session is not None:
            yield session


def _build_session(
    chat_id: int,
    chat_name: str,
    rows: list[IndexMessage],
) -> Session | None:
    session_texts = [
        r.text_data
        for r in rows
        if r.message_type == int(MessageType.TEXT) and r.text_data is not None and r.text_data.strip()
    ]
    if not session_texts:
        return None
    min_id = rows[0].message_id
    session_id = hashlib.sha256(f"{chat_id}:{min_id}".encode()).hexdigest()[:16]
    return Session(
        session_id=session_id,
        chat_id=chat_id,
        chat_name=chat_name,
        timestamp_start=datetime.fromtimestamp(rows[0].timestamp / 1000, tz=UTC),
        timestamp_end=datetime.fromtimestamp(rows[-1].timestamp / 1000, tz=UTC),
        min_message_id=min_id,
        max_message_id=rows[-1].message_id,
        message_count=len(rows),
        embed_text=" ".join(session_texts),
    )
