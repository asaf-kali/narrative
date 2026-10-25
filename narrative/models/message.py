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
    GIF = 13
    MULTI_CONTACT = 14
    REVOKED = 15  # deleted for everyone; row details live in message_revoked
    LIVE_LOCATION = 16
    STICKER = 20


MEDIA_TYPES: frozenset[MessageType] = frozenset(
    {MessageType.IMAGE, MessageType.VIDEO, MessageType.DOCUMENT, MessageType.STICKER, MessageType.GIF}
)

AUDIO_TYPES: frozenset[MessageType] = frozenset({MessageType.AUDIO})

CONTACT_TYPES: frozenset[MessageType] = frozenset({MessageType.CONTACT, MessageType.MULTI_CONTACT})

# Bracketed placeholders shown in place of (or before) a message's text for non-text types.
PLACEHOLDER_LABELS: dict[int, str] = {
    MessageType.IMAGE: "[Image]",
    MessageType.AUDIO: "[Audio]",
    MessageType.VIDEO: "[Video]",
    MessageType.CONTACT: "[Contact]",
    MessageType.MULTI_CONTACT: "[Contacts]",
    MessageType.LOCATION: "[Location]",
    MessageType.DOCUMENT: "[Document]",
    MessageType.STICKER: "[Sticker]",
    MessageType.GIF: "[GIF]",
    MessageType.REVOKED: "[Deleted]",
    MessageType.LIVE_LOCATION: "[Live location]",
}


class ContactCard(BaseModel):
    """A contact (vCard) shared in a chat."""

    name: str
    phones: list[str]


class MessageStats(BaseModel):
    total: int
    text: int
    media: int
    audio: int
    system: int
    revoked: int
    links: int


def message_display_text(*, text_data: str | None, message_type: int) -> str | None:
    """Text to show for a message: its own text, a type placeholder, or both for contact cards.

    Contact messages store the shared contact's display name in `text_data`, so the
    placeholder is prefixed to mark it as a card rather than something the sender typed.
    """
    label = PLACEHOLDER_LABELS.get(message_type)
    if label is None or (text_data and message_type not in CONTACT_TYPES):
        return text_data
    if not text_data:
        return label
    return f"{label} {text_data}"
