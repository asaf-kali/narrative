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
    GROUP_INVITE = 24
    TEMPLATE_IMAGE = 25  # business template messages (message_template)
    TEMPLATE_DOCUMENT = 26
    TEMPLATE_TEXT = 27
    TEMPLATE_VIDEO = 28
    VIEW_ONCE_IMAGE = 42
    VIEW_ONCE_VIDEO = 43
    ADMIN_REVOKED = 64  # deleted by a group admin; also in message_revoked
    POLL = 66
    VIEW_ONCE_AUDIO = 82
    CALL = 90  # call event inside a chat (message_call_log)
    EVENT = 92
    ALBUM = 99  # header row grouping the media messages of an album


MEDIA_TYPES: frozenset[MessageType] = frozenset(
    {
        MessageType.IMAGE,
        MessageType.VIDEO,
        MessageType.DOCUMENT,
        MessageType.STICKER,
        MessageType.GIF,
        MessageType.VIEW_ONCE_IMAGE,
        MessageType.VIEW_ONCE_VIDEO,
    }
)

AUDIO_TYPES: frozenset[MessageType] = frozenset({MessageType.AUDIO, MessageType.VIEW_ONCE_AUDIO})

CONTACT_TYPES: frozenset[MessageType] = frozenset({MessageType.CONTACT, MessageType.MULTI_CONTACT})

LOCATION_TYPES: frozenset[MessageType] = frozenset({MessageType.LOCATION, MessageType.LIVE_LOCATION})

# Types whose `text_data` is a title (contact name, poll question, event name) rather than a
# plain message body, so the placeholder label is kept in front of it.
_LABEL_PREFIXED_TYPES: frozenset[MessageType] = CONTACT_TYPES | {MessageType.POLL, MessageType.EVENT}

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
    MessageType.ADMIN_REVOKED: "[Deleted by admin]",
    MessageType.LIVE_LOCATION: "[Live location]",
    MessageType.GROUP_INVITE: "[Group invite]",
    MessageType.TEMPLATE_IMAGE: "[Image]",
    MessageType.TEMPLATE_DOCUMENT: "[Document]",
    MessageType.TEMPLATE_TEXT: "[Business message]",
    MessageType.TEMPLATE_VIDEO: "[Video]",
    MessageType.VIEW_ONCE_IMAGE: "[View-once image]",
    MessageType.VIEW_ONCE_VIDEO: "[View-once video]",
    MessageType.VIEW_ONCE_AUDIO: "[View-once audio]",
    MessageType.POLL: "[Poll]",
    MessageType.CALL: "[Call]",
    MessageType.EVENT: "[Event]",
    MessageType.ALBUM: "[Album]",
}


class ContactCard(BaseModel):
    """A contact (vCard) shared in a chat."""

    name: str
    phones: list[str]


class Location(BaseModel):
    """A shared pin or live location (for live shares: the last known position)."""

    latitude: float
    longitude: float
    name: str | None
    address: str | None
    live: bool


class PollOption(BaseModel):
    name: str
    votes: int


class Poll(BaseModel):
    """Options and current vote totals of a poll; the question is the message text."""

    options: list[PollOption]
    multiple_choice: bool


class MessageStats(BaseModel):
    total: int
    text: int
    media: int
    audio: int
    system: int
    revoked: int
    links: int


def message_display_text(*, text_data: str | None, message_type: int) -> str | None:
    """Text to show for a message: its own text, a type placeholder, or both for titled types.

    Contact, poll and event messages store a title in `text_data` (contact name, question,
    event name), so the placeholder is prefixed to mark it as such rather than plain text.
    """
    label = PLACEHOLDER_LABELS.get(message_type)
    if label is None or (text_data and message_type not in _LABEL_PREFIXED_TYPES):
        return text_data
    if not text_data:
        return label
    return f"{label} {text_data}"
