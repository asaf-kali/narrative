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
from models.sender import BROADCAST_SERVER, GROUP_SERVER, SenderRegistry

logger = logging.getLogger(__name__)

# Use the system local timezone for timestamp display
_LOCAL_TZ: datetime.tzinfo = datetime.datetime.now().astimezone().tzinfo or datetime.UTC


class DataLoader:
    def __init__(self, db: DBConnection, registry: SenderRegistry | None = None) -> None:
        self._db = db
        self._registry = registry or SenderRegistry(contacts={})

    def load_chats(self) -> list[ChatSummary]:
        return [
            _row_to_chat_summary(row, self._registry)
            for row in fetch_chats(self._db.msgstore)
            if row.chat_id is not None
        ]

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
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(_LOCAL_TZ)
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
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(_LOCAL_TZ)
    received_ms = df["received_timestamp"].where(df["received_timestamp"] > 0)
    df["received_timestamp"] = pd.to_datetime(received_ms, unit="ms", utc=True, errors="coerce").dt.tz_convert(
        _LOCAL_TZ
    )

    # Resolve sender display name — vectorized for performance
    contacts = registry.as_dict()
    is_grp = df["chat_server"].str.endswith(GROUP_SERVER, na=False)
    from_me_mask = df["from_me"] == 1
    phone_col = df["sender_phone"].fillna("").astype(str)
    chat_phone_col = df["chat_phone"].fillna("").astype(str)

    # For 1-on-1 chats, sender_phone is "" in the DB — fall back to chat_phone
    effective_phone = phone_col.where((phone_col != "") | is_grp, chat_phone_col)
    resolved = effective_phone.map(contacts).fillna(effective_phone).replace("", "Unknown")
    df["sender_name"] = resolved.where(~from_me_mask, registry.me_name)

    # Derive time components used by analysis
    df["date"] = df["timestamp"].dt.date
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)
    df["day_of_week"] = df["timestamp"].dt.day_name()
    df["hour"] = df["timestamp"].dt.hour

    # Chat display name — vectorized
    chat_subject = df["chat_subject"].fillna("")
    is_broadcast = df["chat_server"] == BROADCAST_SERVER

    group_fallback = "Group (" + chat_phone_col + ")"
    chat_name = chat_phone_col.map(contacts).fillna(chat_phone_col)  # direct default
    chat_name = chat_name.where(~is_grp, chat_subject.where(chat_subject != "", group_fallback))
    chat_name = chat_name.where(~is_broadcast, chat_subject.where(chat_subject != "", "Broadcast"))
    df["chat_name"] = chat_name.where(chat_subject == "", chat_subject)  # subject beats everything
    df["is_group"] = is_grp

    return df


def _apply_config_filters(df: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
    if config.exclude_system:
        from models.message import MessageType  # noqa: PLC0415

        df = df[df["message_type"] != MessageType.SYSTEM]

    if config.date_from is not None:
        df = df[df["timestamp"] >= _to_local_ts(config.date_from)]

    if config.date_to is not None:
        df = df[df["timestamp"] <= _to_local_ts(config.date_to)]

    return df


def _empty_messages_df() -> pd.DataFrame:
    columns = [
        "message_id",
        "chat_row_id",
        "from_me",
        "timestamp",
        "received_timestamp",
        "message_type",
        "text_data",
        "starred",
        "sender_phone",
        "sender_server",
        "chat_subject",
        "chat_phone",
        "chat_server",
        "chat_jid_type",
        "sender_name",
        "date",
        "year",
        "month",
        "day_of_week",
        "hour",
        "chat_name",
        "is_group",
    ]
    return pd.DataFrame(columns=columns)


def _to_local_ts(dt: datetime.datetime) -> pd.Timestamp:
    ts = pd.Timestamp(dt)
    if ts.tzinfo is None:
        return ts.tz_localize(_LOCAL_TZ)
    return ts.tz_convert(_LOCAL_TZ)


def open_connection(msgstore_path: Path, wadb_path: Path | None = None) -> DBConnection:
    return DBConnection(msgstore_path=msgstore_path, wadb_path=wadb_path)
