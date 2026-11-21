import sqlite3
from pathlib import Path

from seed_data import BOB_PHONE, CHAT_DIRECT, CHAT_GROUP, MSG_CAROL_GROUP_HELLO

from narrative.db.queries.mentions import fetch_mentions


def test_fetch_mentions_resolves_lid_to_phone(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(fetch_mentions(msgstore_conn))
    assert len(rows) == 1
    mention = rows[0]
    assert mention.message_id == MSG_CAROL_GROUP_HELLO
    assert mention.chat_row_id == CHAT_GROUP
    assert mention.mentioned_phone == BOB_PHONE


def test_fetch_mentions_scoped_to_chat(msgstore_conn: sqlite3.Connection) -> None:
    assert len(list(fetch_mentions(msgstore_conn, chat_id=CHAT_GROUP))) == 1
    assert list(fetch_mentions(msgstore_conn, chat_id=CHAT_DIRECT)) == []


def test_fetch_mentions_missing_table_returns_empty(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "no_mentions.db")
    conn.row_factory = sqlite3.Row
    assert list(fetch_mentions(conn)) == []
    conn.close()
