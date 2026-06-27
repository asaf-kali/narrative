from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime

from db.loaders import IndexMessage
from models.message import MessageType
from semantic_search.session import Session

_TEXT_TYPE = int(MessageType.TEXT)


def iterate_sessions(
    messages: Iterator[IndexMessage],
    chat_id: int,
    chat_name: str,
    gap_seconds: int,
    min_session_chars: int = 0,
    max_session_messages: int = 0,
) -> Iterator[Session]:
    """Group a chat's flat message stream into sessions.

    A session ends on an inactivity gap (once it holds enough text) or when it
    reaches ``max_session_messages`` — the hard cap keeps each embedding vector
    focused on a single stretch of conversation instead of averaging a whole
    multi-topic burst into one diluted centroid.
    """
    gap_ms = gap_seconds * 1000
    buffer: list[IndexMessage] = []
    buffer_text_chars = 0

    for msg in messages:
        if _should_split(buffer, msg, gap_ms, buffer_text_chars, min_session_chars, max_session_messages):
            yield from _emit(chat_id=chat_id, chat_name=chat_name, rows=buffer)
            buffer = []
            buffer_text_chars = 0
        buffer.append(msg)
        if msg.message_type == _TEXT_TYPE and msg.text_data:
            buffer_text_chars += len(msg.text_data)

    yield from _emit(chat_id=chat_id, chat_name=chat_name, rows=buffer)


def _should_split(
    buffer: list[IndexMessage],
    msg: IndexMessage,
    gap_ms: int,
    buffer_text_chars: int,
    min_session_chars: int,
    max_session_messages: int,
) -> bool:
    if not buffer:
        return False
    if max_session_messages > 0 and len(buffer) >= max_session_messages:
        return True
    gap_exceeded = msg.timestamp - buffer[-1].timestamp > gap_ms
    return gap_exceeded and buffer_text_chars >= min_session_chars


def _emit(chat_id: int, chat_name: str, rows: list[IndexMessage]) -> Iterator[Session]:
    if not rows:
        return
    session = _build_session(chat_id=chat_id, chat_name=chat_name, rows=rows)
    if session is not None:
        yield session


def _build_session(
    chat_id: int,
    chat_name: str,
    rows: list[IndexMessage],
) -> Session | None:
    text_rows = [r for r in rows if r.message_type == _TEXT_TYPE and r.text_data and r.text_data.strip()]
    if not text_rows:
        return None
    embed_text = "\n".join(r.text_data.strip() for r in text_rows)
    display_text = "\n".join(f"{r.sender_name}: {r.text_data.strip()}" for r in text_rows)
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
        embed_text=embed_text,
        display_text=display_text,
    )
