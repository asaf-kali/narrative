import logging
import sqlite3
from collections.abc import Generator

from db.row_types import RawChatRow  # ty: ignore[unresolved-import]

logger = logging.getLogger(__name__)

_CHATS_SQL = """
SELECT
    c._id              AS chat_id,
    c.subject          AS chat_subject,
    c.created_timestamp,
    cj.user            AS chat_phone,
    cj.server          AS chat_server,
    cj.type            AS chat_jid_type,
    COUNT(CASE WHEN m.message_type != 7 THEN 1 END) AS message_count,
    MIN(m.timestamp)   AS first_timestamp,
    MAX(m.timestamp)   AS last_timestamp
FROM chat c
LEFT JOIN jid cj   ON c.jid_row_id = cj._id
LEFT JOIN message m ON m.chat_row_id = c._id AND m.chat_row_id > 0
GROUP BY c._id
ORDER BY last_timestamp DESC
"""


def fetch_chats(conn: sqlite3.Connection) -> Generator[RawChatRow]:
    for row in conn.execute(_CHATS_SQL):
        yield RawChatRow.model_validate(dict(row))
