import sqlite3
from datetime import UTC, datetime

from seed_data import T0

from narrative.db.queries.range import fetch_range_messages


def test_fetch_range_messages_inclusive_bounds(msgstore_conn: sqlite3.Connection) -> None:
    date_from = datetime.fromtimestamp(T0 / 1000, tz=UTC)
    date_to = datetime.fromtimestamp((T0 + 60_000) / 1000, tz=UTC)
    rows = list(fetch_range_messages(msgstore_conn, date_from, date_to))
    ids = {r.timestamp for r in rows}
    assert T0 in ids
    assert T0 + 60_000 in ids


def test_fetch_range_messages_excludes_system(msgstore_conn: sqlite3.Connection) -> None:
    date_from = datetime.fromtimestamp(0, tz=UTC)
    date_to = datetime.fromtimestamp((T0 + 200_000) / 1000, tz=UTC)
    rows = list(fetch_range_messages(msgstore_conn, date_from, date_to))
    assert all(r.message_type != 7 for r in rows)


def test_fetch_range_messages_outside_window_excluded(msgstore_conn: sqlite3.Connection) -> None:
    date_from = datetime.fromtimestamp((T0 + 1_000_000) / 1000, tz=UTC)
    date_to = datetime.fromtimestamp((T0 + 2_000_000) / 1000, tz=UTC)
    assert list(fetch_range_messages(msgstore_conn, date_from, date_to)) == []
