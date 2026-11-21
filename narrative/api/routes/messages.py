import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import pandas as pd
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from narrative.analysis.reactions import MessageReactions, reactions_by_message
from narrative.analysis.replies import ReplyPreview, replies_by_message
from narrative.db import cached
from narrative.db.attachments import MessageAttachments, load_message_attachments
from narrative.db.cached import MetadataFilters
from narrative.db.loaders import DataLoader, build_messages_df, chat_summaries, datetime_to_ms, open_connection
from narrative.db.queries.messages import fetch_message_bounds, fetch_messages_page
from narrative.db.row_types import MessagesMetadata, RawMessageRow, RawSenderCount
from narrative.models.chat import ChatSort, ChatSummary
from narrative.models.message import message_display_text
from narrative.models.sender import SenderRegistry
from narrative.tracing import span

logger = logging.getLogger(__name__)
router = APIRouter()

_OPTIONS_LIMIT = 100


class SenderInfo(BaseModel):
    sender_id: str
    sender_name: str
    phone: str
    message_count: int


class ChatOptions(BaseModel):
    """Chats with messages in the date range; `items` is capped, `total` counts every match."""

    total: int
    items: list[ChatSummary]


class SenderOptions(BaseModel):
    """Senders with messages in the date range; `items` is capped, `total` counts every match."""

    total: int
    items: list[SenderInfo]


@router.get("/messages/bounds")
def get_messages_bounds(request: Request, chat_id: int | None = None) -> dict[str, Any]:
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        bounds = fetch_message_bounds(db.msgstore, chat_id=chat_id)
    if bounds is None:
        return {"first_ts": None, "last_ts": None}
    return {"first_ts": bounds[0], "last_ts": bounds[1]}


@router.get("/messages/metadata")
def get_global_messages_metadata(
    request: Request,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    chat_ids: Annotated[list[int] | None, Query()] = None,
    sender_ids: Annotated[list[str] | None, Query()] = None,
) -> dict[str, Any]:
    date_from_ms = datetime_to_ms(date_from) if date_from else None
    date_to_ms = datetime_to_ms(date_to) if date_to else None
    msgstore: Path = request.app.state.msgstore_path
    filters = MetadataFilters(
        chat_ids=frozenset(chat_ids) if chat_ids else None,
        sender_ids=frozenset(sender_ids) if sender_ids else None,
        date_from_ms=date_from_ms,
        date_to_ms=date_to_ms,
        search=search,
    )
    meta = cached.messages_metadata(msgstore_path=msgstore, filters=filters)
    return {"total": meta.total}


@router.get("/messages/chat-options", response_model=ChatOptions)
def get_chat_options(
    request: Request,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
    limit: int = _OPTIONS_LIMIT,
) -> ChatOptions:
    """Chats active in the date range, busiest first, optionally filtered by name."""
    msgstore: Path = request.app.state.msgstore_path
    registry: SenderRegistry = request.app.state.sender_registry
    available = set(_date_range_metadata(msgstore, date_from=date_from, date_to=date_to).available_chat_ids)
    rows = [r for r in cached.chat_rows(msgstore_path=msgstore) if r.chat_id in available]
    summaries = chat_summaries(rows=rows, registry=registry, search=q, sort=ChatSort.MESSAGES, limit=None)
    return ChatOptions(total=len(summaries), items=summaries[:limit])


@router.get("/messages/sender-options", response_model=SenderOptions)
def get_sender_options(
    request: Request,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
    limit: int = _OPTIONS_LIMIT,
) -> SenderOptions:
    """Senders active in the date range, busiest first, optionally filtered by name or phone."""
    msgstore: Path = request.app.state.msgstore_path
    registry: SenderRegistry = request.app.state.sender_registry
    available = set(_date_range_metadata(msgstore, date_from=date_from, date_to=date_to).available_sender_ids)
    rows = [r for r in cached.sender_counts(msgstore_path=msgstore) if r.sender_id in available]
    senders = [_sender_info(row, registry) for row in rows]
    if q:
        needle = q.lower()
        senders = [s for s in senders if needle in s.sender_name.lower() or needle in s.phone]
    return SenderOptions(total=len(senders), items=senders[:limit])


def _date_range_metadata(msgstore: Path, date_from: datetime | None, date_to: datetime | None) -> MessagesMetadata:
    filters = MetadataFilters(
        date_from_ms=datetime_to_ms(date_from) if date_from else None,
        date_to_ms=datetime_to_ms(date_to) if date_to else None,
    )
    return cached.messages_metadata(msgstore_path=msgstore, filters=filters)


