import logging
import sqlite3
from collections.abc import Generator

from db.row_types import RawReactionRow

logger = logging.getLogger(__name__)

# Joins: message_add_on links a reaction to a parent message (parent_message_row_id),
# message_add_on_reaction has the emoji string. Reactor jid is resolved through the
# standard LID->phone block; chat jid provides the 1-on-1 fallback for the other party.
# message_add_on_type = 56 is the reaction add-on; empty reaction = removed reaction.
_REACTIONS_SQL = """
SELECT
    ao._id                             AS reaction_id,
    ao.parent_message_row_id           AS parent_message_id,
    ao.chat_row_id,
    ao.from_me,
    aor.reaction                       AS emoji,
    COALESCE(pj.user, sj.user, '')     AS reactor_phone,
    COALESCE(cj.user, '')              AS chat_phone,
    ao.timestamp
FROM message_add_on ao
JOIN message_add_on_reaction aor ON aor.message_add_on_row_id = ao._id
LEFT JOIN jid sj     ON ao.sender_jid_row_id = sj._id
LEFT JOIN jid_map lm ON sj._id = lm.lid_row_id AND sj.server = 'lid'
LEFT JOIN jid pj     ON lm.jid_row_id = pj._id
LEFT JOIN chat c     ON ao.chat_row_id = c._id
LEFT JOIN jid cj     ON c.jid_row_id = cj._id
WHERE ao.message_add_on_type = 56 AND aor.reaction != ''
"""


def fetch_reactions(conn: sqlite3.Connection, chat_id: int | None = None) -> Generator[RawReactionRow]:
    sql = _REACTIONS_SQL
    params: tuple[int, ...] = ()
    if chat_id is not None:
        sql = f"{sql} AND ao.chat_row_id = ?"
        params = (chat_id,)
    try:
        for row in conn.execute(sql, params):
            yield RawReactionRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("Reactions tables not found — skipping.")
