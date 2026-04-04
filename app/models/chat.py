import logging
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChatType(StrEnum):
    DIRECT = "direct"
    GROUP = "group"
    BROADCAST = "broadcast"


class ChatSummary(BaseModel):
    chat_id: int
    display_name: str
    chat_type: ChatType
    message_count: int
    participant_count: int | None
    date_first: datetime | None
    date_last: datetime | None
