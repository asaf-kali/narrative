"""Secondary indexes for msgstore.db.

Decrypted crypt15 backups keep only SQLite's automatic (UNIQUE/PK) indexes, so every
filter on `message` scans the whole table. The server opens the DB read-only, so the
indexes are created once at startup through a short-lived read-write connection.
`CREATE INDEX IF NOT EXISTS` makes this a no-op on later starts.
"""

import logging
import sqlite3
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class IndexSpec(BaseModel):
    name: str
    table: str
    columns: str


INDEXES: list[IndexSpec] = [
    # Per-chat pages, chat DataFrames, and per-chat date filters.
    IndexSpec(name="narrative_message_chat_ts", table="message", columns="chat_row_id, timestamp"),
    # Global pages ordered by time, and global date-range filters.
    IndexSpec(name="narrative_message_ts", table="message", columns="timestamp"),
    # Resolving a quoted message to its parent row (replies join on key_id + chat).
    IndexSpec(name="narrative_message_key", table="message", columns="key_id, chat_row_id"),
    # Reactions for a set of messages, and reactions per chat.
    IndexSpec(name="narrative_add_on_parent", table="message_add_on", columns="parent_message_row_id"),
    IndexSpec(name="narrative_add_on_chat", table="message_add_on", columns="chat_row_id"),
    # Replies per chat.
    IndexSpec(name="narrative_quoted_chat", table="message_quoted", columns="chat_row_id"),
]


def ensure_indexes(msgstore_path: Path) -> None:
    """Create any missing secondary indexes; refresh planner stats if one was added.

    A failure (read-only file, locked DB) is logged and skipped: queries still work, just slower.
    """
    try:
        conn = sqlite3.connect(msgstore_path)
    except sqlite3.Error:
        logger.warning(f"Could not open {msgstore_path} read-write; skipping index creation", exc_info=True)
        return
    try:
        _create_missing(conn=conn)
    finally:
        conn.close()


def _create_missing(conn: sqlite3.Connection) -> None:
    existing = _existing_index_names(conn=conn)
    created = [spec.name for spec in INDEXES if spec.name not in existing and _create_index(conn=conn, spec=spec)]
    if not created:
        return
    conn.execute("ANALYZE")
    conn.commit()
    logger.info(f"Created msgstore indexes: {', '.join(created)}")


def _existing_index_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    return {row[0] for row in rows}


def _create_index(conn: sqlite3.Connection, spec: IndexSpec) -> bool:
    # Names, tables and columns come from the INDEXES constant above, never from user input.
    sql = f"CREATE INDEX IF NOT EXISTS {spec.name} ON {spec.table} ({spec.columns})"
    try:
        conn.execute(sql)
    except sqlite3.Error as exc:
        # Missing table (older WhatsApp schema) or read-only file.
        logger.warning(f"Skipping index {spec.name}: {exc}")
        return False
    return True
