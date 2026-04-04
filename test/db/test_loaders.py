import sqlite3
from datetime import UTC
from unittest import mock

import pytest
from db.loaders import DataLoader
from models.config import AnalysisConfig
from models.message import MessageType


@pytest.fixture
def mock_db(in_memory_msgstore: sqlite3.Connection) -> mock.MagicMock:
    db = mock.MagicMock()
    db.msgstore = in_memory_msgstore
    db.wadb = None
    return db


def test_load_chats_returns_list(mock_db: mock.MagicMock) -> None:
    loader = DataLoader(mock_db)
    chats = loader.load_chats()
    assert len(chats) == 2


def test_load_chats_have_display_names(mock_db: mock.MagicMock) -> None:
    loader = DataLoader(mock_db)
    chats = loader.load_chats()
    names = {c.display_name for c in chats}
    assert "Family Group" in names


def test_load_messages_returns_df(mock_db: mock.MagicMock) -> None:
    loader = DataLoader(mock_db)
    config = AnalysisConfig(chat_id=1)
    df = loader.load_messages(config)
    assert not df.empty
    assert "sender_name" in df.columns
    assert "timestamp" in df.columns


def test_load_messages_filters_by_chat(mock_db: mock.MagicMock) -> None:
    loader = DataLoader(mock_db)
    df_chat1 = loader.load_messages(AnalysisConfig(chat_id=1))
    df_chat2 = loader.load_messages(AnalysisConfig(chat_id=2))
    assert len(df_chat1) != len(df_chat2)
    assert all(df_chat1["chat_row_id"] == 1)
    assert all(df_chat2["chat_row_id"] == 2)


def test_load_messages_excludes_system_by_default(mock_db: mock.MagicMock) -> None:
    # Seed a system message (type 7)
    conn: sqlite3.Connection = mock_db.msgstore
    conn.execute(
        "INSERT INTO message (_id, chat_row_id, from_me, timestamp, message_type, text_data, sender_jid_row_id) "
        "VALUES (99, 1, 0, 1704067200000, 7, 'Group notification', 1)"
    )
    conn.commit()

    loader = DataLoader(mock_db)
    df = loader.load_messages(AnalysisConfig(chat_id=1, exclude_system=True))
    assert MessageType.SYSTEM not in df["message_type"].to_numpy()


def test_load_messages_date_filter(mock_db: mock.MagicMock) -> None:
    from datetime import datetime  # noqa: PLC0415

    loader = DataLoader(mock_db)
    config = AnalysisConfig(
        chat_id=1,
        date_from=datetime(2025, 1, 1, tzinfo=UTC),
    )
    df = loader.load_messages(config)
    # All seed data is from 2024, so result should be empty
    assert df.empty


def test_load_messages_no_chat_filter_loads_all(mock_db: mock.MagicMock) -> None:
    loader = DataLoader(mock_db)
    df = loader.load_messages(AnalysisConfig())
    assert len(df) > 4


def test_contact_names_from_wadb(in_memory_msgstore: sqlite3.Connection) -> None:
    wadb = sqlite3.connect(":memory:")
    wadb.row_factory = sqlite3.Row
    wadb.execute("CREATE TABLE wa_contacts (jid TEXT, display_name TEXT)")
    wadb.execute("INSERT INTO wa_contacts VALUES ('972501234567@s.whatsapp.net', 'Alice')")
    wadb.commit()

    db = mock.MagicMock()
    db.msgstore = in_memory_msgstore
    db.wadb = wadb

    loader = DataLoader(db)
    names = loader.load_contact_names()
    assert names.get("972501234567") == "Alice"
