import logging
import sqlite3
from collections.abc import Generator

from narrative.db.row_types import RawCallRow, RawMessageCallRow

logger = logging.getLogger(__name__)

# call_result values observed in real data:
# 0=unknown, 2=missed, 3=busy, 4=declined, 5=connected/completed
_CALLS_SQL = """
SELECT
    cl._id          AS call_id,
    cl.timestamp,
    cl.call_result,
    cl.duration,
    cl.video_call   AS is_video,
    cl.from_me,
    COALESCE(j.user, '') AS caller_phone
FROM call_log cl
LEFT JOIN jid j ON cl.jid_row_id = j._id
"""


# Call events shown inside a chat (message_type 90) link to call_log via message_call_log.
_MESSAGE_CALLS_SQL = """
SELECT
    mc.message_row_id AS message_id,
    cl.call_result,
    cl.duration,
    cl.video_call     AS is_video
FROM message_call_log mc
JOIN call_log cl ON cl._id = mc.call_log_row_id
WHERE mc.message_row_id IN ({placeholders})
"""


def fetch_calls(conn: sqlite3.Connection) -> Generator[RawCallRow]:
    try:
        for row in conn.execute(_CALLS_SQL):
            yield RawCallRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("call_log table not found — skipping.")


def fetch_message_calls(conn: sqlite3.Connection, message_ids: set[int]) -> Generator[RawMessageCallRow]:
    if not message_ids:
        return
    placeholders = ",".join("?" * len(message_ids))
    sql = _MESSAGE_CALLS_SQL.format(placeholders=placeholders)
    try:
        for row in conn.execute(sql, sorted(message_ids)):
            yield RawMessageCallRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("message_call_log table not found — skipping.")
