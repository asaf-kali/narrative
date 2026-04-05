import logging
import sqlite3

logger = logging.getLogger(__name__)

# Full-text search across all messages.
# - Only searches text messages (message_type = 0) for relevance.
# - Uses LIKE with leading wildcard — no index, acceptable for interactive search
#   with debounce and a reasonable LIMIT.
# - LID JIDs resolved via jid_map (same pattern as messages query).
# - Results ordered newest-first so the most recent matches appear at the top.
_SEARCH_SQL = """
SELECT
    c._id                                                              AS chat_id,
    c.subject                                                          AS chat_subject,
    cj.user                                                            AS chat_phone,
    cj.server                                                          AS chat_server,
    strftime('%Y-%m-%dT%H:%M:%S', m.timestamp / 1000, 'unixepoch', 'localtime') AS timestamp,
    m.text_data,
    m.from_me,
    COALESCE(pj.user, sj.user, '')    AS sender_phone,
    COALESCE(pj.server, sj.server, '') AS sender_server
FROM message m
LEFT JOIN jid sj      ON m.sender_jid_row_id = sj._id
LEFT JOIN jid_map lm  ON sj._id = lm.lid_row_id AND sj.server = 'lid'
LEFT JOIN jid pj      ON lm.jid_row_id = pj._id
LEFT JOIN chat c      ON m.chat_row_id = c._id
LEFT JOIN jid cj      ON c.jid_row_id = cj._id
WHERE m.chat_row_id > 0
  AND m.message_type = 0
  AND m.text_data LIKE ? ESCAPE '\\'
ORDER BY m.timestamp DESC
LIMIT ?
"""


def _escape_like(term: str) -> str:
    """Escape LIKE special characters so the user's query is treated literally."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_messages(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[sqlite3.Row]:
    pattern = f"%{_escape_like(query)}%"
    return conn.execute(_SEARCH_SQL, (pattern, limit)).fetchall()
