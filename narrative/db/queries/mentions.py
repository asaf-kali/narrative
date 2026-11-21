import logging
import sqlite3
from collections.abc import Generator

from narrative.db.row_types import RawMentionRow

logger = logging.getLogger(__name__)

# message_mentions holds one row per @mention: mm.message_row_id is the mentioning message,
# mm.jid_row_id the mentioned user. The mentioned jid is resolved through the standard
# LID->phone block. The message join supplies the chat for scoping.
_MENTIONS_SQL = """
SELECT
    mm.message_row_id                  AS message_id,
    m.chat_row_id,
    COALESCE(pj.user, mj.user, '')     AS mentioned_phone
FROM message_mentions mm
JOIN message m       ON m._id = mm.message_row_id
LEFT JOIN jid mj     ON mm.jid_row_id = mj._id
LEFT JOIN jid_map lm ON mj._id = lm.lid_row_id AND mj.server = 'lid'
LEFT JOIN jid pj     ON lm.jid_row_id = pj._id
"""


def fetch_mentions(conn: sqlite3.Connection, chat_id: int | None = None) -> Generator[RawMentionRow]:
    """Yield @mentions, optionally scoped to one chat."""
    sql = _MENTIONS_SQL
    params: list[int] = []
    if chat_id is not None:
        sql += " WHERE m.chat_row_id = ?"
        params.append(chat_id)
    try:
        for row in conn.execute(sql, params):
            yield RawMentionRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("Mentions table not found — skipping.")
