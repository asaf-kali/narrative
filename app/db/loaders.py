import datetime
import logging
import sqlite3
from collections.abc import Generator
from pathlib import Path

import pandas as pd
from db.connection import DBConnection
from db.queries.calls import fetch_calls
from db.queries.chats import fetch_chats
from db.queries.messages import (
    fetch_all_messages,
    fetch_index_rows_paged,
    fetch_messages_for_chat,
)
from db.queries.reactions import fetch_reactions
from db.row_types import RawChatRow, RawMessageRow
from models.chat import ChatSummary, ChatType
from models.config import AnalysisConfig
from models.message import MessageType
from models.sender import BROADCAST_SERVER, GROUP_SERVER, SenderRegistry
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class IndexMessage(BaseModel):
    """Message row prepared for the streaming indexer pipeline."""

    message_id: int
    chat_row_id: int
    timestamp: int  # ms UTC, no tz conversion
    message_type: int
    text_data: str | None
    chat_name: str
    sender_name: str


# Messages DataFrame column names
COL_MESSAGE_ID = "message_id"
COL_CHAT_ROW_ID = "chat_row_id"
COL_FROM_ME = "from_me"
COL_TIMESTAMP = "timestamp"
COL_RECEIVED_TIMESTAMP = "received_timestamp"
COL_MESSAGE_TYPE = "message_type"
COL_TEXT_DATA = "text_data"
COL_STARRED = "starred"
COL_SENDER_PHONE = "sender_phone"
COL_SENDER_SERVER = "sender_server"
COL_CHAT_SUBJECT = "chat_subject"
COL_CHAT_PHONE = "chat_phone"
COL_CHAT_SERVER = "chat_server"
COL_CHAT_JID_TYPE = "chat_jid_type"
COL_SENDER_NAME = "sender_name"
COL_DATE = "date"
COL_YEAR = "year"
COL_MONTH = "month"
COL_DAY_OF_WEEK = "day_of_week"
COL_HOUR = "hour"
COL_CHAT_NAME = "chat_name"
COL_IS_GROUP = "is_group"

# Use the system local timezone for timestamp display
_LOCAL_TZ: datetime.tzinfo = datetime.datetime.now().astimezone().tzinfo or datetime.UTC


class DataLoader:
    def __init__(self, db: DBConnection, registry: SenderRegistry | None = None) -> None:
        self._db = db
        self._registry = registry or SenderRegistry(contacts={})

    def load_chats(self, search: str | None = None, limit: int = 100) -> list[ChatSummary]:
        summaries = [_row_to_chat_summary(row, self._registry) for row in fetch_chats(self._db.msgstore)]
        if search:
            needle = search.lower()
            return [s for s in summaries if needle in s.display_name.lower()]
        return summaries[:limit]

    def load_messages(self, config: AnalysisConfig) -> pd.DataFrame:
        rows = self._fetch_raw_messages(config)
        if not rows:
            return _empty_messages_df()
        return build_messages_df(rows, self._registry)

    def _fetch_raw_messages(self, config: AnalysisConfig) -> list[RawMessageRow]:
        date_from_ms = datetime_to_ms(config.date_from) if config.date_from is not None else None
        date_to_ms = datetime_to_ms(config.date_to) if config.date_to is not None else None
        kwargs = {
            "date_from_ms": date_from_ms,
            "date_to_ms": date_to_ms,
            "exclude_system": config.exclude_system,
        }
        if config.chat_id is not None:
            return list(fetch_messages_for_chat(self._db.msgstore, chat_id=config.chat_id, **kwargs))
        return list(fetch_all_messages(self._db.msgstore, **kwargs))

    def load_reactions(self) -> pd.DataFrame:
        rows = list(fetch_reactions(self._db.msgstore))
        if not rows:
            return pd.DataFrame(columns=["reaction_message_id", "parent_message_id", "emoji", "sender_phone"])
        return pd.DataFrame([r.model_dump() for r in rows])

    def iter_chat_messages(
        self,
        chat_id: int,
        chunk_size: int,
        after_id: int = 0,
    ) -> Generator[IndexMessage]:
        """Flat message stream for one chat. Paginates DB internally; caller sees plain iterator."""
        contacts = self._registry.as_dict()
        system_type = int(MessageType.SYSTEM)
        cursor = after_id
        while True:
            rows = fetch_index_rows_paged(self._db.msgstore, chat_id, cursor, chunk_size)
            if not rows:
                return
            for r in rows:
                if r["message_type"] != system_type:
                    yield _raw_row_to_index_message(row=r, registry=self._registry, contacts=contacts)
            # Advance cursor on full page's last _id (even if those rows were filtered).
            cursor = rows[-1]["message_id"]
            if len(rows) < chunk_size:
                return

    def load_boundary_rows(
        self,
        chat_id: int,
        min_id: int,
        max_id: int,
    ) -> list[IndexMessage]:
        """Load a previous session's messages for incremental boundary reconstruction."""
        contacts = self._registry.as_dict()
        rows = fetch_index_rows_paged(self._db.msgstore, chat_id, after_id=min_id - 1, limit=max_id - min_id + 200)
        return [
            _raw_row_to_index_message(row=r, registry=self._registry, contacts=contacts)
            for r in rows
            if r["message_id"] <= max_id
        ]

    def load_calls(self) -> pd.DataFrame:
        rows = list(fetch_calls(self._db.msgstore))
        if not rows:
            return pd.DataFrame(
                columns=["call_id", "timestamp", "call_result", "duration", "is_video", "from_me", "caller_phone"]
            )
        df = pd.DataFrame([r.model_dump() for r in rows])
        df[COL_TIMESTAMP] = pd.to_datetime(df[COL_TIMESTAMP], unit="ms", utc=True).dt.tz_convert(_LOCAL_TZ)
        return df


