import sqlite3
from pathlib import Path

from seed_data import CHAT_GROUP, MSG_BOB_GROUP_HELLO, MSG_CAROL_GROUP_HELLO

from narrative.db.queries.reactions import fetch_reactions


def test_fetch_reactions_all(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(fetch_reactions(msgstore_conn))
    assert {r.parent_message_id for r in rows} == {MSG_BOB_GROUP_HELLO, MSG_CAROL_GROUP_HELLO}


def test_fetch_reactions_scoped_to_chat(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(fetch_reactions(msgstore_conn, chat_id=CHAT_GROUP))
    assert len(rows) == 2


def test_fetch_reactions_scoped_to_missing_chat_returns_empty(msgstore_conn: sqlite3.Connection) -> None:
    assert list(fetch_reactions(msgstore_conn, chat_id=999)) == []


def test_fetch_reactions_missing_tables_returns_empty(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "no_reactions.db")
    conn.row_factory = sqlite3.Row
    assert list(fetch_reactions(conn)) == []
    conn.close()
