import sqlite3

from seed_data import ALICE_PHONE, CHAT_DIRECT, CHAT_GROUP, GROUP_SUBJECT

from narrative.db.queries.chats import fetch_chat_names, fetch_chats


def test_fetch_chats_returns_all_three(msgstore_conn: sqlite3.Connection) -> None:
    chats = list(fetch_chats(msgstore_conn))
    assert len(chats) == 3


def test_fetch_chats_message_count_excludes_system(msgstore_conn: sqlite3.Connection) -> None:
    chats = list(fetch_chats(msgstore_conn))
    direct = next(c for c in chats if c.chat_id == CHAT_DIRECT)
    assert direct.message_count == 3


def test_fetch_chats_group_has_subject_and_phone(msgstore_conn: sqlite3.Connection) -> None:
    chats = list(fetch_chats(msgstore_conn))
    group = next(c for c in chats if c.chat_id == CHAT_GROUP)
    assert group.chat_subject == GROUP_SUBJECT
    assert group.chat_server == "g.us"


def test_fetch_chat_names_resolves_requested_ids(msgstore_conn: sqlite3.Connection) -> None:
    names = fetch_chat_names(msgstore_conn, [CHAT_DIRECT])
    assert len(names) == 1
    assert names[0].chat_phone == ALICE_PHONE


def test_fetch_chat_names_empty_list_returns_empty(msgstore_conn: sqlite3.Connection) -> None:
    assert fetch_chat_names(msgstore_conn, []) == []
