import sqlite3
from pathlib import Path

from db.queries.calls import fetch_calls
from seed_data import ALICE_PHONE


def test_fetch_calls_returns_row(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(fetch_calls(msgstore_conn))
    assert len(rows) == 1
    assert rows[0].caller_phone == ALICE_PHONE
    assert rows[0].duration == 120


def test_fetch_calls_missing_table_returns_empty(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "no_calls.db")
    conn.row_factory = sqlite3.Row
    assert list(fetch_calls(conn)) == []
    conn.close()