# ── private helpers ──────────────────────────────────────────────────────────


def _raw_row_to_index_message(row: sqlite3.Row, registry: SenderRegistry, contacts: dict[str, str]) -> IndexMessage:
    """Build IndexMessage directly from a sqlite3.Row — no intermediate Pydantic model."""
    server: str = row["chat_server"] or ""
    phone: str = row["chat_phone"] or ""
    subject: str = row["chat_subject"] or ""
    is_grp = server.endswith(GROUP_SERVER)
    is_broadcast = server == BROADCAST_SERVER

    if subject:
        chat_name: str = subject
    elif is_grp:
        chat_name = f"Group ({phone})"
    elif is_broadcast:
        chat_name = "Broadcast"
    else:
        chat_name = contacts.get(phone) or phone or "Unknown"

    sender_phone: str = row["sender_phone"] or ""
    effective_phone = sender_phone if (sender_phone or is_grp) else phone
    if row["from_me"]:
        sender_name: str = registry.me_name
    else:
        sender_name = contacts.get(effective_phone) or effective_phone or "Unknown"

    return IndexMessage.model_construct(
        message_id=row["message_id"],
        chat_row_id=row["chat_row_id"],
        timestamp=row["timestamp"],
        message_type=row["message_type"],
        text_data=row["text_data"],
        chat_name=chat_name,
        sender_name=sender_name,
    )


def _to_index_message(row: RawMessageRow, registry: SenderRegistry, contacts: dict[str, str]) -> IndexMessage:
    server = row.chat_server or ""
    phone = row.chat_phone or ""
    subject = row.chat_subject or ""
    is_grp = server.endswith(GROUP_SERVER)
    is_broadcast = server == BROADCAST_SERVER

    if subject:
        chat_name: str = subject
    elif is_grp:
        chat_name = f"Group ({phone})"
    elif is_broadcast:
        chat_name = "Broadcast"
    else:
        chat_name = contacts.get(phone) or phone or "Unknown"

    sender_phone = row.sender_phone or ""
    effective_phone = sender_phone if (sender_phone or is_grp) else phone
    if row.from_me:
        sender_name: str = registry.me_name
    else:
        sender_name = contacts.get(effective_phone) or effective_phone or "Unknown"

    return IndexMessage(
        message_id=row.message_id,
        chat_row_id=row.chat_row_id,
        timestamp=row.timestamp,
        message_type=row.message_type,
        text_data=row.text_data,
        chat_name=chat_name,
        sender_name=sender_name,
    )


def _row_to_chat_summary(row: RawChatRow, registry: SenderRegistry) -> ChatSummary:
    server = row.chat_server or ""
    phone = row.chat_phone or ""

    if server == GROUP_SERVER:
        chat_type = ChatType.GROUP
        display_name = row.chat_subject or f"Group ({phone})"
    elif server == BROADCAST_SERVER:
        chat_type = ChatType.BROADCAST
        display_name = row.chat_subject or "Broadcast"
    else:
        chat_type = ChatType.DIRECT
        display_name = registry.resolve_chat_name(row.chat_subject, server, phone)

    first_ts = row.first_timestamp
    last_ts = row.last_timestamp

    is_lid = server == "lid"
    phone_val = phone if chat_type == ChatType.DIRECT else None

    return ChatSummary(
        chat_id=row.chat_id,
        display_name=display_name,
        chat_type=chat_type,
        message_count=row.message_count or 0,
        participant_count=None,
        date_first=pd.to_datetime(first_ts, unit="ms", utc=True).to_pydatetime() if first_ts else None,
        date_last=pd.to_datetime(last_ts, unit="ms", utc=True).to_pydatetime() if last_ts else None,
        phone=phone_val,
        is_lid=is_lid,
    )


