import logging
from pathlib import Path

from db.loaders import open_connection
from db.queries.day import fetch_day_messages
from fastapi import APIRouter, HTTPException, Request
from models.message import MessageType
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

_GROUP_SERVER = "g.us"

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
    contact_names: dict[str, str] = request.app.state.contact_names or {}

    logger.info(f"Loading day detail for {date}")
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        rows = fetch_day_messages(db.msgstore, date)

    if not rows:
        return DayDetail(date=date, total_messages=0, active_chats=0, senders=[], timeline=[], messages=[])

    messages: list[DayMessage] = []
    bucket_counts: dict[tuple[str, str], int] = {}
    chat_name_set: set[str] = set()
    sender_freq: dict[str, int] = {}

    for row in rows:
        r = dict(row)
        chat_name = _resolve_chat_name(r, contact_names)
        sender_name = _resolve_sender(r, contact_names)
        text = _message_text(r)

        chat_name_set.add(chat_name)
        sender_freq[sender_name] = sender_freq.get(sender_name, 0) + 1

        hh, mm = r["time"].split(":")
        bucket = f"{hh}:{int(mm) // 5 * 5:02d}"
        bucket_counts[(bucket, chat_name)] = bucket_counts.get((bucket, chat_name), 0) + 1

        messages.append(
            DayMessage(
                time=r["time"],
                chat_name=chat_name,
                sender_name=sender_name,
                text=text,
                message_type=r["message_type"],
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


def _resolve_chat_name(r: dict[str, object], contact_names: dict[str, str]) -> str:
    subject = str(r.get("chat_subject") or "")
    server = str(r.get("chat_server") or "")
    phone = str(r.get("chat_phone") or "")
    if subject:
        return subject
    if server == _GROUP_SERVER:
        return f"Group ({phone})"
    return contact_names.get(phone) or phone or "Unknown"


def _resolve_sender(r: dict[str, object], contact_names: dict[str, str]) -> str:
    if r.get("from_me") == 1:
        return "Me"
    phone = str(r.get("sender_phone") or "")
    chat_server = str(r.get("chat_server") or "")
    # Direct chat: sender_phone is empty; use the chat phone instead
    if not phone and chat_server != _GROUP_SERVER:
        chat_phone = str(r.get("chat_phone") or "")
        return contact_names.get(chat_phone) or chat_phone or "Unknown"
    return contact_names.get(phone) or phone or "Unknown"


def _message_text(r: dict[str, object]) -> str | None:
    text = r.get("text_data")
    if text:
        return str(text)
    raw = r.get("message_type")
    msg_type = int(raw) if isinstance(raw, (int, float)) else 0
    return _TYPE_LABELS.get(msg_type)
