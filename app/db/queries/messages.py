import logging
import sqlite3
from collections.abc import Generator

from db.row_types import RawMessageRow, RawSenderCount

logger = logging.getLogger(__name__)

# Fetches all messages with sender and chat info denormalized.
# - from_me=1: sent by device owner; from_me=0: received.
# - sender_jid_row_id is set for group messages (identifies who sent in the group).
# - For 1-on-1 chats, sender is derived from the chat JID + from_me flag.
# - text_data holds message text inline (message_text table is for link previews).
# - Recent WhatsApp versions use LID JIDs (server='lid') for group senders instead
#   of phone-based JIDs.  jid_map maps lid_row_id → jid_row_id for the phone JID,
#   so we join through it and prefer the resolved phone number (pj) over the raw lid.
_MESSAGES_SQL = """
SELECT
    m._id            AS message_id,
    m.chat_row_id,
    m.from_me,
    m.timestamp,
    m.received_timestamp,
    m.message_type,
    m.text_data,
    m.starred,
    COALESCE(pj.user, sj.user, '')   AS sender_phone,
    COALESCE(pj.server, sj.server, '') AS sender_server,
    c.subject                    AS chat_subject,
    COALESCE(cj.user,   '')      AS chat_phone,
    COALESCE(cj.server, '')      AS chat_server,
    cj.type                AS chat_jid_type
FROM message m
LEFT JOIN jid sj       ON m.sender_jid_row_id = sj._id
LEFT JOIN jid_map lm   ON sj._id = lm.lid_row_id AND sj.server = 'lid'
LEFT JOIN jid pj       ON lm.jid_row_id = pj._id
LEFT JOIN chat c       ON m.chat_row_id = c._id
LEFT JOIN jid cj       ON c.jid_row_id = cj._id
WHERE m.chat_row_id > 0
"""

_SYSTEM_TYPE = 7

# Derives a stable sender_id from raw DB columns without requiring the contacts registry.
# Matches the Python logic in _build_sender_id_series: 'me' > phone > chat_phone fallback.
_SENDER_ID_CASE = (
    "CASE "
    "WHEN m.from_me = 1 THEN 'me' "
    "WHEN COALESCE(pj.user, sj.user, '') != '' THEN COALESCE(pj.user, sj.user) "
    "ELSE COALESCE(cj.user, '') "
    "END"
)


def _build_sql(
    extra_where: str = "",
    exclude_system: bool = True,
    date_from_ms: int | None = None,
    date_to_ms: int | None = None,
) -> tuple[str, list[int]]:
    sql = _MESSAGES_SQL + extra_where
    params: list[int] = []
    if exclude_system:
        sql += f" AND m.message_type != {_SYSTEM_TYPE}"
    if date_from_ms is not None:
        sql += " AND m.timestamp >= ?"
        params.append(date_from_ms)
    if date_to_ms is not None:
        sql += " AND m.timestamp <= ?"
        params.append(date_to_ms)
    return sql, params


def _build_browse_filter(
    chat_id: int | None = None,
    chat_ids: list[int] | None = None,
    date_from_ms: int | None = None,
    date_to_ms: int | None = None,
    exclude_system: bool = True,
    sender_ids: list[str] | None = None,
    search: str | None = None,
) -> tuple[str, list[int | str]]:
    where = ""
    params: list[int | str] = []
    if chat_id is not None:
        where += " AND m.chat_row_id = ?"
        params.append(chat_id)
    elif chat_ids:
        placeholders = ",".join("?" * len(chat_ids))
        where += f" AND m.chat_row_id IN ({placeholders})"
        params.extend(chat_ids)
    if exclude_system:
        where += f" AND m.message_type != {_SYSTEM_TYPE}"
    if date_from_ms is not None:
        where += " AND m.timestamp >= ?"
        params.append(date_from_ms)
    if date_to_ms is not None:
        where += " AND m.timestamp <= ?"
        params.append(date_to_ms)
    if search:
        where += " AND m.text_data LIKE ?"
        params.append(f"%{search}%")
    if sender_ids:
        placeholders = ",".join("?" * len(sender_ids))
        where += f" AND ({_SENDER_ID_CASE}) IN ({placeholders})"
        params.extend(sender_ids)
    return where, params


