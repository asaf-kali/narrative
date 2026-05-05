from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd
from models.message import MessageType
from numpy.typing import NDArray

_GAP_SECONDS = 15 * 60


@dataclass
class Session:
    session_id: str
    chat_id: int
    chat_name: str
    timestamp_start: int  # ms UTC
    timestamp_end: int  # ms UTC
    min_message_id: int
    max_message_id: int
    embed_text: str  # joined text for embedding only — not stored persistently


def chunk_messages(df: pd.DataFrame, gap_seconds: int = _GAP_SECONDS) -> Iterator[Session]:
    work = _prepare(df)
    text_mask = _text_mask(work)
    gap_ms = gap_seconds * 1000
    for chat_id_val, group in work.groupby("chat_row_id", sort=False):
        chat_mask = text_mask.reindex(group.index, fill_value=False)
        yield from _chunk_chat(group, chat_mask, int(chat_id_val), gap_ms)  # type: ignore[arg-type]


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if pd.api.types.is_datetime64_any_dtype(work["timestamp"]):
        work["timestamp_ms"] = work["timestamp"].astype("int64") // 1_000_000
    else:
        work["timestamp_ms"] = work["timestamp"].astype("int64")
    return work.sort_values(["chat_row_id", "timestamp_ms"]).reset_index(drop=True)


def _text_mask(df: pd.DataFrame) -> pd.Series[bool]:
    return (df["message_type"] == int(MessageType.TEXT)) & df["text_data"].notna() & (df["text_data"].str.strip() != "")


def _chunk_chat(
    group: pd.DataFrame,
    text_mask: pd.Series[bool],
    chat_id: int,
    gap_ms: int,
) -> Iterator[Session]:
    chat_name = str(group["chat_name"].iloc[0])
    timestamps: NDArray[np.int64] = group["timestamp_ms"].to_numpy()
    msg_ids: NDArray[np.int64] = group["message_id"].to_numpy()
    texts = group["text_data"].where(text_mask).fillna("")

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
        timestamp_start=int(timestamps[start]),
        timestamp_end=int(timestamps[end - 1]),
        min_message_id=min_id,
        max_message_id=int(msg_ids[end - 1]),
        embed_text=" ".join(session_texts),
    )
