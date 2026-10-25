import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import pandas as pd
from fastapi import APIRouter, Query, Request

from narrative.analysis.reactions import MessageReactions, reactions_by_message
from narrative.analysis.replies import ReplyPreview, replies_by_message
from narrative.db.loaders import DataLoader, build_messages_df, datetime_to_ms, open_connection
from narrative.db.queries.messages import (
    fetch_message_bounds,
    fetch_messages_metadata,
    fetch_messages_page,
    fetch_sender_counts,
)
from narrative.db.row_types import RawMessageRow
from narrative.db.vcards import ContactCardsByMessage, load_contact_cards
from narrative.models.message import CONTACT_TYPES, message_display_text
from narrative.models.sender import SenderRegistry

logger = logging.getLogger(__name__)
router = APIRouter()


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
    wadb: Path | None = request.app.state.wadb_path

    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        meta = fetch_messages_metadata(
            db.msgstore,
            chat_ids=chat_ids,
            date_from_ms=date_from_ms,
            date_to_ms=date_to_ms,
            sender_ids=sender_ids,
            search=search,
        )

    return {
        "total": meta.total,
        "available_chat_ids": meta.available_chat_ids,
        "available_sender_ids": meta.available_sender_ids,
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

    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
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
        contact_cards_by_msg = _load_contact_cards(db.msgstore, raw_rows=raw_rows)

    if not raw_rows:
        return {"messages": []}
    reactions_by_msg, replies_by_msg = _load_engagement_lookups(request, chat_id=None)
    df = build_messages_df(raw_rows, registry)
    messages = _df_to_message_list(
        df,
        include_chat_id=True,
        reactions_by_msg=reactions_by_msg,
        replies_by_msg=replies_by_msg,
        contact_cards_by_msg=contact_cards_by_msg,
    )
    return {"messages": messages}


@router.get("/senders")
def get_senders(
    request: Request,
    sender_ids: Annotated[list[str] | None, Query()] = None,
) -> list[dict[str, Any]]:
    logger.info("Fetching senders with message counts")
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry
    contacts = registry.as_dict()

    sender_id_set = set(sender_ids) if sender_ids else None
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        rows = fetch_sender_counts(db.msgstore, sender_ids=sender_id_set)

    result = []
    for row in rows:
        if row.from_me:
            sender_name = registry.me_name
            phone = ""
        else:
            phone = row.effective_phone
            sender_name = contacts.get(phone) or phone or "Unknown"
        result.append(
            {
                "sender_id": row.sender_id,
                "sender_name": sender_name,
                "phone": phone,
                "message_count": row.message_count,
            }
        )
    return result


def _df_to_message_list(
    df: pd.DataFrame,
    *,
    include_chat_id: bool = False,
    reactions_by_msg: dict[int, MessageReactions] | None = None,
    replies_by_msg: dict[int, ReplyPreview] | None = None,
    contact_cards_by_msg: ContactCardsByMessage | None = None,
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
        if contact_cards_by_msg:
            cards = contact_cards_by_msg.get(message_id)
            entry["contacts"] = [c.model_dump() for c in cards] if cards else None
        messages.append(entry)
    return messages


def _load_engagement_lookups(
    request: Request, chat_id: int | None
) -> tuple[dict[int, MessageReactions], dict[int, ReplyPreview]]:
    """Load reaction + reply lookups keyed by message id (chat-scoped or global)."""
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        loader = DataLoader(db, registry=registry)
        reactions_df = loader.load_reactions(chat_id=chat_id)
        replies_df = loader.load_replies(chat_id=chat_id)
    return reactions_by_message(reactions_df), replies_by_message(replies_df)


def _load_contact_cards(conn: sqlite3.Connection, raw_rows: list[RawMessageRow]) -> ContactCardsByMessage:
    """Load parsed vCards for the contact messages in this page, keyed by message id."""
    contact_ids = {r.message_id for r in raw_rows if r.message_type in CONTACT_TYPES}
    return load_contact_cards(conn, message_ids=contact_ids)
