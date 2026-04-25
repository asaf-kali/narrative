import logging
from pathlib import Path

from db.loaders import open_connection  # ty: ignore[unresolved-import]
from db.queries.day import fetch_day_messages  # ty: ignore[unresolved-import]
from fastapi import APIRouter, HTTPException, Request
from models.message import MessageType  # ty: ignore[unresolved-import]
from models.sender import GROUP_SERVER, SenderRegistry  # ty: ignore[unresolved-import]
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


class DayMessage(BaseModel):
    time: str
    chat_name: str
    sender_name: str
    text: str | None
    message_type: int


class DayBucket(BaseModel):
    bucket: str  # "HH:MM" rounded to 5-minute boundary
    chat_name: str
    count: int


class DayDetail(BaseModel):
    date: str
    total_messages: int
    active_chats: int
    senders: list[str]  # ordered by frequency descending
    timeline: list[DayBucket]
    messages: list[DayMessage]


@router.get("/day/{date}", response_model=DayDetail)
def get_day_detail(date: str, request: Request) -> DayDetail:
    _DATE_LEN = 10
    if len(date) != _DATE_LEN or date[4] != "-" or date[7] != "-":
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry

    logger.info(f"Loading day detail for {date}")
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        rows = list(fetch_day_messages(db.msgstore, date))

    if not rows:
        return DayDetail(date=date, total_messages=0, active_chats=0, senders=[], timeline=[], messages=[])

    messages: list[DayMessage] = []
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
        text = _message_text(r.text_data, r.message_type)

        chat_name_set.add(chat_name)
        sender_freq[sender.display_name] = sender_freq.get(sender.display_name, 0) + 1

        hh, mm = r.time.split(":")
        bucket = f"{hh}:{int(mm) // 5 * 5:02d}"
        bucket_counts[(bucket, chat_name)] = bucket_counts.get((bucket, chat_name), 0) + 1

        messages.append(
            DayMessage(
                time=r.time,
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

    logger.info(f"Day {date}: {len(messages)} messages, {len(chat_name_set)} chats, {len(senders)} senders")
    return DayDetail(
        date=date,
        total_messages=len(messages),
        active_chats=len(chat_name_set),
        senders=senders,
        timeline=timeline,
        messages=messages,
    )


# ── private helpers ───────────────────────────────────────────────────────────


def _message_text(text_data: str | None, message_type: int) -> str | None:
    if text_data:
        return text_data
    return _TYPE_LABELS.get(message_type)
