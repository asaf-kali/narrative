import logging
from enum import IntEnum

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MessageType(IntEnum):
    TEXT = 0
    IMAGE = 1
    AUDIO = 2
    VIDEO = 3
    CONTACT = 4
    LOCATION = 5
    SYSTEM = 7
    DOCUMENT = 9
    STICKER = 13
    GIF = 15
    LIVE_LOCATION = 20


MEDIA_TYPES: frozenset[MessageType] = frozenset(
    {MessageType.IMAGE, MessageType.VIDEO, MessageType.DOCUMENT, MessageType.STICKER, MessageType.GIF}
)

AUDIO_TYPES: frozenset[MessageType] = frozenset({MessageType.AUDIO})


class MessageStats(BaseModel):
    total: int
    text: int
    media: int
    audio: int
    system: int
    revoked: int
    links: int
