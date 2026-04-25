import logging
import sqlite3
from collections.abc import Generator

from db.row_types import RawReactionRow  # ty: ignore[unresolved-import]

logger = logging.getLogger(__name__)

# Joins: message_add_on links a reaction to a parent message,
# message_add_on_reaction has the emoji string and sender info.
_REACTIONS_SQL = """
SELECT
    ao.message_row_id      AS reaction_message_id,
    ao.parent_message_row_id AS parent_message_id,
    aor.reaction           AS emoji,
    COALESCE(sj.user, '')  AS sender_phone,
    ao.timestamp
FROM message_add_on ao
JOIN message_add_on_reaction aor ON aor.message_add_on_row_id = ao._id
LEFT JOIN jid sj ON ao.sender_jid_row_id = sj._id
"""


def fetch_reactions(conn: sqlite3.Connection) -> Generator[RawReactionRow]:
    try:
        for row in conn.execute(_REACTIONS_SQL):
            yield RawReactionRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("Reactions tables not found — skipping.")