def _sender_info(row: RawSenderCount, registry: SenderRegistry) -> SenderInfo:
    if row.from_me:
        return SenderInfo(
            sender_id=row.sender_id, sender_name=registry.me_name, phone="", message_count=row.message_count
        )
    phone = row.effective_phone
    name = registry.resolve_sender(phone=phone, from_me=False).display_name
    return SenderInfo(sender_id=row.sender_id, sender_name=name, phone=phone, message_count=row.message_count)


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
    sort: Literal["asc", "desc"] = "desc",
) -> dict[str, Any]:
    logger.info(
        f"Fetching messages: date_from={date_from}, date_to={date_to}, "
        f"search={search}, chat_ids={chat_ids}, sender_ids={sender_ids}"
    )
    date_from_ms = datetime_to_ms(date_from) if date_from else None
    date_to_ms = datetime_to_ms(date_to) if date_to else None
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry

    with span("db.page"), open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        raw_rows = fetch_messages_page(
            db.msgstore,
            chat_ids=chat_ids,
            date_from_ms=date_from_ms,
            date_to_ms=date_to_ms,
            sender_ids=sender_ids,
            search=search,
            sort_asc=sort == "asc",
            limit=limit,
            offset=offset,
        )
        attachments = load_message_attachments(db.msgstore, rows=raw_rows)

    if not raw_rows:
        return {"messages": []}
    reactions_by_msg, replies_by_msg = _load_engagement_lookups(request, rows=raw_rows)
    with span("serialize"):
        df = build_messages_df(raw_rows, registry)
        messages = _df_to_message_list(
            df,
            include_chat_id=True,
            reactions_by_msg=reactions_by_msg,
            replies_by_msg=replies_by_msg,
            attachments=attachments,
        )
    return {"messages": messages}


@router.get("/senders", response_model=list[SenderInfo])
def get_senders(
    request: Request,
    sender_ids: Annotated[list[str] | None, Query()] = None,
) -> list[SenderInfo]:
    logger.info("Fetching senders with message counts")
    msgstore: Path = request.app.state.msgstore_path
    registry: SenderRegistry = request.app.state.sender_registry

    rows = cached.sender_counts(msgstore_path=msgstore)
    if sender_ids:
        wanted = set(sender_ids)
        rows = [r for r in rows if r.sender_id in wanted]
    return [_sender_info(row, registry) for row in rows]


def _df_to_message_list(
    df: pd.DataFrame,
    *,
    include_chat_id: bool = False,
    reactions_by_msg: dict[int, MessageReactions] | None = None,
    replies_by_msg: dict[int, ReplyPreview] | None = None,
    attachments: MessageAttachments | None = None,
) -> list[dict[str, Any]]:
    messages = []
    for _, row in df.iterrows():
        message_type = int(row["message_type"])
        text = message_display_text(text_data=row.get("text_data"), message_type=message_type)
        phone = str(row.get("sender_phone", "") or "")
        from_me = int(row.get("from_me", 0))
        s_id = "me" if from_me else (phone or str(row["sender_name"]))
        message_id = int(row["message_id"])
        entry: dict[str, Any] = {
            "message_id": message_id,
            # millisecond precision so the UI can show an exact (sub-second) timestamp
            "timestamp": row["timestamp"].strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "chat_name": str(row.get("chat_name", "")),
            "sender_name": str(row["sender_name"]),
            "sender_id": s_id,
            "text": str(text) if text else None,
            "message_type": message_type,
        }
        if include_chat_id:
            entry["chat_id"] = int(row["chat_row_id"])
        if reactions_by_msg:
            reactions = reactions_by_msg.get(message_id)
            entry["reactions"] = reactions.model_dump() if reactions else None
        if replies_by_msg:
            reply = replies_by_msg.get(message_id)
            entry["reply_to"] = reply.model_dump() if reply else None
        if attachments:
            entry.update(attachments.fields_for(message_id))
        messages.append(entry)
    return messages


def _load_engagement_lookups(
    request: Request, rows: list[RawMessageRow]
) -> tuple[dict[int, MessageReactions], dict[int, ReplyPreview]]:
    """Load reaction + reply lookups, keyed by message id, for just the given page of messages."""
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry
    message_ids = {r.message_id for r in rows}
    with span("db.engagement"), open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        loader = DataLoader(db, registry=registry)
        reactions_df = loader.load_reactions(message_ids=message_ids)
        replies_df = loader.load_replies(message_ids=message_ids)
    return reactions_by_message(reactions_df), replies_by_message(replies_df)
