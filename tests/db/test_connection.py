import sqlite3
from pathlib import Path

import pytest
from seed_data import SCHEMA_SQL, seed_msgstore

from narrative.db.connection import DBConnection


def test_msgstore_property_raises_before_open(tmp_path: Path) -> None:
    db = DBConnection(msgstore_path=tmp_path / "msgstore.db")
    with pytest.raises(RuntimeError, match="not opened"):
        _ = db.msgstore


def test_wadb_property_none_before_open(tmp_path: Path) -> None:
    db = DBConnection(msgstore_path=tmp_path / "msgstore.db")
    assert db.wadb is None


def test_context_manager_opens_and_closes_msgstore(tmp_path: Path) -> None:
    msgstore_path = tmp_path / "msgstore.db"
    conn = sqlite3.connect(msgstore_path)
    conn.executescript(SCHEMA_SQL)
    seed_msgstore(conn)
    conn.close()

    db = DBConnection(msgstore_path=msgstore_path)
    with db as opened:
        assert opened.msgstore is not None
        row = opened.msgstore.execute("SELECT COUNT(*) FROM message").fetchone()
        assert row[0] == 9
    with pytest.raises(RuntimeError, match="not opened"):
        _ = db.msgstore


def test_wadb_absent_when_path_not_provided(tmp_path: Path) -> None:
    msgstore_path = tmp_path / "msgstore.db"
    sqlite3.connect(msgstore_path).close()

    with DBConnection(msgstore_path=msgstore_path) as db:
        assert db.wadb is None


def test_wadb_absent_when_file_missing(tmp_path: Path) -> None:
    msgstore_path = tmp_path / "msgstore.db"
    sqlite3.connect(msgstore_path).close()
    missing_wadb = tmp_path / "wa.db"  # never created

    with DBConnection(msgstore_path=msgstore_path, wadb_path=missing_wadb) as db:
        assert db.wadb is None


def test_wadb_opened_when_file_exists(tmp_path: Path) -> None:
    msgstore_path = tmp_path / "msgstore.db"
    wadb_path = tmp_path / "wa.db"
    sqlite3.connect(msgstore_path).close()
    sqlite3.connect(wadb_path).close()

    with DBConnection(msgstore_path=msgstore_path, wadb_path=wadb_path) as db:
        assert db.wadb is not None
