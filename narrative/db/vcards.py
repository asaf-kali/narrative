"""Parse vCards attached to contact messages into `ContactCard` models.

WhatsApp stores vCard 3.0 text, e.g.::

    BEGIN:VCARD
    VERSION:3.0
    N:;Alice;;;
    FN:Alice
    item1.TEL;waid=972501234567:+972 50-123-4567
    END:VCARD
"""

import logging
import re
import sqlite3

from narrative.db.queries.vcards import fetch_vcards
from narrative.models.message import ContactCard

logger = logging.getLogger(__name__)

ContactCardsByMessage = dict[int, list[ContactCard]]

_UNKNOWN_NAME = "Unknown contact"
# vCard text escapes (\\ \, \; \n): keep the escaped char, flatten \n to a space.
_ESCAPE_PATTERN = re.compile(r"\\(.)")


def load_contact_cards(conn: sqlite3.Connection, message_ids: set[int]) -> ContactCardsByMessage:
    """Map each contact message id to the cards it shares (in vCard order)."""
    cards: ContactCardsByMessage = {}
    for row in fetch_vcards(conn, message_ids=message_ids):
        card = parse_vcard(vcard=row.vcard or "")
        cards.setdefault(row.message_id, []).append(card)
    return cards


def parse_vcard(vcard: str) -> ContactCard:
    name = ""
    phones: list[str] = []
    for line in _unfold_lines(vcard=vcard):
        prop, _, value = line.partition(":")
        prop_name = _property_name(prop=prop)
        stripped = value.strip()
        value = _unescape(value=stripped)
        if prop_name == "FN" and value:
            name = value
        elif prop_name == "TEL" and value:
            phones.append(value)
    return ContactCard(name=name or _UNKNOWN_NAME, phones=phones)


def _unfold_lines(vcard: str) -> list[str]:
    """Join folded continuation lines (RFC 6350 §3.2: a line starting with a space or tab)."""
    lines: list[str] = []
    for raw in vcard.splitlines():
        if raw[:1] in {" ", "\t"} and lines:
            lines[-1] += raw[1:]
            continue
        lines.append(raw)
    return lines


def _property_name(prop: str) -> str:
    """`item1.TEL;type=CELL` → `TEL` (drop group prefix and parameters)."""
    name = prop.split(";", 1)[0]
    return name.rsplit(".", 1)[-1].upper()


def _unescape(value: str) -> str:
    return _ESCAPE_PATTERN.sub(_unescape_match, value)


def _unescape_match(match: re.Match[str]) -> str:
    char = match.group(1)
    return " " if char in {"n", "N"} else char
