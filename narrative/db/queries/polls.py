import logging
import sqlite3
from collections.abc import Generator

from narrative.db.row_types import RawPollOptionRow

logger = logging.getLogger(__name__)

# One row per poll option (message_type 66); the poll question is the message's text_data.
# vote_total matches the count of message_add_on_poll_vote_selected_option rows per option.
# selectable_options_count: 1 = single choice, 0 = any number of options.
_POLL_OPTIONS_SQL = """
SELECT
    o.message_row_id            AS message_id,
    o.option_name,
    o.vote_total,
    p.selectable_options_count
FROM message_poll_option o
LEFT JOIN message_poll p ON p.message_row_id = o.message_row_id
WHERE o.message_row_id IN ({placeholders})
ORDER BY o.message_row_id, o._id
"""


def fetch_poll_options(conn: sqlite3.Connection, message_ids: set[int]) -> Generator[RawPollOptionRow]:
    if not message_ids:
        return
    placeholders = ",".join("?" * len(message_ids))
    sql = _POLL_OPTIONS_SQL.format(placeholders=placeholders)
    try:
        for row in conn.execute(sql, sorted(message_ids)):
            yield RawPollOptionRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("Poll tables not found — skipping.")
