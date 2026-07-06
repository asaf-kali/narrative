import sqlite3

from seed_data import T0, local_date

from narrative.db.queries.stats import fetch_daily_counts


def test_fetch_daily_counts_excludes_system(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_daily_counts(msgstore_conn)
    total = sum(r["count"] for r in rows)
    assert total == 8


def test_fetch_daily_counts_grouped_by_local_day(msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_daily_counts(msgstore_conn)
    assert len(rows) == 1
    assert rows[0]["day"] == local_date(T0)
