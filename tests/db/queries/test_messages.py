import sqlite3

from seed_data import (
    ALICE_PHONE,
    CHAT_BROADCAST,
    CHAT_DIRECT,
    CHAT_GROUP,
    MSG_BOB_GROUP_HELLO,
    MSG_CAROL_GROUP_HELLO,
    T0,
)

from narrative.db.queries.messages import (
    count_filtered_messages,
    count_messages,
    count_messages_for_chat,
    fetch_all_messages,
    fetch_distinct_chat_ids,
    fetch_distinct_sender_ids,
    fetch_index_rows_paged,
    fetch_message_bounds,
    fetch_messages_for_chat,
    fetch_messages_for_chat_paged,
    fetch_messages_metadata,
    fetch_messages_page,
    fetch_sender_counts,
    get_max_message_id_for_chat,
)


def test_fetch_messages_page_excludes_system_by_default(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_messages_page(msgstore_conn, chat_id=CHAT_DIRECT)
    assert len(rows) == 3
    assert all(r.message_type != 7 for r in rows)


def test_fetch_messages_page_includes_system_when_disabled(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_messages_page(msgstore_conn, chat_id=CHAT_DIRECT, exclude_system=False)
    assert len(rows) == 4


def test_fetch_messages_page_sort_asc_vs_desc(msgstore_conn: sqlite3.Connection) -> None:
    asc = fetch_messages_page(msgstore_conn, chat_id=CHAT_GROUP, sort_asc=True)
    desc = fetch_messages_page(msgstore_conn, chat_id=CHAT_GROUP, sort_asc=False)
    assert [r.message_id for r in asc] == list(reversed([r.message_id for r in desc]))


def test_fetch_messages_page_pagination(msgstore_conn: sqlite3.Connection) -> None:
    page1 = fetch_messages_page(msgstore_conn, chat_id=CHAT_GROUP, sort_asc=True, limit=2, offset=0)
    page2 = fetch_messages_page(msgstore_conn, chat_id=CHAT_GROUP, sort_asc=True, limit=2, offset=2)
    assert [r.message_id for r in page1] == [5, 6]
    assert [r.message_id for r in page2] == [7, 8]


def test_fetch_messages_page_search_filters_text(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_messages_page(msgstore_conn, search="carol")
    assert len(rows) == 1
    text = rows[0].text_data
    assert text is not None
    assert "carol" in text.lower()


def test_fetch_messages_page_date_range_filters(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_messages_page(msgstore_conn, date_from_ms=T0 + 15_000, date_to_ms=T0 + 25_000)
    assert {r.message_id for r in rows} == {MSG_CAROL_GROUP_HELLO}


def test_fetch_messages_page_sender_ids_filters_by_case_expression(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_messages_page(msgstore_conn, sender_ids=["me"])
    assert all(r.from_me == 1 for r in rows)
    assert len(rows) == 3  # msg2, msg7, msg9


def test_fetch_messages_page_chat_ids_filters_multiple(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_messages_page(msgstore_conn, chat_ids=[CHAT_DIRECT, CHAT_GROUP])
    assert all(r.chat_row_id in {CHAT_DIRECT, CHAT_GROUP} for r in rows)


def test_count_filtered_messages_matches_page_length(msgstore_conn: sqlite3.Connection) -> None:
    count = count_filtered_messages(msgstore_conn, chat_id=CHAT_GROUP)
    rows = fetch_messages_page(msgstore_conn, chat_id=CHAT_GROUP, limit=1000)
    assert count == len(rows)


def test_fetch_distinct_chat_ids(msgstore_conn: sqlite3.Connection) -> None:
    ids = fetch_distinct_chat_ids(msgstore_conn)
    assert set(ids) == {CHAT_DIRECT, CHAT_GROUP, CHAT_BROADCAST}


def test_fetch_distinct_sender_ids_includes_me_and_phones(msgstore_conn: sqlite3.Connection) -> None:
    ids = fetch_distinct_sender_ids(msgstore_conn)
    assert "me" in ids
    assert ALICE_PHONE in ids


def test_fetch_messages_metadata_totals(msgstore_conn: sqlite3.Connection) -> None:
    meta = fetch_messages_metadata(msgstore_conn, chat_id=CHAT_GROUP)
    assert meta.total == 4
    assert meta.available_chat_ids == []  # chat_id given => no cross-chat listing


def test_fetch_messages_metadata_global_lists_chats(msgstore_conn: sqlite3.Connection) -> None:
    meta = fetch_messages_metadata(msgstore_conn)
    assert meta.available_chat_ids == [CHAT_DIRECT, CHAT_GROUP, CHAT_BROADCAST]


def test_fetch_all_messages_excludes_system(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(fetch_all_messages(msgstore_conn))
    assert all(r.message_type != 7 for r in rows)
    assert len(rows) == 8


def test_fetch_messages_for_chat_scopes_to_chat(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(fetch_messages_for_chat(msgstore_conn, chat_id=CHAT_DIRECT))
    assert all(r.chat_row_id == CHAT_DIRECT for r in rows)
    assert len(rows) == 3


def test_fetch_sender_counts_groups_by_sender(msgstore_conn: sqlite3.Connection) -> None:
    counts = fetch_sender_counts(msgstore_conn)
    me_row = next(r for r in counts if r.sender_id == "me")
    assert me_row.message_count == 3


def test_fetch_sender_counts_filters_by_sender_ids(msgstore_conn: sqlite3.Connection) -> None:
    counts = fetch_sender_counts(msgstore_conn, sender_ids={"me"})
    assert len(counts) == 1
    assert counts[0].sender_id == "me"


def test_fetch_message_bounds_global(msgstore_conn: sqlite3.Connection) -> None:
    bounds = fetch_message_bounds(msgstore_conn)
    assert bounds is not None
    lo, hi = bounds
    assert lo <= hi


def test_fetch_message_bounds_per_chat(msgstore_conn: sqlite3.Connection) -> None:
    bounds = fetch_message_bounds(msgstore_conn, chat_id=CHAT_DIRECT)
    assert bounds == (T0, T0 + 120_000)  # system msg (T0+180000) excluded


def test_fetch_message_bounds_none_for_empty_chat(msgstore_conn: sqlite3.Connection) -> None:
    assert fetch_message_bounds(msgstore_conn, chat_id=999) is None


def test_count_messages_excludes_system(msgstore_conn: sqlite3.Connection) -> None:
    assert count_messages(msgstore_conn) == 8


def test_count_messages_for_chat_respects_after_id(msgstore_conn: sqlite3.Connection) -> None:
    assert count_messages_for_chat(msgstore_conn, chat_id=CHAT_GROUP, after_id=MSG_BOB_GROUP_HELLO) == 3


def test_get_max_message_id_for_chat(msgstore_conn: sqlite3.Connection) -> None:
    assert get_max_message_id_for_chat(msgstore_conn, chat_id=CHAT_GROUP) == 8


def test_get_max_message_id_for_chat_no_messages_returns_zero(msgstore_conn: sqlite3.Connection) -> None:
    assert get_max_message_id_for_chat(msgstore_conn, chat_id=999) == 0


def test_fetch_messages_for_chat_paged(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_messages_for_chat_paged(msgstore_conn, chat_id=CHAT_GROUP, after_id=0, limit=2)
    assert [r.message_id for r in rows] == [MSG_BOB_GROUP_HELLO, MSG_BOB_GROUP_HELLO + 1]


def test_fetch_index_rows_paged_returns_raw_rows(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_index_rows_paged(msgstore_conn, chat_id=CHAT_GROUP, after_id=0, limit=100)
    assert len(rows) == 4
    assert rows[0]["message_id"] == MSG_BOB_GROUP_HELLO


def test_fetch_index_rows_paged_includes_system_messages(msgstore_conn: sqlite3.Connection) -> None:
    """Unlike other message queries this one does not filter message_type=7 in SQL — caller filters."""
    rows = fetch_index_rows_paged(msgstore_conn, chat_id=CHAT_DIRECT, after_id=0, limit=100)
    assert any(r["message_type"] == 7 for r in rows)


def test_fetch_messages_page_returns_empty_for_missing_chat(msgstore_conn: sqlite3.Connection) -> None:
    assert fetch_messages_page(msgstore_conn, chat_id=999) == []
