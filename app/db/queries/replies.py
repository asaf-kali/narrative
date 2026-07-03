import logging
import sqlite3
from collections.abc import Generator

from db.row_types import RawReplyRow

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


def fetch_replies(conn: sqlite3.Connection, chat_id: int | None = None) -> Generator[RawReplyRow]:
    sql = _REPLIES_SQL
    params: tuple[int, ...] = ()
    if chat_id is not None:
        sql = f"{sql} WHERE mq.chat_row_id = ?"
        params = (chat_id,)
    try:
        for row in conn.execute(sql, params):
            yield RawReplyRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("Quoted-message table not found — skipping.")
