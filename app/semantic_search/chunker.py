from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from db.loaders import (
    COL_CHAT_NAME,
    COL_CHAT_ROW_ID,
    COL_MESSAGE_ID,
    COL_MESSAGE_TYPE,
    COL_TEXT_DATA,
    COL_TIMESTAMP,
    IndexMessage,
)
from models.message import MessageType
from numpy.typing import NDArray

_COL_TIMESTAMP_MS = "timestamp_ms"


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


def chunk_messages(df: pd.DataFrame, gap_seconds: int) -> Iterator[Session]:
    work = _prepare(df)
    text_mask = _text_mask(work)
    gap_ms = gap_seconds * 1000
    for chat_id_val, group in work.groupby(COL_CHAT_ROW_ID, sort=False):
        chat_mask = text_mask.reindex(group.index, fill_value=False)
        yield from _chunk_chat(group, chat_mask, int(chat_id_val), gap_ms)


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if pd.api.types.is_datetime64_any_dtype(work[COL_TIMESTAMP]):
        work[_COL_TIMESTAMP_MS] = work[COL_TIMESTAMP].astype("int64") // 1_000_000
    else:
        work[_COL_TIMESTAMP_MS] = work[COL_TIMESTAMP].astype("int64")
    return work.sort_values([COL_CHAT_ROW_ID, _COL_TIMESTAMP_MS]).reset_index(drop=True)


def _text_mask(df: pd.DataFrame) -> pd.Series[bool]:
    return (  # type: ignore[no-any-return]
        (df[COL_MESSAGE_TYPE] == int(MessageType.TEXT))
        & df[COL_TEXT_DATA].notna()
        & (df[COL_TEXT_DATA].str.strip() != "")
    )


def _chunk_chat(
    group: pd.DataFrame,
    text_mask: pd.Series[bool],
    chat_id: int,
    gap_ms: int,
) -> Iterator[Session]:
    chat_name = str(group[COL_CHAT_NAME].iloc[0])
    timestamps: NDArray[np.int64] = group[_COL_TIMESTAMP_MS].to_numpy()
    msg_ids: NDArray[np.int64] = group[COL_MESSAGE_ID].to_numpy()
    texts = group[COL_TEXT_DATA].where(text_mask).fillna("")

    session_start = 0
    for i in range(1, len(group) + 1):
        is_last = i == len(group)
        gap_exceeded = not is_last and (timestamps[i] - timestamps[i - 1] > gap_ms)
        if not (gap_exceeded or is_last):
            continue
        session = _build_session(chat_id, chat_name, timestamps, msg_ids, texts, session_start, i)
        session_start = i
        if session is None:
            continue
        yield session


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
            session = _build_session_from_messages(
                chat_id=chat_id, chat_name=chat_name, rows=buffer, start=0, end=len(buffer)
            )
            if session is not None:
                yield session
            buffer = []
        buffer.append(msg)

    if buffer:
        session = _build_session_from_messages(chat_id, chat_name, buffer, 0, len(buffer))
        if session is not None:
            yield session


def _build_session_from_messages(
    chat_id: int,
    chat_name: str,
    rows: list[IndexMessage],
    start: int,
    end: int,
) -> Session | None:
    window = rows[start:end]
    session_texts = [
        r.text_data
        for r in window
        if r.message_type == int(MessageType.TEXT) and r.text_data is not None and r.text_data.strip()
    ]
    if not session_texts:
        return None
    min_id = window[0].message_id
    session_id = hashlib.sha256(f"{chat_id}:{min_id}".encode()).hexdigest()[:16]
    return Session(
        session_id=session_id,
        chat_id=chat_id,
        chat_name=chat_name,
        timestamp_start=datetime.fromtimestamp(window[0].timestamp / 1000, tz=UTC),
        timestamp_end=datetime.fromtimestamp(window[-1].timestamp / 1000, tz=UTC),
        min_message_id=min_id,
        max_message_id=window[-1].message_id,
        message_count=len(window),
        embed_text=" ".join(session_texts),
    )


def _build_session(
    chat_id: int,
    chat_name: str,
    timestamps: NDArray[np.int64],
    msg_ids: NDArray[np.int64],
    texts: pd.Series[str],
    start: int,
    end: int,
) -> Session | None:
    session_texts = [t for t in texts.iloc[start:end] if t]
    if not session_texts:
        return None
    min_id = int(msg_ids[start])
    session_id = hashlib.sha256(f"{chat_id}:{min_id}".encode()).hexdigest()[:16]
    return Session(
        session_id=session_id,
        chat_id=chat_id,
        chat_name=chat_name,
        timestamp_start=datetime.fromtimestamp(int(timestamps[start]) / 1000, tz=UTC),
        timestamp_end=datetime.fromtimestamp(int(timestamps[end - 1]) / 1000, tz=UTC),
        min_message_id=min_id,
        max_message_id=int(msg_ids[end - 1]),
        message_count=end - start,
        embed_text=" ".join(session_texts),
    )
