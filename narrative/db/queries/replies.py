import json
import logging
import sqlite3
from collections.abc import Generator

from narrative.db.row_types import RawReplyRow

logger = logging.getLogger(__name__)

# message_quoted holds one row per reply message X. mq.message_row_id = X's message._id.
# The remaining columns snapshot the quoted parent Y (from_me/sender/text/type), so the
# preview renders even when Y is gone. The true parent Y._id is resolved via (key_id, chat)
# which is unique in `message`; it stays NULL for deleted/aged-out parents.
# Quoted sender jid is resolved through the standard LID->phone block; chat jid gives the
# 1-on-1 fallback for the other party.
_REPLIES_SQL = """
SELECT
    mq.message_row_id                  AS message_id,
    orig._id                           AS quoted_message_id,
    mq.chat_row_id,
    mq.from_me                         AS quoted_from_me,
    mq.message_type                    AS quoted_type,
    mq.text_data                       AS quoted_text,
    COALESCE(pj.user, sj.user, '')     AS quoted_phone,
    COALESCE(cj.user, '')              AS chat_phone,
    mq.timestamp
FROM message_quoted mq
LEFT JOIN message orig ON orig.key_id = mq.key_id
                      AND orig.chat_row_id = mq.parent_message_chat_row_id
LEFT JOIN jid sj     ON mq.sender_jid_row_id = sj._id
LEFT JOIN jid_map lm ON sj._id = lm.lid_row_id AND sj.server = 'lid'
LEFT JOIN jid pj     ON lm.jid_row_id = pj._id
LEFT JOIN chat c     ON mq.chat_row_id = c._id
LEFT JOIN jid cj     ON c.jid_row_id = cj._id
"""


def fetch_replies(
    conn: sqlite3.Connection,
    chat_id: int | None = None,
    message_ids: set[int] | None = None,
) -> Generator[RawReplyRow]:
    """Yield replies, optionally scoped to one chat and/or to specific reply messages."""
    conditions: list[str] = []
    params: list[int | str] = []
    if chat_id is not None:
        conditions.append("mq.chat_row_id = ?")
        params.append(chat_id)
    if message_ids is not None:
        # One JSON-array parameter instead of N placeholders: no SQLite variable limit.
        conditions.append("mq.message_row_id IN (SELECT value FROM json_each(?))")
        ids_json = json.dumps(sorted(message_ids))
        params.append(ids_json)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = _REPLIES_SQL + where
    try:
        for row in conn.execute(sql, params):
            yield RawReplyRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("Quoted-message table not found — skipping.")
