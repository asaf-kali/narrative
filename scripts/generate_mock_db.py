#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["faker>=24", "typer>=0.12"]
# ///
"""Generate mock msgstore.db, wa.db, and contacts.csv for testing.

Usage:
    uv run scripts/generate_mock_db.py [--out-dir data/mock]
"""

import csv
import random
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

import typer
from faker import Faker

fake = Faker("en_US")
Faker.seed(1337)
random.seed(1337)

USER_SERVER = "s.whatsapp.net"
GROUP_SERVER = "g.us"

N_CONTACTS = 20
N_DIRECT_CHATS = 12
N_GROUPS = 4
N_MESSAGES = 4000

_FROM_ME_PROBABILITY = 0.35

# Timestamp range: last 3 years
_NOW_MS = int(datetime.now(tz=UTC).timestamp() * 1000)
_THREE_YEARS_MS = 3 * 365 * 24 * 3600 * 1000
_START_MS = _NOW_MS - _THREE_YEARS_MS

MESSAGE_TYPE_WEIGHTS = [
    (0, 80),  # text
    (1, 8),  # image
    (2, 5),  # audio
    (3, 3),  # video
    (9, 3),  # document
    (13, 1),  # sticker
]
_MSG_TYPE_POPULATION = [t for t, w in MESSAGE_TYPE_WEIGHTS for _ in range(w)]

_TEXT_POOL: list[str] = [fake.sentence() for _ in range(200)]


class Contact(TypedDict):
    phone: str
    name: str


ChatEntry = tuple[int, list[str], bool]
MessageRow = tuple[int, int, int, int, int, str | None, int, int | None]


def _random_ms_timestamp(start: int = _START_MS, end: int = _NOW_MS) -> int:
    return random.randint(start, end)  # noqa: S311


def _phone() -> str:
    return fake.numerify("1##########")


def _group_jid_user() -> str:
    return fake.numerify("####################") + "-" + fake.numerify("##########")


def _make_contacts(n: int) -> list[Contact]:
    seen_phones: set[str] = set()
    contacts: list[Contact] = []
    while len(contacts) < n:
        phone = _phone()
        if phone in seen_phones:
            continue
        seen_phones.add(phone)
        contacts.append({"phone": phone, "name": fake.name()})
    return contacts


def _create_msgstore_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jid (
            _id     INTEGER PRIMARY KEY AUTOINCREMENT,
            user    TEXT NOT NULL,
            server  TEXT NOT NULL,
            type    INTEGER DEFAULT 0,
            UNIQUE (user, server)
        );

        CREATE TABLE IF NOT EXISTS jid_map (
            lid_row_id  INTEGER NOT NULL,
            jid_row_id  INTEGER NOT NULL,
            PRIMARY KEY (lid_row_id)
        );

        CREATE TABLE IF NOT EXISTS chat (
            _id               INTEGER PRIMARY KEY AUTOINCREMENT,
            jid_row_id        INTEGER NOT NULL,
            subject           TEXT,
            created_timestamp INTEGER
        );

        CREATE TABLE IF NOT EXISTS message (
            _id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_row_id         INTEGER NOT NULL,
            from_me             INTEGER NOT NULL DEFAULT 0,
            timestamp           INTEGER NOT NULL,
            received_timestamp  INTEGER NOT NULL DEFAULT 0,
            message_type        INTEGER NOT NULL DEFAULT 0,
            text_data           TEXT,
            starred             INTEGER NOT NULL DEFAULT 0,
            sender_jid_row_id   INTEGER
        );

        CREATE INDEX IF NOT EXISTS message_chat_ts ON message (chat_row_id, timestamp);
        CREATE INDEX IF NOT EXISTS message_ts ON message (timestamp);
    """)


def _create_wadb_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS wa_contacts (
            jid          TEXT PRIMARY KEY,
            display_name TEXT
        );
    """)


def _insert_jid(conn: sqlite3.Connection, user: str, server: str, jid_type: int = 0) -> int:
    cur = conn.execute(
        "INSERT OR IGNORE INTO jid (user, server, type) VALUES (?, ?, ?)",
        (user, server, jid_type),
    )
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute("SELECT _id FROM jid WHERE user = ? AND server = ?", (user, server)).fetchone()
    return int(row[0])


def _populate_contacts(
    contacts: list[Contact],
    msgstore: sqlite3.Connection,
    wadb: sqlite3.Connection,
) -> dict[str, int]:
    contact_jid_ids: dict[str, int] = {}
    for c in contacts:
        jid_id = _insert_jid(msgstore, c["phone"], USER_SERVER)
        contact_jid_ids[c["phone"]] = jid_id
        wadb.execute(
            "INSERT OR IGNORE INTO wa_contacts (jid, display_name) VALUES (?, ?)",
            (f"{c['phone']}@{USER_SERVER}", c["name"]),
        )
    return contact_jid_ids


