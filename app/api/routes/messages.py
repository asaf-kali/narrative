import logging
from datetime import UTC, datetime, tzinfo
from typing import Annotated, Any

import pandas as pd
from api.deps import get_df
from fastapi import APIRouter, Query, Request
from models.config import AnalysisConfig
from models.message import MessageType

logger = logging.getLogger(__name__)
router = APIRouter()

_LOCAL_TZ: tzinfo = datetime.now().astimezone().tzinfo or UTC

_TYPE_LABELS: dict[int, str] = {
    MessageType.IMAGE: "[Image]",
    MessageType.AUDIO: "[Audio]",
    MessageType.VIDEO: "[Video]",
    MessageType.CONTACT: "[Contact]",
    MessageType.LOCATION: "[Location]",
    MessageType.DOCUMENT: "[Document]",
    MessageType.STICKER: "[Sticker]",
    MessageType.GIF: "[GIF]",
}


@router.get("/messages")
def get_global_messages(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    chat_ids: Annotated[list[int] | None, Query()] = None,
    sender_ids: Annotated[list[str] | None, Query()] = None,
) -> dict[str, Any]:
    logger.info(
        f"Fetching messages with filters: date_from={date_from}, date_to={date_to}, "
        f"search={search}, chat_ids={chat_ids}, sender_ids={sender_ids}"
    )
    config = AnalysisConfig(chat_id=None, exclude_system=True)
    df = get_df(request, config)
    if df.empty:
        return {"total": 0, "messages": []}

    if date_from is not None:
        df = df[df["timestamp"] >= _to_ts(date_from)]
    if date_to is not None:
        df = df[df["timestamp"] <= _to_ts(date_to)]
    if chat_ids:
        df = df[df["chat_row_id"].isin(chat_ids)]
    if sender_ids:
        df = df[_build_sender_id_series(df).isin(sender_ids)]
    if search:
        df = df[df["text_data"].str.contains(search, case=False, na=False)]

    df = df.sort_values("timestamp", ascending=False)
    total = len(df)
    page = df.iloc[offset : offset + limit]

    messages = []
    for _, row in page.iterrows():
        text = row.get("text_data")
        if not text:
            text = _TYPE_LABELS.get(int(row["message_type"]))
        phone = str(row.get("sender_phone", "") or "")
        from_me = int(row.get("from_me", 0))
        s_id = "me" if from_me else (phone or str(row["sender_name"]))
        messages.append(
            {
                "timestamp": row["timestamp"].strftime("%Y-%m-%dT%H:%M:%S"),
                "chat_name": str(row.get("chat_name", "")),
                "sender_name": str(row["sender_name"]),
                "sender_id": s_id,
                "text": str(text) if text else None,
                "message_type": int(row["message_type"]),
            }
        )

    return {"total": total, "messages": messages}


@router.get("/senders")
def get_senders(request: Request) -> list[dict[str, Any]]:
    logger.info("Fetching senders with message counts")
    config = AnalysisConfig(chat_id=None, exclude_system=True)
    df = get_df(request, config)
    if df.empty:
        return []

    # For 1-on-1 received messages, sender_phone is "" — the peer's phone is in
    # chat_phone. Use that as the effective phone so name+phone search both work.
    phone_col = df["sender_phone"].fillna("").astype(str)
    chat_phone_col = df["chat_phone"].fillna("").astype(str)
    from_me_mask = df["from_me"] == 1
    effective_phone = phone_col.where(
        (phone_col != "") | df["is_group"] | from_me_mask,
        chat_phone_col,
    )
    df = df.assign(_sender_id=_build_sender_id_series(df), _effective_phone=effective_phone)
    counts = df.groupby("_sender_id").size().rename("message_count")
    df_unique = df.drop_duplicates(subset="_sender_id").join(counts, on="_sender_id")
    df_unique = df_unique.sort_values("message_count", ascending=False)

    return [
        {
            "sender_id": str(row["_sender_id"]),
            "sender_name": str(row["sender_name"]),
            "phone": str(row["_effective_phone"]),
            "message_count": int(row["message_count"]),
        }
        for _, row in df_unique.iterrows()
    ]


def _build_sender_id_series(df: pd.DataFrame) -> pd.Series:
    """Derive sender_id per row: 'me' if from_me, else phone or sender_name as fallback."""
    phone_col = df["sender_phone"].fillna("").astype(str)
    name_col = df["sender_name"].astype(str)
    fallback = phone_col.where(phone_col != "", name_col)
    return fallback.mask(df["from_me"] == 1, "me")


def _to_ts(dt: datetime) -> pd.Timestamp:
    """Convert a (possibly tz-naive) datetime to a tz-aware Timestamp in local time."""
    ts = pd.Timestamp(dt)
    if ts.tzinfo is None:
        return ts.tz_localize(_LOCAL_TZ)
    return ts.tz_convert(_LOCAL_TZ)
