import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated

from db.loaders import open_connection
from db.queries.range import fetch_range_messages
from fastapi import APIRouter, Query, Request
from models.message import MessageType
from models.sender import GROUP_SERVER, SenderRegistry
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

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


class RangeMessage(BaseModel):
    timestamp: str  # "YYYY-MM-DDTHH:MM" local time
    chat_name: str
    sender_name: str
    text: str | None
    message_type: int


class DayBucket(BaseModel):
    bucket: str  # "YYYY-MM-DD" for daily grouping
    chat_name: str
    count: int


class RangeDetail(BaseModel):
    date_from: str
    date_to: str
    total_messages: int
    active_chats: int
    senders: list[str]
    timeline: list[DayBucket]
    messages: list[RangeMessage]


_VALID_BUCKETS = {"hourly", "daily", "weekly", "monthly"}


@router.get("/range", response_model=RangeDetail)
def get_range_detail(
    date_from: datetime,
    date_to: datetime,
    request: Request,
    bucket: Annotated[str, Query(pattern="^(hourly|daily|weekly|monthly|yearly)$")] = "daily",
) -> RangeDetail:
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry

    logger.info(f"Loading range detail: {date_from} → {date_to} (bucket={bucket})")
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        rows = list(fetch_range_messages(db.msgstore, date_from, date_to, bucket=bucket))

    if not rows:
        return RangeDetail(
            date_from=date_from.isoformat(timespec="minutes"),
            date_to=date_to.isoformat(timespec="minutes"),
            total_messages=0,
            active_chats=0,
            senders=[],
            timeline=[],
            messages=[],
        )

    messages: list[RangeMessage] = []
    bucket_counts: dict[tuple[str, str], int] = {}
    chat_name_set: set[str] = set()
    sender_freq: dict[str, int] = {}

    for r in rows:
        is_group = r.chat_server == GROUP_SERVER
        chat_name = registry.resolve_chat_name(r.chat_subject, r.chat_server, r.chat_phone or "")
        sender = registry.resolve_sender(
            phone=r.sender_phone,
            from_me=bool(r.from_me),
            chat_phone=r.chat_phone or "",
            is_group=is_group,
        )
        text = r.text_data or _TYPE_LABELS.get(r.message_type)

        chat_name_set.add(chat_name)
        sender_freq[sender.display_name] = sender_freq.get(sender.display_name, 0) + 1
        bucket_counts[(r.date_bucket, chat_name)] = bucket_counts.get((r.date_bucket, chat_name), 0) + 1

        messages.append(
            RangeMessage(
                timestamp=r.local_dt,
                chat_name=chat_name,
                sender_name=sender.display_name,
                text=text,
                message_type=r.message_type,
            )
        )

    timeline = [
        DayBucket(bucket=bucket, chat_name=chat, count=count) for (bucket, chat), count in sorted(bucket_counts.items())
    ]
    senders = sorted(sender_freq, key=lambda s: -sender_freq[s])

    logger.info(f"Range {date_from}→{date_to}: {len(messages)} messages, {len(chat_name_set)} chats")
    return RangeDetail(
        date_from=date_from.isoformat(timespec="minutes"),
        date_to=date_to.isoformat(timespec="minutes"),
        total_messages=len(messages),
        active_chats=len(chat_name_set),
        senders=senders,
        timeline=timeline,
        messages=messages,
    )
