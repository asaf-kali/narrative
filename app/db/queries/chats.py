import logging
import sqlite3

logger = logging.getLogger(__name__)

_CHATS_SQL = """
SELECT
    c._id              AS chat_id,
    c.subject          AS chat_subject,
    c.created_timestamp,
    cj.user            AS chat_phone,
    cj.server          AS chat_server,
    cj.type            AS chat_jid_type,
    COUNT(m._id)       AS message_count,
    MIN(m.timestamp)   AS first_timestamp,
    MAX(m.timestamp)   AS last_timestamp
FROM chat c
LEFT JOIN jid cj   ON c.jid_row_id = cj._id
LEFT JOIN message m ON m.chat_row_id = c._id AND m.chat_row_id > 0
GROUP BY c._id
ORDER BY last_timestamp DESC
"""


def fetch_chats(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = conn.execute(_CHATS_SQL)
    return cursor.fetchall()
