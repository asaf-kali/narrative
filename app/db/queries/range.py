import logging
import sqlite3
from collections.abc import Generator
from datetime import datetime

from db.row_types import RawRangeMessageRow

logger = logging.getLogger(__name__)

_RANGE_MESSAGES_SQL = """
SELECT
    m.timestamp,
    strftime('%Y-%m-%dT%H:%M', m.timestamp / 1000, 'unixepoch', 'localtime') AS local_dt,
    m.message_type,
    m.from_me,
    m.text_data,
    COALESCE(pj.user, sj.user, '')     AS sender_phone,
    COALESCE(pj.server, sj.server, '')  AS sender_server,
    c.subject                           AS chat_subject,
    cj.user                             AS chat_phone,
    cj.server                           AS chat_server
FROM message m
LEFT JOIN jid sj       ON m.sender_jid_row_id = sj._id
LEFT JOIN jid_map lm   ON sj._id = lm.lid_row_id AND sj.server = 'lid'
LEFT JOIN jid pj       ON lm.jid_row_id = pj._id
LEFT JOIN chat c       ON m.chat_row_id = c._id
LEFT JOIN jid cj       ON c.jid_row_id = cj._id
WHERE m.chat_row_id > 0
  AND m.message_type != 7
  AND m.timestamp >= ?
  AND m.timestamp <= ?
ORDER BY m.timestamp
"""


def fetch_range_messages(
    conn: sqlite3.Connection,
    date_from: datetime,
    date_to: datetime,
) -> Generator[RawRangeMessageRow]:
    """Yield all non-system messages between date_from and date_to (inclusive)."""
    from_ms = int(date_from.timestamp() * 1000)
    to_ms = int(date_to.timestamp() * 1000)
    for row in conn.execute(_RANGE_MESSAGES_SQL, (from_ms, to_ms)):
        yield RawRangeMessageRow.model_validate(dict(row))
