import sqlite3
from pathlib import Path

from seed_data import SeededPaths, build_schema

from narrative.db.indexes import INDEXES, ensure_indexes


def test_ensure_indexes_creates_all_indexes(seeded_db_paths: SeededPaths) -> None:
    ensure_indexes(msgstore_path=seeded_db_paths.msgstore)
    names = _index_names(path=seeded_db_paths.msgstore)
    assert {spec.name for spec in INDEXES} <= names


def test_ensure_indexes_is_idempotent(seeded_db_paths: SeededPaths) -> None:
    ensure_indexes(msgstore_path=seeded_db_paths.msgstore)
    ensure_indexes(msgstore_path=seeded_db_paths.msgstore)
    names = _index_names(path=seeded_db_paths.msgstore)
    assert {spec.name for spec in INDEXES} <= names


def test_ensure_indexes_skips_missing_tables(tmp_path: Path) -> None:
    path = tmp_path / "partial.db"
    conn = sqlite3.connect(path)
    build_schema(conn)
    conn.execute("DROP TABLE message_quoted")
    conn.close()
    ensure_indexes(msgstore_path=path)
    names = _index_names(path=path)
    assert "narrative_message_ts" in names
    assert "narrative_quoted_chat" not in names


def test_ensure_indexes_on_read_only_file_does_not_raise(seeded_db_paths: SeededPaths) -> None:
    seeded_db_paths.msgstore.chmod(0o444)
    try:
        ensure_indexes(msgstore_path=seeded_db_paths.msgstore)
    finally:
        seeded_db_paths.msgstore.chmod(0o644)
    assert "narrative_message_ts" not in _index_names(path=seeded_db_paths.msgstore)


def _index_names(path: Path) -> set[str]:
    conn = sqlite3.connect(path)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    conn.close()
    return {row[0] for row in rows}