def fetch_messages_page(
    conn: sqlite3.Connection,
    chat_id: int | None = None,
    chat_ids: list[int] | None = None,
    date_from_ms: int | None = None,
    date_to_ms: int | None = None,
    exclude_system: bool = True,
    sender_ids: list[str] | None = None,
    search: str | None = None,
    sort_asc: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[RawMessageRow]:
    where, params = _build_browse_filter(
        chat_id=chat_id,
        chat_ids=chat_ids,
        date_from_ms=date_from_ms,
        date_to_ms=date_to_ms,
        exclude_system=exclude_system,
        sender_ids=sender_ids,
        search=search,
    )
    order = "ASC" if sort_asc else "DESC"
    sql = _MESSAGES_SQL + where + f" ORDER BY m.timestamp {order} LIMIT ? OFFSET ?"
    rows = conn.execute(sql, [*params, limit, offset]).fetchall()
    return [RawMessageRow.model_validate(dict(r)) for r in rows]


def count_filtered_messages(
    conn: sqlite3.Connection,
    chat_id: int | None = None,
    chat_ids: list[int] | None = None,
    date_from_ms: int | None = None,
    date_to_ms: int | None = None,
    exclude_system: bool = True,
    sender_ids: list[str] | None = None,
    search: str | None = None,
) -> int:
    where, params = _build_browse_filter(
        chat_id=chat_id,
        chat_ids=chat_ids,
        date_from_ms=date_from_ms,
        date_to_ms=date_to_ms,
        exclude_system=exclude_system,
        sender_ids=sender_ids,
        search=search,
    )
    # Reuse full JOIN set so sender_ids CASE expression resolves correctly.
    count_sql = "SELECT COUNT(*) FROM (SELECT m._id" + _MESSAGES_SQL[_MESSAGES_SQL.index("\nFROM") :] + where + ")"  # noqa: S608
    row = conn.execute(count_sql, params).fetchone()
    return int(row[0]) if row else 0


def fetch_distinct_chat_ids(
    conn: sqlite3.Connection,
    date_from_ms: int | None = None,
    date_to_ms: int | None = None,
    exclude_system: bool = True,
) -> list[int]:
    sql = "SELECT DISTINCT m.chat_row_id FROM message m WHERE m.chat_row_id > 0"
    params: list[int] = []
    if exclude_system:
        sql += f" AND m.message_type != {_SYSTEM_TYPE}"
    if date_from_ms is not None:
        sql += " AND m.timestamp >= ?"
        params.append(date_from_ms)
    if date_to_ms is not None:
        sql += " AND m.timestamp <= ?"
        params.append(date_to_ms)
    return [r[0] for r in conn.execute(sql, params).fetchall()]


def fetch_all_messages(
    conn: sqlite3.Connection,
    date_from_ms: int | None = None,
    date_to_ms: int | None = None,
    exclude_system: bool = True,
) -> Generator[RawMessageRow]:
    sql, params = _build_sql(exclude_system=exclude_system, date_from_ms=date_from_ms, date_to_ms=date_to_ms)
    for row in conn.execute(sql, params):
        yield RawMessageRow.model_validate(dict(row))


def fetch_messages_for_chat(
    conn: sqlite3.Connection,
    chat_id: int,
    date_from_ms: int | None = None,
    date_to_ms: int | None = None,
    exclude_system: bool = True,
) -> Generator[RawMessageRow]:
    sql, params = _build_sql(
        extra_where=" AND m.chat_row_id = ?",
        exclude_system=exclude_system,
        date_from_ms=date_from_ms,
        date_to_ms=date_to_ms,
    )
    for row in conn.execute(sql, [chat_id, *params]):
        yield RawMessageRow.model_validate(dict(row))


_SENDER_COUNTS_SQL = """
SELECT
    (CASE
        WHEN m.from_me = 1 THEN 'me'
        WHEN COALESCE(pj.user, sj.user, '') != '' THEN COALESCE(pj.user, sj.user)
        ELSE COALESCE(cj.user, '')
    END) AS sender_id,
    m.from_me,
    (CASE
        WHEN m.from_me = 1 THEN ''
        WHEN COALESCE(pj.user, sj.user, '') != '' THEN COALESCE(pj.user, sj.user)
        WHEN COALESCE(cj.server, '') NOT LIKE '%g.us' THEN COALESCE(cj.user, '')
        ELSE ''
    END) AS effective_phone,
    COUNT(*) AS message_count
FROM message m
LEFT JOIN jid sj       ON m.sender_jid_row_id = sj._id
LEFT JOIN jid_map lm   ON sj._id = lm.lid_row_id AND sj.server = 'lid'
LEFT JOIN jid pj       ON lm.jid_row_id = pj._id
LEFT JOIN chat c       ON m.chat_row_id = c._id
LEFT JOIN jid cj       ON c.jid_row_id = cj._id
WHERE m.chat_row_id > 0 AND m.message_type != {_SYSTEM_TYPE}
GROUP BY sender_id
ORDER BY message_count DESC
"""


def fetch_sender_counts(conn: sqlite3.Connection) -> list[RawSenderCount]:
    sql = _SENDER_COUNTS_SQL.format(_SYSTEM_TYPE=_SYSTEM_TYPE)
    return [RawSenderCount.model_validate(dict(r)) for r in conn.execute(sql).fetchall()]


def count_messages(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM message WHERE chat_row_id > 0 AND message_type != 7").fetchone()
    return int(row[0]) if row else 0


def count_messages_for_chat(conn: sqlite3.Connection, chat_id: int, after_id: int = 0) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM message WHERE chat_row_id = ? AND _id > ? AND message_type != 7",
        (chat_id, after_id),
    ).fetchone()
    return int(row[0]) if row else 0


def get_max_message_id_for_chat(conn: sqlite3.Connection, chat_id: int) -> int:
    row = conn.execute("SELECT MAX(_id) FROM message WHERE chat_row_id = ?", (chat_id,)).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


# Cursor-based pagination on _id (stable PK, no timestamp ties).
_MESSAGES_PAGED_SQL = _MESSAGES_SQL + " AND m.chat_row_id = ? AND m._id > ? ORDER BY m._id LIMIT ?"


def fetch_messages_for_chat_paged(
    conn: sqlite3.Connection,
    chat_id: int,
    after_id: int,
    limit: int,
) -> list[RawMessageRow]:
    rows = conn.execute(_MESSAGES_PAGED_SQL, (chat_id, after_id, limit)).fetchall()
    return [RawMessageRow.model_validate(dict(r)) for r in rows]


def fetch_index_rows_paged(
    conn: sqlite3.Connection,
    chat_id: int,
    after_id: int,
    limit: int,
) -> list[sqlite3.Row]:
    """Return raw sqlite3.Row objects — no Pydantic overhead. For the indexer hot path only."""
    return conn.execute(_MESSAGES_PAGED_SQL, (chat_id, after_id, limit)).fetchall()