def _populate_direct_chats(
    contacts: list[Contact],
    contact_jid_ids: dict[str, int],
    msgstore: sqlite3.Connection,
) -> list[ChatEntry]:
    phones = [c["phone"] for c in contacts]
    direct_phones = random.sample(phones, min(N_DIRECT_CHATS, len(contacts)))
    chat_ids: list[ChatEntry] = []
    for phone in direct_phones:
        jid_id = contact_jid_ids[phone]
        cur = msgstore.execute("INSERT INTO chat (jid_row_id, subject) VALUES (?, NULL)", (jid_id,))
        assert cur.lastrowid is not None  # noqa: S101
        chat_ids.append((cur.lastrowid, [phone], False))
    return chat_ids


def _populate_groups(
    contacts: list[Contact],
    msgstore: sqlite3.Connection,
) -> list[ChatEntry]:
    chat_ids: list[ChatEntry] = []
    group_names = [fake.bs().title() for _ in range(N_GROUPS)]
    all_phones = [c["phone"] for c in contacts]
    for group_name in group_names:
        group_user = _group_jid_user()
        group_jid_id = _insert_jid(msgstore, group_user, GROUP_SERVER)
        cur = msgstore.execute(
            "INSERT INTO chat (jid_row_id, subject) VALUES (?, ?)",
            (group_jid_id, group_name),
        )
        assert cur.lastrowid is not None  # noqa: S101
        n_members = random.randint(4, min(10, len(contacts)))  # noqa: S311
        members = random.sample(all_phones, n_members)
        chat_ids.append((cur.lastrowid, members, True))
    return chat_ids


def _generate_messages(
    chat_ids: list[ChatEntry],
    contact_jid_ids: dict[str, int],
) -> list[MessageRow]:
    messages: list[MessageRow] = []
    for _ in range(N_MESSAGES):
        chat_db_id, participants, is_group = random.choice(chat_ids)  # noqa: S311
        msg_type = random.choice(_MSG_TYPE_POPULATION)  # noqa: S311
        ts = _random_ms_timestamp()
        received_ts = ts + random.randint(500, 5000) if msg_type == 0 else 0  # noqa: S311
        text = random.choice(_TEXT_POOL) if msg_type == 0 else None  # noqa: S311

        from_me = random.random() < _FROM_ME_PROBABILITY  # noqa: S311
        if from_me:
            sender_jid_row_id = None
        elif is_group:
            sender_phone = random.choice(participants)  # noqa: S311
            sender_jid_row_id = contact_jid_ids[sender_phone]
        else:
            sender_jid_row_id = contact_jid_ids[participants[0]]

        messages.append((chat_db_id, int(from_me), ts, received_ts, msg_type, text, 0, sender_jid_row_id))

    messages.sort(key=lambda r: r[2])
    return messages


def main(out_dir: Path = typer.Argument(Path("data/mock"))) -> None:  # noqa: B008
    out_dir.mkdir(parents=True, exist_ok=True)
    msgstore_path = out_dir / "msgstore.db"
    wadb_path = out_dir / "wa.db"
    contacts_csv_path = out_dir / "contacts.csv"

    for p in (msgstore_path, wadb_path):
        if p.exists():
            p.unlink()

    contacts = _make_contacts(N_CONTACTS)
    me_phone = _phone()
    while me_phone in {c["phone"] for c in contacts}:
        me_phone = _phone()

    msgstore = sqlite3.connect(msgstore_path)
    wadb = sqlite3.connect(wadb_path)
    _create_msgstore_schema(msgstore)
    _create_wadb_schema(wadb)

    contact_jid_ids = _populate_contacts(contacts, msgstore, wadb)
    direct_chats = _populate_direct_chats(contacts, contact_jid_ids, msgstore)
    group_chats = _populate_groups(contacts, msgstore)
    all_chats = direct_chats + group_chats

    messages = _generate_messages(all_chats, contact_jid_ids)
    msgstore.executemany(
        "INSERT INTO message "
        "(chat_row_id, from_me, timestamp, received_timestamp, message_type, text_data, starred, sender_jid_row_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        messages,
    )

    msgstore.commit()
    wadb.commit()
    msgstore.close()
    wadb.close()

    with contacts_csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["phone", "name"])
        writer.writeheader()
        writer.writerows(contacts)


if __name__ == "__main__":
    typer.run(main)
