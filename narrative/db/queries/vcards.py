import logging
import sqlite3
from collections.abc import Generator

from narrative.db.row_types import RawVcardRow

logger = logging.getLogger(__name__)

# message_vcard holds one row per shared contact; a multi-contact message
# (message_type = 14) has several rows for the same message_row_id.
_VCARDS_SQL = """
SELECT
    message_row_id AS message_id,
    vcard
FROM message_vcard
WHERE message_row_id IN ({placeholders})
ORDER BY message_row_id, _id
"""


def fetch_vcards(conn: sqlite3.Connection, message_ids: set[int]) -> Generator[RawVcardRow]:
    if not message_ids:
        return
    placeholders = ",".join("?" * len(message_ids))
    sql = _VCARDS_SQL.format(placeholders=placeholders)
    try:
        for row in conn.execute(sql, sorted(message_ids)):
            yield RawVcardRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("message_vcard table not found — skipping.")
