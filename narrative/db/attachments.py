"""Type-specific details (contact cards, locations, polls, ...) attached to a page of messages.

Each kind is loaded with one query over just the message ids of the matching
types, so a page of plain text messages costs no extra queries.
"""

import logging
import sqlite3
from typing import Any

from pydantic import BaseModel, Field

from narrative.db.locations import LocationsByMessage, load_locations
from narrative.db.polls import PollsByMessage, load_polls
from narrative.db.row_types import RawMessageRow
from narrative.db.vcards import ContactCardsByMessage, load_contact_cards
from narrative.models.message import CONTACT_TYPES, LOCATION_TYPES, MessageType

logger = logging.getLogger(__name__)

_POLL_TYPES: frozenset[MessageType] = frozenset({MessageType.POLL})


class MessageAttachments(BaseModel):
    contacts: ContactCardsByMessage = Field(default_factory=dict)
    locations: LocationsByMessage = Field(default_factory=dict)
    polls: PollsByMessage = Field(default_factory=dict)

    def fields_for(self, message_id: int) -> dict[str, Any]:
        """Return API fields for one message; each is `None` when the message lacks that detail."""
        cards = self.contacts.get(message_id)
        location = self.locations.get(message_id)
        poll = self.polls.get(message_id)
        return {
            "contacts": [c.model_dump() for c in cards] if cards else None,
            "location": location.model_dump() if location else None,
            "poll": poll.model_dump() if poll else None,
        }


def load_message_attachments(conn: sqlite3.Connection, rows: list[RawMessageRow]) -> MessageAttachments:
    contact_ids = _ids_of_types(rows=rows, types=CONTACT_TYPES)
    contacts = load_contact_cards(conn, message_ids=contact_ids)
    location_ids = _ids_of_types(rows=rows, types=LOCATION_TYPES)
    locations = load_locations(conn, message_ids=location_ids)
    poll_ids = _ids_of_types(rows=rows, types=_POLL_TYPES)
    polls = load_polls(conn, message_ids=poll_ids)
    return MessageAttachments(contacts=contacts, locations=locations, polls=polls)


def _ids_of_types(rows: list[RawMessageRow], types: frozenset[MessageType]) -> set[int]:
    return {r.message_id for r in rows if r.message_type in types}
