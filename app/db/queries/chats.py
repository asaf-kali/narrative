import logging
import sqlite3
from collections.abc import Generator

from db.row_types import RawChatNameRow, RawChatRow

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


def fetch_chat_names(conn: sqlite3.Connection, chat_ids: list[int]) -> list[RawChatNameRow]:
    """Resolve chat identity (subject + jid) for specific chats, skipping message aggregation.

    Cheap counterpart to fetch_chats for display-name lookups: no GROUP BY over message.
    """
    if not chat_ids:
        return []
    # `placeholders` is only "?,?,..." parameter markers (count of chat_ids); the ids
    # themselves are bound as parameters below, so there is no injection vector.
    placeholders = ",".join("?" * len(chat_ids))
    sql = (
        "SELECT c._id AS chat_id, c.subject AS chat_subject, "  # noqa: S608
        "cj.user AS chat_phone, cj.server AS chat_server "
        "FROM chat c LEFT JOIN jid cj ON c.jid_row_id = cj._id "
        f"WHERE c._id IN ({placeholders})"
    )
    rows = conn.execute(sql, chat_ids).fetchall()
    return [RawChatNameRow.model_validate(dict(row)) for row in rows]
