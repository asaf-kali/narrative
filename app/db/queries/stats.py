import logging
import sqlite3

logger = logging.getLogger(__name__)

# Groups all non-system messages by local calendar day.
# SQLite's 'localtime' modifier converts the UTC unix timestamp to local time
# so the day boundary matches the user's clock.
_DAILY_COUNTS_SQL = """
SELECT
    date(timestamp / 1000, 'unixepoch', 'localtime') AS day,
    COUNT(*) AS count
FROM message
WHERE message_type != 7
  AND chat_row_id > 0
GROUP BY day
ORDER BY day
"""


def fetch_daily_counts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(_DAILY_COUNTS_SQL).fetchall()
