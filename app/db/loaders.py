import datetime
import logging
from pathlib import Path

import pandas as pd
from db.connection import DBConnection
from db.queries.calls import fetch_calls
from db.queries.chats import fetch_chats
from db.queries.messages import fetch_all_messages, fetch_messages_for_chat
from db.queries.reactions import fetch_reactions
from db.row_types import RawChatRow, RawMessageRow
from models.chat import ChatSummary, ChatType
from models.config import AnalysisConfig
from models.message import MessageType
from models.sender import BROADCAST_SERVER, GROUP_SERVER, SenderRegistry

logger = logging.getLogger(__name__)

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
        summaries = [
            _row_to_chat_summary(row, self._registry)
            for row in fetch_chats(self._db.msgstore)
            if row.chat_id is not None
        ]
        if search:
            needle = search.lower()
            return [s for s in summaries if needle in s.display_name.lower()]
        return summaries[:limit]

    def load_messages(self, config: AnalysisConfig) -> pd.DataFrame:
        rows = list(
            fetch_messages_for_chat(self._db.msgstore, config.chat_id)
            if config.chat_id is not None
            else fetch_all_messages(self._db.msgstore)
        )
        if not rows:
            return _empty_messages_df()

        df = _rows_to_messages_df(rows, self._registry)
        return _apply_config_filters(df, config)

    def load_reactions(self) -> pd.DataFrame:
        rows = list(fetch_reactions(self._db.msgstore))
        if not rows:
            return pd.DataFrame(columns=["reaction_message_id", "parent_message_id", "emoji", "sender_phone"])
        return pd.DataFrame([r.model_dump() for r in rows])

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


def _rows_to_messages_df(rows: list[RawMessageRow], registry: SenderRegistry) -> pd.DataFrame:
    df = pd.DataFrame([r.model_dump() for r in rows])

    # Normalise timestamps
    df[COL_TIMESTAMP] = pd.to_datetime(df[COL_TIMESTAMP], unit="ms", utc=True).dt.tz_convert(_LOCAL_TZ)
    received_ms = df[COL_RECEIVED_TIMESTAMP].where(df[COL_RECEIVED_TIMESTAMP] > 0)
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
    df[COL_MONTH] = df[COL_TIMESTAMP].dt.to_period("M").astype(str)
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


def _apply_config_filters(df: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
    if config.exclude_system:
        df = df[df[COL_MESSAGE_TYPE] != MessageType.SYSTEM]

    if config.date_from is not None:
        df = df[df[COL_TIMESTAMP] >= _to_local_ts(config.date_from)]

    if config.date_to is not None:
        df = df[df[COL_TIMESTAMP] <= _to_local_ts(config.date_to)]

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


def _to_local_ts(dt: datetime.datetime) -> pd.Timestamp:
    ts = pd.Timestamp(dt)
    if ts.tzinfo is None:
        return ts.tz_localize(_LOCAL_TZ)
    return ts.tz_convert(_LOCAL_TZ)


def open_connection(msgstore_path: Path, wadb_path: Path | None = None) -> DBConnection:
    return DBConnection(msgstore_path=msgstore_path, wadb_path=wadb_path)