def build_messages_df(rows: list[RawMessageRow], registry: SenderRegistry) -> pd.DataFrame:
    df = pd.DataFrame([r.model_dump() for r in rows])

    # Normalise timestamps
    df[COL_TIMESTAMP] = pd.to_datetime(df[COL_TIMESTAMP], unit="ms", utc=True).dt.tz_convert(_LOCAL_TZ)
    # Clamp received_timestamp: 0/negative = missing; >_MAX_MS_TS = sentinel/corrupt (would overflow int64 ns)
    _MAX_MS_TS = 9_000_000_000_000  # ~year 2255, safely below int64 nanosecond overflow
    received_ms = df[COL_RECEIVED_TIMESTAMP].where(
        (df[COL_RECEIVED_TIMESTAMP] > 0) & (df[COL_RECEIVED_TIMESTAMP] < _MAX_MS_TS)
    )
    df[COL_RECEIVED_TIMESTAMP] = pd.to_datetime(received_ms, unit="ms", utc=True, errors="coerce").dt.tz_convert(
        _LOCAL_TZ
    )

    # Resolve sender display name — vectorized for performance
    contacts = registry.as_dict()
    is_grp = df[COL_CHAT_SERVER].str.endswith(GROUP_SERVER, na=False)
    from_me_mask = df[COL_FROM_ME] == 1
    phone_col = df[COL_SENDER_PHONE].fillna("").astype(str)
    chat_phone_col = df[COL_CHAT_PHONE].fillna("").astype(str)

    # For 1-on-1 chats, sender_phone is "" in the DB — fall back to chat_phone
    effective_phone = phone_col.where((phone_col != "") | is_grp, chat_phone_col)
    resolved = effective_phone.map(contacts).fillna(effective_phone).replace("", "Unknown")
    df[COL_SENDER_NAME] = resolved.where(~from_me_mask, registry.me_name)

    # Derive time components used by analysis
    df[COL_DATE] = df[COL_TIMESTAMP].dt.date
    df[COL_YEAR] = df[COL_TIMESTAMP].dt.year
    df[COL_MONTH] = df[COL_TIMESTAMP].dt.strftime("%Y-%m")
    df[COL_DAY_OF_WEEK] = df[COL_TIMESTAMP].dt.day_name()
    df[COL_HOUR] = df[COL_TIMESTAMP].dt.hour

    # Chat display name — vectorized
    chat_subject = df[COL_CHAT_SUBJECT].fillna("")
    is_broadcast = df[COL_CHAT_SERVER] == BROADCAST_SERVER

    group_fallback = "Group (" + chat_phone_col + ")"
    chat_name = chat_phone_col.map(contacts).fillna(chat_phone_col)  # direct default
    chat_name = chat_name.where(~is_grp, chat_subject.where(chat_subject != "", group_fallback))
    chat_name = chat_name.where(~is_broadcast, chat_subject.where(chat_subject != "", "Broadcast"))
    df[COL_CHAT_NAME] = chat_name.where(chat_subject == "", chat_subject)  # subject beats everything
    df[COL_IS_GROUP] = is_grp

    return df


def _empty_messages_df() -> pd.DataFrame:
    columns = [
        COL_MESSAGE_ID,
        COL_CHAT_ROW_ID,
        COL_FROM_ME,
        COL_TIMESTAMP,
        COL_RECEIVED_TIMESTAMP,
        COL_MESSAGE_TYPE,
        COL_TEXT_DATA,
        COL_STARRED,
        COL_SENDER_PHONE,
        COL_SENDER_SERVER,
        COL_CHAT_SUBJECT,
        COL_CHAT_PHONE,
        COL_CHAT_SERVER,
        COL_CHAT_JID_TYPE,
        COL_SENDER_NAME,
        COL_DATE,
        COL_YEAR,
        COL_MONTH,
        COL_DAY_OF_WEEK,
        COL_HOUR,
        COL_CHAT_NAME,
        COL_IS_GROUP,
    ]
    return pd.DataFrame(columns=columns)


def datetime_to_ms(dt: datetime.datetime) -> int:
    """Convert datetime to UTC milliseconds (DB timestamp format). Treats tz-naive as local."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_LOCAL_TZ)
    return int(dt.timestamp() * 1000)


def open_connection(msgstore_path: Path, wadb_path: Path | None = None) -> DBConnection:
    return DBConnection(msgstore_path=msgstore_path, wadb_path=wadb_path)
