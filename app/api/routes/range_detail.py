import logging
from datetime import UTC, datetime
from pathlib import Path

from db.loaders import open_connection
from db.queries.range import fetch_range_messages
from fastapi import APIRouter, Request
from models.message import MessageType
from models.sender import GROUP_SERVER, SenderRegistry
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

NUM_BUCKETS = 30

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


class RangeBucket(BaseModel):
    bucket: str  # "YYYY-MM-DDTHH:MM" start of bucket (local time)
    chat_name: str
    count: int


class RangeDetail(BaseModel):
    date_from: str
    date_to: str
    total_messages: int
    active_chats: int
    senders: list[str]
    buckets: list[str]  # all NUM_BUCKETS labels, including empty ones
    timeline: list[RangeBucket]
    messages: list[RangeMessage]


@router.get("/range", response_model=RangeDetail)
def get_range_detail(
    date_from: datetime,
    date_to: datetime,
    request: Request,
) -> RangeDetail:
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry

    from_ms = int(date_from.timestamp() * 1000)
    to_ms = int(date_to.timestamp() * 1000)
    bucket_size_ms = (to_ms - from_ms) / NUM_BUCKETS

    # Pre-compute the label for each bucket (local datetime of its start)
    bucket_labels = [
        datetime.fromtimestamp((from_ms + i * bucket_size_ms) / 1000, tz=UTC).astimezone().strftime("%Y-%m-%dT%H:%M")
        for i in range(NUM_BUCKETS)
    ]

    logger.info(f"Loading range detail: {date_from} → {date_to} (bucket_size={bucket_size_ms / 1000:.0f}s)")
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        rows = list(fetch_range_messages(db.msgstore, date_from, date_to))

    if not rows:
        return RangeDetail(
            date_from=date_from.isoformat(timespec="minutes"),
            date_to=date_to.isoformat(timespec="minutes"),
            total_messages=0,
            active_chats=0,
            senders=[],
            buckets=bucket_labels,
            timeline=[],
            messages=[],
        )

    messages: list[RangeMessage] = []
    # bucket_idx → chat_name → count
    bucket_chat_counts: dict[int, dict[str, int]] = {i: {} for i in range(NUM_BUCKETS)}
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

        bucket_idx = min(int((r.timestamp - from_ms) / bucket_size_ms), NUM_BUCKETS - 1)
        counts = bucket_chat_counts[bucket_idx]
        counts[chat_name] = counts.get(chat_name, 0) + 1

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
        RangeBucket(bucket=bucket_labels[i], chat_name=chat, count=count)
        for i in range(NUM_BUCKETS)
        for chat, count in bucket_chat_counts[i].items()
    ]
    senders = sorted(sender_freq, key=lambda s: -sender_freq[s])

    logger.info(f"Range {date_from}→{date_to}: {len(messages)} messages, {len(chat_name_set)} chats")
    return RangeDetail(
        date_from=date_from.isoformat(timespec="minutes"),
        date_to=date_to.isoformat(timespec="minutes"),
        total_messages=len(messages),
        active_chats=len(chat_name_set),
        senders=senders,
        buckets=bucket_labels,
        timeline=timeline,
        messages=messages,
    )
