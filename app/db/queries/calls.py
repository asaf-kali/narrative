import logging
import sqlite3

logger = logging.getLogger(__name__)

# call_result values observed in real data:
# 0=unknown, 2=missed, 3=busy, 4=declined, 5=connected/completed
_CALLS_SQL = """
SELECT
    cl._id          AS call_id,
    cl.jid_row_id,
    cl.timestamp,
    cl.call_result,
    cl.duration,
    cl.video_call   AS is_video,
    cl.from_me,
    COALESCE(j.user, '') AS caller_phone
FROM call_log cl
LEFT JOIN jid j ON cl.jid_row_id = j._id
"""


def fetch_calls(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    try:
        cursor = conn.execute(_CALLS_SQL)
        return cursor.fetchall()
    except sqlite3.OperationalError:
        logger.debug("call_log table not found — skipping.")
        return []
