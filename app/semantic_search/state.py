from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from semantic_search.session import Session, SessionMeta

_SCHEMA = """
CREATE TABLE IF NOT EXISTS index_state (
    chat_id INTEGER PRIMARY KEY,
    max_indexed_message_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS indexed_sessions (
    session_id TEXT PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    min_message_id INTEGER NOT NULL,
    max_message_id INTEGER NOT NULL,
    timestamp_start INTEGER NOT NULL,
    timestamp_end INTEGER NOT NULL
);
"""


class StateDB:
    def __init__(self, search_dir: Path) -> None:
        search_dir.mkdir(parents=True, exist_ok=True)
        self._path = search_dir / "state.db"
        self._conn = sqlite3.connect(str(self._path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def get_max_indexed(self, chat_id: int) -> int:
        row = self._conn.execute(
            "SELECT max_indexed_message_id FROM index_state WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return int(row[0]) if row else 0

    def upsert_state(self, chat_id: int, max_id: int) -> None:
        self._conn.execute(
            "INSERT INTO index_state (chat_id, max_indexed_message_id) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET max_indexed_message_id = excluded.max_indexed_message_id",
            (chat_id, max_id),
        )
        self._conn.commit()

    def insert_sessions(self, sessions: list[Session]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO indexed_sessions "
            "(session_id, chat_id, min_message_id, max_message_id, timestamp_start, timestamp_end) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    s.session_id,
                    s.chat_id,
                    s.min_message_id,
                    s.max_message_id,
                    int(s.timestamp_start.timestamp() * 1000),
                    int(s.timestamp_end.timestamp() * 1000),
                )
                for s in sessions
            ],
        )
        self._conn.commit()

    def delete_session(self, session_id: str) -> None:
        self._conn.execute("DELETE FROM indexed_sessions WHERE session_id = ?", (session_id,))
        self._conn.commit()

    def get_last_session(self, chat_id: int) -> SessionMeta | None:
        row = self._conn.execute(
            "SELECT session_id, chat_id, min_message_id, max_message_id, timestamp_start, timestamp_end "
            "FROM indexed_sessions WHERE chat_id = ? ORDER BY max_message_id DESC LIMIT 1",
            (chat_id,),
        ).fetchone()
        if row is None:
            return None
        return SessionMeta(
            session_id=row[0],
            chat_id=row[1],
            min_message_id=row[2],
            max_message_id=row[3],
            timestamp_start=datetime.fromtimestamp(row[4] / 1000, tz=UTC),
            timestamp_end=datetime.fromtimestamp(row[5] / 1000, tz=UTC),
        )

    def all_chat_ids(self) -> list[int]:
        rows = self._conn.execute("SELECT chat_id FROM index_state").fetchall()
        return [int(r[0]) for r in rows]

    def count_sessions_for_chat(self, chat_id: int) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM indexed_sessions WHERE chat_id = ?", (chat_id,)).fetchone()
        return int(row[0]) if row else 0
