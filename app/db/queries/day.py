import logging
import sqlite3
from collections.abc import Generator

from db.row_types import RawDayMessageRow

logger = logging.getLogger(__name__)

# Fetches every non-system message for a given local calendar day,
# with sender resolved through jid_map (LID → phone JID) and chat name.
# Returns rows sorted by timestamp ascending so the caller gets a ready-to-use feed.
_DAY_MESSAGES_SQL = """
SELECT
    m.timestamp,
    strftime('%H:%M', m.timestamp / 1000, 'unixepoch', 'localtime') AS time,
    m.message_type,
    m.from_me,
    m.text_data,
    COALESCE(pj.user, sj.user, '')    AS sender_phone,
    COALESCE(pj.server, sj.server, '') AS sender_server,
    c.subject                          AS chat_subject,
    cj.user                            AS chat_phone,
    cj.server                          AS chat_server
FROM message m
LEFT JOIN jid sj       ON m.sender_jid_row_id = sj._id
LEFT JOIN jid_map lm   ON sj._id = lm.lid_row_id AND sj.server = 'lid'
LEFT JOIN jid pj       ON lm.jid_row_id = pj._id
LEFT JOIN chat c       ON m.chat_row_id = c._id
LEFT JOIN jid cj       ON c.jid_row_id = cj._id
WHERE m.chat_row_id > 0
  AND m.message_type != 7
  AND date(m.timestamp / 1000, 'unixepoch', 'localtime') = ?
ORDER BY m.timestamp
"""


def fetch_day_messages(conn: sqlite3.Connection, date: str) -> Generator[RawDayMessageRow]:
    """Yield all non-system messages for `date` (YYYY-MM-DD) sorted by time."""
    for row in conn.execute(_DAY_MESSAGES_SQL, (date,)):
        yield RawDayMessageRow.model_validate(dict(row))
