import sqlite3
from pathlib import Path

from seed_data import DAVE_VCARD, ERIN_VCARD, FRANK_VCARD, MSG_ALICE_CONTACT, MSG_ALICE_HELLO, MSG_ME_CONTACTS

from narrative.db.queries.vcards import fetch_vcards


def test_fetch_vcards_returns_rows_in_message_then_insert_order(contacts_msgstore_conn: sqlite3.Connection) -> None:
    rows = list(fetch_vcards(contacts_msgstore_conn, message_ids={MSG_ME_CONTACTS, MSG_ALICE_CONTACT}))
    assert [(r.message_id, r.vcard) for r in rows] == [
        (MSG_ALICE_CONTACT, DAVE_VCARD),
        (MSG_ME_CONTACTS, ERIN_VCARD),
        (MSG_ME_CONTACTS, FRANK_VCARD),
    ]


def test_fetch_vcards_ignores_messages_without_vcards(contacts_msgstore_conn: sqlite3.Connection) -> None:
    assert list(fetch_vcards(contacts_msgstore_conn, message_ids={MSG_ALICE_HELLO})) == []


def test_fetch_vcards_empty_ids_returns_empty(contacts_msgstore_conn: sqlite3.Connection) -> None:
    assert list(fetch_vcards(contacts_msgstore_conn, message_ids=set())) == []


def test_fetch_vcards_missing_table_returns_empty(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "no_vcards.db")
    conn.row_factory = sqlite3.Row
    assert list(fetch_vcards(conn, message_ids={1})) == []
    conn.close()
