import sqlite3

from seed_data import T0, local_date

from narrative.db.queries.day import fetch_day_messages


def test_fetch_day_messages_returns_non_system_messages_for_date(msgstore_conn: sqlite3.Connection) -> None:
    date = local_date(T0)
    rows = list(fetch_day_messages(msgstore_conn, date))
    assert len(rows) == 8  # all non-system messages fall on the same local day
    assert all(r.message_type != 7 for r in rows)


def test_fetch_day_messages_sorted_ascending(msgstore_conn: sqlite3.Connection) -> None:
    date = local_date(T0)
    rows = list(fetch_day_messages(msgstore_conn, date))
    timestamps = [r.timestamp for r in rows]
    assert timestamps == sorted(timestamps)


def test_fetch_day_messages_empty_for_other_date(msgstore_conn: sqlite3.Connection) -> None:
    assert list(fetch_day_messages(msgstore_conn, "1999-01-01")) == []
