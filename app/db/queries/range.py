import logging
import sqlite3
from collections.abc import Generator
from datetime import datetime

from db.row_types import RawRangeMessageRow

logger = logging.getLogger(__name__)

# Safe mapping — never interpolate user input directly into SQL
_BUCKET_EXPR: dict[str, str] = {
    "hourly": "strftime('%Y-%m-%dT%H:00', m.timestamp / 1000, 'unixepoch', 'localtime')",
    "daily": "date(m.timestamp / 1000, 'unixepoch', 'localtime')",
    "weekly": "strftime('%Y-W%W', m.timestamp / 1000, 'unixepoch', 'localtime')",
    "monthly": "strftime('%Y-%m', m.timestamp / 1000, 'unixepoch', 'localtime')",
    "yearly": "strftime('%Y', m.timestamp / 1000, 'unixepoch', 'localtime')",
}

_RANGE_MESSAGES_SQL_TEMPLATE = """
SELECT
    m.timestamp,
    strftime('%Y-%m-%dT%H:%M', m.timestamp / 1000, 'unixepoch', 'localtime') AS local_dt,
    {bucket_expr}                                                               AS date_bucket,
    m.message_type,
    m.from_me,
    m.text_data,
    COALESCE(pj.user, sj.user, '')     AS sender_phone,
    COALESCE(pj.server, sj.server, '')  AS sender_server,
    c.subject                           AS chat_subject,
    cj.user                             AS chat_phone,
    cj.server                           AS chat_server
FROM message m
LEFT JOIN jid sj       ON m.sender_jid_row_id = sj._id
LEFT JOIN jid_map lm   ON sj._id = lm.lid_row_id AND sj.server = 'lid'
LEFT JOIN jid pj       ON lm.jid_row_id = pj._id
LEFT JOIN chat c       ON m.chat_row_id = c._id
LEFT JOIN jid cj       ON c.jid_row_id = cj._id
WHERE m.chat_row_id > 0
  AND m.message_type != 7
  AND m.timestamp >= ?
  AND m.timestamp <= ?
ORDER BY m.timestamp
"""


def fetch_range_messages(
    conn: sqlite3.Connection,
    date_from: datetime,
    date_to: datetime,
    bucket: str = "daily",
) -> Generator[RawRangeMessageRow]:
    """Yield all non-system messages between date_from and date_to (inclusive)."""
    bucket_expr = _BUCKET_EXPR.get(bucket, _BUCKET_EXPR["daily"])
    sql = _RANGE_MESSAGES_SQL_TEMPLATE.format(bucket_expr=bucket_expr)
    from_ms = int(date_from.timestamp() * 1000)
    to_ms = int(date_to.timestamp() * 1000)
    for row in conn.execute(sql, (from_ms, to_ms)):
        yield RawRangeMessageRow.model_validate(dict(row))
