import sqlite3
from pathlib import Path

from db.queries.replies import fetch_replies
from seed_data import CHAT_GROUP, MSG_BOB_GROUP_HELLO, MSG_ME_GROUP


def test_fetch_replies_resolves_quoted_parent(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(fetch_replies(msgstore_conn))
    assert len(rows) == 1
    reply = rows[0]
    assert reply.message_id == MSG_ME_GROUP
    assert reply.quoted_message_id == MSG_BOB_GROUP_HELLO


def test_fetch_replies_scoped_to_chat(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(fetch_replies(msgstore_conn, chat_id=CHAT_GROUP))
    assert len(rows) == 1


def test_fetch_replies_scoped_to_missing_chat_returns_empty(msgstore_conn: sqlite3.Connection) -> None:
    assert list(fetch_replies(msgstore_conn, chat_id=999)) == []


def test_fetch_replies_missing_tables_returns_empty(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "no_replies.db")
    conn.row_factory = sqlite3.Row
    assert list(fetch_replies(conn)) == []
    conn.close()
