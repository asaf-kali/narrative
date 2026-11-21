import logging
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChatType(StrEnum):
    DIRECT = "direct"
    GROUP = "group"
    BROADCAST = "broadcast"


class ChatSort(StrEnum):
    LAST_MESSAGE = "last"  # most recent message first
    MESSAGES = "messages"  # most messages first
    MINE = "mine"  # most messages sent by me first


class ChatSummary(BaseModel):
    chat_id: int
    display_name: str
    chat_type: ChatType
    message_count: int
    my_message_count: int = 0
    participant_count: int | None
    date_first: datetime | None
    date_last: datetime | None
    phone: str | None  # phone digits for direct chats; None for groups/broadcasts
    is_lid: bool  # True when `phone` is a WhatsApp LID, not a real phone number
