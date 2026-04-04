import datetime
import logging
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
from db.connection import DBConnection
from db.queries.calls import fetch_calls
from db.queries.chats import fetch_chats
from db.queries.messages import fetch_all_messages, fetch_messages_for_chat
from db.queries.reactions import fetch_reactions
from models.chat import ChatSummary, ChatType
from models.config import AnalysisConfig

logger = logging.getLogger(__name__)

# Use the system local timezone for timestamp display
_LOCAL_TZ: datetime.tzinfo = datetime.datetime.now().astimezone().tzinfo or datetime.UTC

# JID server suffixes used to determine chat type
_GROUP_SERVER = "g.us"
_BROADCAST_SERVER = "broadcast"

# WhatsApp JID format for wa_contacts: "phonenumber@s.whatsapp.net"
_JID_SUFFIX = "@s.whatsapp.net"


class DataLoader:
    def __init__(self, db: DBConnection) -> None:
        self._db = db
        self._contact_names: dict[str, str] = {}

    def load_contact_names(self) -> dict[str, str]:
        if self._contact_names:
            return self._contact_names
        if self._db.wadb is None:
            return {}
        try:
            rows = self._db.wadb.execute(
                "SELECT jid, display_name FROM wa_contacts WHERE display_name IS NOT NULL AND display_name != ''"
            ).fetchall()
            self._contact_names = {row["jid"].replace(_JID_SUFFIX, ""): row["display_name"] for row in rows}
        except sqlite3.OperationalError:
            logger.debug("wa_contacts table not found — no contact name resolution.")
        return self._contact_names

    def load_chats(self) -> list[ChatSummary]:
        rows = fetch_chats(self._db.msgstore)
        contact_names = self.load_contact_names()
        return [_row_to_chat_summary(row, contact_names) for row in rows if row["chat_id"] is not None]

    def load_messages(self, config: AnalysisConfig) -> pd.DataFrame:
        rows = (
            fetch_messages_for_chat(self._db.msgstore, config.chat_id)
            if config.chat_id is not None
            else fetch_all_messages(self._db.msgstore)
        )
        if not rows:
            return _empty_messages_df()

        contact_names = self.load_contact_names()
        df = _rows_to_messages_df(rows, contact_names)
        return _apply_config_filters(df, config)

    def load_reactions(self) -> pd.DataFrame:
        rows = fetch_reactions(self._db.msgstore)
        if not rows:
            return pd.DataFrame(columns=["reaction_message_id", "parent_message_id", "emoji", "sender_phone"])
        return pd.DataFrame([dict(row) for row in rows])

    def load_calls(self) -> pd.DataFrame:
        rows = fetch_calls(self._db.msgstore)
        if not rows:
            return pd.DataFrame(
                columns=["call_id", "timestamp", "call_result", "duration", "is_video", "from_me", "caller_phone"]
            )
        df = pd.DataFrame([dict(row) for row in rows])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(_LOCAL_TZ)
        return df


# ── private helpers ──────────────────────────────────────────────────────────


def _row_to_chat_summary(row: sqlite3.Row, contact_names: dict[str, str]) -> ChatSummary:
    server = row["chat_server"] or ""
    phone = row["chat_phone"] or ""

    if server == _GROUP_SERVER:
        chat_type = ChatType.GROUP
        display_name = row["chat_subject"] or f"Group ({phone})"
    elif server == _BROADCAST_SERVER:
        chat_type = ChatType.BROADCAST
        display_name = row["chat_subject"] or "Broadcast"
    else:
        chat_type = ChatType.DIRECT
        display_name = contact_names.get(phone) or row["chat_subject"] or phone

    first_ts = row["first_timestamp"]
    last_ts = row["last_timestamp"]

    return ChatSummary(
        chat_id=row["chat_id"],
        display_name=display_name,
        chat_type=chat_type,
        message_count=row["message_count"] or 0,
        participant_count=None,
        date_first=pd.to_datetime(first_ts, unit="ms", utc=True).to_pydatetime() if first_ts else None,
        date_last=pd.to_datetime(last_ts, unit="ms", utc=True).to_pydatetime() if last_ts else None,
    )


def _rows_to_messages_df(rows: list[sqlite3.Row], contact_names: dict[str, str]) -> pd.DataFrame:
    records = [dict(row) for row in rows]
    df = pd.DataFrame(records)

    # Normalise timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(_LOCAL_TZ)
    received_ms = df["received_timestamp"].where(df["received_timestamp"] > 0)
    df["received_timestamp"] = pd.to_datetime(received_ms, unit="ms", utc=True, errors="coerce").dt.tz_convert(
        _LOCAL_TZ
    )

    # Resolve sender display name
    df["sender_name"] = df.apply(lambda r: _resolve_sender(r, contact_names), axis=1)

    # Derive time components used by analysis
    df["date"] = df["timestamp"].dt.date
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)
    df["day_of_week"] = df["timestamp"].dt.day_name()
    df["hour"] = df["timestamp"].dt.hour

    # Chat display name
    df["chat_name"] = df.apply(
        lambda r: _resolve_chat_name(r, contact_names),
        axis=1,
    )
    df["is_group"] = df["chat_server"].str.endswith(_GROUP_SERVER, na=False)

    return df


def _resolve_sender(row: pd.Series[Any], contact_names: dict[str, str]) -> str:
    phone = str(row.get("sender_phone") or "")
    if phone and phone in contact_names:
        return contact_names[phone]
    if row.get("from_me") == 1:
        return "Me"
    # Fallback: use chat phone for 1-on-1 chats
    chat_server = str(row.get("chat_server") or "")
    if chat_server != _GROUP_SERVER:
        chat_phone = str(row.get("chat_phone") or "")
        return contact_names.get(chat_phone) or chat_phone or "Unknown"
    return phone or "Unknown"


def _resolve_chat_name(row: pd.Series[Any], contact_names: dict[str, str]) -> str:
    server = str(row.get("chat_server") or "")
    phone = str(row.get("chat_phone") or "")
    subject = row.get("chat_subject")
    if subject:
        return str(subject)
    if server != _GROUP_SERVER:
        return contact_names.get(phone) or phone or "Unknown"
    return f"Group ({phone})"


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
        "quoted_row_id",
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
