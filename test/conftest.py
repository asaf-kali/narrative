import sqlite3
from datetime import UTC, datetime

import pandas as pd
import pytest


@pytest.fixture
def in_memory_msgstore() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_schema(conn)
    _seed_data(conn)
    return conn


@pytest.fixture
def sample_messages_df() -> pd.DataFrame:
    now = datetime.now(tz=UTC)
    rows = [
        {
            "message_id": 1,
            "chat_row_id": 1,
            "from_me": 0,
            "timestamp": pd.Timestamp(now),
            "received_timestamp": None,
            "message_type": 0,
            "text_data": "Hello how are you doing today",
            "starred": 0,
            "quoted_row_id": None,
            "sender_phone": "972501234567",
            "sender_name": "Alice",
            "chat_name": "Family",
            "is_group": True,
            "day_of_week": now.strftime("%A"),
            "hour": now.hour,
            "date": now.date(),
            "year": now.year,
            "month": now.strftime("%Y-%m"),
        },
        {
            "message_id": 2,
            "chat_row_id": 1,
            "from_me": 1,
            "timestamp": pd.Timestamp(now),
            "received_timestamp": None,
            "message_type": 0,
            "text_data": "I am doing great thanks for asking",
            "starred": 0,
            "quoted_row_id": None,
            "sender_phone": "",
            "sender_name": "Me",
            "chat_name": "Family",
            "is_group": True,
            "day_of_week": now.strftime("%A"),
            "hour": now.hour,
            "date": now.date(),
            "year": now.year,
            "month": now.strftime("%Y-%m"),
        },
        {
            "message_id": 3,
            "chat_row_id": 1,
            "from_me": 0,
            "timestamp": pd.Timestamp(now),
            "received_timestamp": None,
            "message_type": 1,
            "text_data": None,
            "starred": 0,
            "quoted_row_id": None,
            "sender_phone": "972507654321",
            "sender_name": "Bob",
            "chat_name": "Family",
            "is_group": True,
            "day_of_week": now.strftime("%A"),
            "hour": now.hour,
            "date": now.date(),
            "year": now.year,
            "month": now.strftime("%Y-%m"),
        },
        {
            "message_id": 4,
            "chat_row_id": 1,
            "from_me": 0,
            "timestamp": pd.Timestamp(now),
            "received_timestamp": None,
            "message_type": 0,
            "text_data": "Nice photo Bob love it",
            "starred": 0,
            "quoted_row_id": None,
            "sender_phone": "972501234567",
            "sender_name": "Alice",
            "chat_name": "Family",
            "is_group": True,
            "day_of_week": now.strftime("%A"),
            "hour": now.hour,
            "date": now.date(),
            "year": now.year,
            "month": now.strftime("%Y-%m"),
        },
    ]
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jid (
            _id INTEGER PRIMARY KEY,
            user TEXT,
            server TEXT DEFAULT 's.whatsapp.net',
            type INTEGER DEFAULT 0,
            raw_string TEXT
        );
        CREATE TABLE IF NOT EXISTS chat (
            _id INTEGER PRIMARY KEY,
            jid_row_id INTEGER,
            subject TEXT,
            created_timestamp INTEGER
        );
        CREATE TABLE IF NOT EXISTS message (
            _id INTEGER PRIMARY KEY,
            chat_row_id INTEGER,
            from_me INTEGER,
            timestamp INTEGER,
            received_timestamp INTEGER,
            message_type INTEGER DEFAULT 0,
            text_data TEXT,
            starred INTEGER DEFAULT 0,
            quoted_row_id INTEGER,
            sender_jid_row_id INTEGER
        );
    """)


def _seed_data(conn: sqlite3.Connection) -> None:
    base_ts = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
    day_ms = 86_400_000

    conn.executemany(
        "INSERT INTO jid (_id, user, server) VALUES (?, ?, ?)",
        [
            (1, "972501234567", "s.whatsapp.net"),
            (2, "972507654321", "s.whatsapp.net"),
            (3, "group123", "g.us"),
        ],
    )
    conn.executemany(
        "INSERT INTO chat (_id, jid_row_id, subject) VALUES (?, ?, ?)",
        [
            (1, 3, "Family Group"),
            (2, 1, None),
        ],
    )
    messages = [
        (1, 1, 0, base_ts + 0 * day_ms, 0, "Good morning everyone", 1),
        (2, 1, 1, base_ts + 1 * day_ms, 1, "Morning! How is everyone?", 2),
        (3, 1, 0, base_ts + 2 * day_ms, 1, None, 1),  # image
        (4, 1, 0, base_ts + 3 * day_ms, 1, "Check this out", 2),
        (5, 2, 0, base_ts + 4 * day_ms, 0, "Hey just you and me", 1),
        (6, 2, 1, base_ts + 5 * day_ms, 0, "Yeah let us catch up", None),
    ]
    for msg_id, chat_id, from_me, ts, msg_type, text, sender_jid_id in messages:
        conn.execute(
            "INSERT INTO message (_id, chat_row_id, from_me, timestamp, message_type, text_data, sender_jid_row_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg_id, chat_id, from_me, ts, msg_type, text, sender_jid_id),
        )
    conn.commit()
