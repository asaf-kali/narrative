from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pandas as pd
from models.message import MessageType

_GAP_MS = 5 * 60 * 1000  # 5-minute gap between sessions


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


def chunk_messages(df: pd.DataFrame, gap_ms: int = _GAP_MS) -> list[Session]:
    # Expects columns: message_id, chat_row_id, chat_name, timestamp (datetime or int ms), text_data, message_type
    work = df.copy()

    # Normalise timestamp to integer ms so gap arithmetic is uniform
    if pd.api.types.is_datetime64_any_dtype(work["timestamp"]):
        work["timestamp_ms"] = work["timestamp"].astype("int64") // 1_000_000
    else:
        work["timestamp_ms"] = work["timestamp"].astype("int64")

    text_mask = (
        (work["message_type"] == int(MessageType.TEXT))
        & work["text_data"].notna()
        & (work["text_data"].str.strip() != "")
    )
    work = work.sort_values(["chat_row_id", "timestamp_ms"]).reset_index(drop=True)
    text_mask = text_mask.reindex(work.index, fill_value=False)

    sessions: list[Session] = []

    for chat_id_val, group in work.groupby("chat_row_id", sort=False):
        chat_id = int(chat_id_val)
        chat_name: str = str(group["chat_name"].iloc[0])
        timestamps = group["timestamp_ms"].to_numpy()
        msg_ids = group["message_id"].to_numpy()
        texts = group["text_data"].where(text_mask.reindex(group.index, fill_value=False)).fillna("")

        session_start = 0
        for i in range(1, len(group) + 1):
            is_last = i == len(group)
            new_session = (not is_last) and (timestamps[i] - timestamps[i - 1] > gap_ms)

            if new_session or is_last:
                session_texts = [t for t in texts.iloc[session_start:i] if t]
                if not session_texts:
                    session_start = i
                    continue

                min_id = int(msg_ids[session_start])
                max_id = int(msg_ids[i - 1])
                session_id = hashlib.sha256(f"{chat_id}:{min_id}".encode()).hexdigest()[:16]

                sessions.append(
                    Session(
                        session_id=session_id,
                        chat_id=chat_id,
                        chat_name=chat_name,
                        timestamp_start=int(timestamps[session_start]),
                        timestamp_end=int(timestamps[i - 1]),
                        min_message_id=min_id,
                        max_message_id=max_id,
                        embed_text=" ".join(session_texts),
                    )
                )
                session_start = i

    return sessions
