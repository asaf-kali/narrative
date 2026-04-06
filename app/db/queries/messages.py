import logging
import sqlite3
from collections.abc import Generator

from db.row_types import RawMessageRow

logger = logging.getLogger(__name__)

# Fetches all messages with sender and chat info denormalized.
# - from_me=1: sent by device owner; from_me=0: received.
# - sender_jid_row_id is set for group messages (identifies who sent in the group).
# - For 1-on-1 chats, sender is derived from the chat JID + from_me flag.
# - text_data holds message text inline (message_text table is for link previews).
# - Recent WhatsApp versions use LID JIDs (server='lid') for group senders instead
#   of phone-based JIDs.  jid_map maps lid_row_id → jid_row_id for the phone JID,
#   so we join through it and prefer the resolved phone number (pj) over the raw lid.
_MESSAGES_SQL = """
SELECT
    m._id            AS message_id,
    m.chat_row_id,
    m.from_me,
    m.timestamp,
    m.received_timestamp,
    m.message_type,
    m.text_data,
    m.starred,
    COALESCE(pj.user, sj.user, '')   AS sender_phone,
    COALESCE(pj.server, sj.server, '') AS sender_server,
    c.subject              AS chat_subject,
    cj.user                AS chat_phone,
    cj.server              AS chat_server,
    cj.type                AS chat_jid_type
FROM message m
LEFT JOIN jid sj       ON m.sender_jid_row_id = sj._id
LEFT JOIN jid_map lm   ON sj._id = lm.lid_row_id AND sj.server = 'lid'
LEFT JOIN jid pj       ON lm.jid_row_id = pj._id
LEFT JOIN chat c       ON m.chat_row_id = c._id
LEFT JOIN jid cj       ON c.jid_row_id = cj._id
WHERE m.chat_row_id > 0
"""


def fetch_all_messages(conn: sqlite3.Connection) -> Generator[RawMessageRow]:
    for row in conn.execute(_MESSAGES_SQL):
        yield RawMessageRow.model_validate(dict(row))


def fetch_messages_for_chat(conn: sqlite3.Connection, chat_id: int) -> Generator[RawMessageRow]:
    sql = _MESSAGES_SQL + " AND m.chat_row_id = ?"
    for row in conn.execute(sql, (chat_id,)):
        yield RawMessageRow.model_validate(dict(row))
