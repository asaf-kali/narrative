"""Pydantic models mirroring raw SQL query output columns.

Each class maps 1:1 to the SELECT columns of its corresponding query.
Use `model_validate(dict(row))` to construct from sqlite3.Row objects.
`extra='ignore'` tolerates DB schema variations across WhatsApp versions.
"""

from pydantic import BaseModel, ConfigDict


class _RowBase(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RawMessageRow(_RowBase):
    message_id: int
    chat_row_id: int
    from_me: int
    timestamp: int
    received_timestamp: int
    message_type: int
    text_data: str | None
    starred: int
    sender_phone: str
    sender_server: str
    chat_subject: str | None
    chat_phone: str
    chat_server: str
    chat_jid_type: str | None


class RawChatRow(_RowBase):
    chat_id: int
    chat_subject: str | None
    created_timestamp: int | None
    chat_phone: str
    chat_server: str
    chat_jid_type: str | None
    message_count: int
    first_timestamp: int | None
    last_timestamp: int | None


class RawDayMessageRow(_RowBase):
    timestamp: int
    time: str
    message_type: int
    from_me: int
    text_data: str | None
    sender_phone: str
    sender_server: str
    chat_subject: str | None
    chat_phone: str
    chat_server: str


class RawSearchRow(_RowBase):
    chat_id: int
    chat_subject: str | None
    chat_phone: str
    chat_server: str
    timestamp: str
    text_data: str
    from_me: int
    sender_phone: str
    sender_server: str


class RawReactionRow(_RowBase):
    reaction_message_id: int
    parent_message_id: int
    emoji: str
    sender_phone: str
    timestamp: int


class RawCallRow(_RowBase):
    call_id: int
    timestamp: int
    call_result: int
    duration: int
    is_video: int
    from_me: int
    caller_phone: str
