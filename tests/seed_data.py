"""Deterministic WhatsApp-schema seed data shared by every backend test.

Builds a minimal but representative slice of a real msgstore.db / wa.db: one
direct chat, one group (with an LID-mapped sender), one broadcast, reactions,
a reply, a call, and a system message. Every test module that needs concrete
IDs/values imports the constants below instead of re-deriving them.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class SeededPaths:
    msgstore: Path
    wadb: Path


SCHEMA_SQL = """
CREATE TABLE jid (
    _id INTEGER PRIMARY KEY,
    user TEXT,
    server TEXT,
    type INTEGER
);

CREATE TABLE jid_map (
    lid_row_id INTEGER,
    jid_row_id INTEGER
);

CREATE TABLE chat (
    _id INTEGER PRIMARY KEY,
    jid_row_id INTEGER,
    subject TEXT,
    created_timestamp INTEGER
);

CREATE TABLE message (
    _id INTEGER PRIMARY KEY,
    chat_row_id INTEGER,
    from_me INTEGER,
    timestamp INTEGER,
    received_timestamp INTEGER,
    message_type INTEGER,
    text_data TEXT,
    starred INTEGER,
    sender_jid_row_id INTEGER,
    key_id TEXT
);

CREATE TABLE message_add_on (
    _id INTEGER PRIMARY KEY,
    parent_message_row_id INTEGER,
    chat_row_id INTEGER,
    from_me INTEGER,
    sender_jid_row_id INTEGER,
    timestamp INTEGER,
    message_add_on_type INTEGER
);

CREATE TABLE message_add_on_reaction (
    message_add_on_row_id INTEGER,
    reaction TEXT
);

CREATE TABLE message_quoted (
    message_row_id INTEGER,
    key_id TEXT,
    chat_row_id INTEGER,
    from_me INTEGER,
    message_type INTEGER,
    text_data TEXT,
    sender_jid_row_id INTEGER,
    parent_message_chat_row_id INTEGER,
    timestamp INTEGER
);

CREATE TABLE message_vcard (
    _id INTEGER PRIMARY KEY,
    message_row_id INTEGER,
    vcard TEXT
);

CREATE TABLE message_location (
    message_row_id INTEGER,
    chat_row_id INTEGER,
    latitude REAL,
    longitude REAL,
    place_name TEXT,
    place_address TEXT,
    live_location_share_duration INTEGER,
    live_location_final_latitude REAL,
    live_location_final_longitude REAL
);

CREATE TABLE message_poll (
    message_row_id INTEGER,
    selectable_options_count INTEGER
);

CREATE TABLE message_poll_option (
    _id INTEGER PRIMARY KEY,
    message_row_id INTEGER,
    option_name TEXT,
    vote_total INTEGER
);

CREATE TABLE call_log (
    _id INTEGER PRIMARY KEY,
    timestamp INTEGER,
    call_result INTEGER,
    duration INTEGER,
    video_call INTEGER,
    from_me INTEGER,
    jid_row_id INTEGER
);
"""

WA_SCHEMA_SQL = """
CREATE TABLE wa_contacts (
    jid TEXT,
    display_name TEXT
);
"""

# Reference instant; all message timestamps are offsets (ms) from this.
T0 = int(datetime(2024, 1, 10, 9, 0, 0, tzinfo=UTC).timestamp() * 1000)

# jid._id values
JID_ALICE = 1  # direct-chat partner, resolved via wa_contacts
JID_BOB_PHONE = 2  # group member, resolved via wa_contacts through LID
JID_BOB_LID = 3  # Bob's LID jid used as message sender in the group
JID_CAROL = 4  # group member with a plain (non-LID) phone jid
JID_GROUP = 5
JID_BROADCAST = 6

ALICE_PHONE = "111111111"
BOB_PHONE = "222222222"
CAROL_PHONE = "333333333"

ALICE_NAME = "Alice Wonderland"
BOB_NAME = "Bob Marley"
CAROL_NAME = "Carol Danvers"

# chat._id values
CHAT_DIRECT = 1
CHAT_GROUP = 2
CHAT_BROADCAST = 3
GROUP_SUBJECT = "Test Group"

# message._id values
MSG_ALICE_HELLO = 1
MSG_ME_REPLY_ALICE = 2
MSG_ALICE_IMAGE = 3
MSG_SYSTEM = 4
MSG_BOB_GROUP_HELLO = 5
MSG_CAROL_GROUP_HELLO = 6
MSG_ME_GROUP = 7
MSG_BOB_GROUP_AUDIO = 8
MSG_BROADCAST = 9
MSG_ALICE_CONTACT = 10  # single shared contact (message_type 4)
MSG_ME_CONTACTS = 11  # multi-contact message (message_type 14) with two vCards
MSG_ALICE_LOCATION = 12  # static pin with a place name (message_type 5)
MSG_ME_LIVE_LOCATION = 13  # live location share that moved (message_type 16)
MSG_ALICE_POLL = 14  # single-choice poll (message_type 66)

CAROL_GROUP_TEXT = "group hello from carol \U0001f600"  # includes 😀 for emoji tests
SYSTEM_TEXT = "Messages are end-to-end encrypted"

DAVE_NAME = "Dave Grohl"
DAVE_PHONE = "+1 555-0100"
ERIN_NAME = "Erin Brockovich"
ERIN_PHONES = ("+1 555-0200", "+1 555-0201")
FRANK_NAME = "Frank Ocean"
MULTI_CONTACT_TEXT = "2 contacts"

DAVE_VCARD = (
    f"BEGIN:VCARD\nVERSION:3.0\nN:Grohl;Dave;;;\nFN:{DAVE_NAME}\nitem1.TEL;waid=15550100:{DAVE_PHONE}\nEND:VCARD"
)
ERIN_VCARD = (
    f"BEGIN:VCARD\nVERSION:3.0\nFN:{ERIN_NAME}\n"
    f"TEL;type=CELL:{ERIN_PHONES[0]}\nTEL;type=WORK:{ERIN_PHONES[1]}\nEND:VCARD"
)
FRANK_VCARD = f"BEGIN:VCARD\nVERSION:3.0\nFN:{FRANK_NAME}\nEND:VCARD"

PLACE_NAME = "Blue Bottle Coffee"
PLACE_ADDRESS = "1 Ferry Building, San Francisco"
PLACE_LAT, PLACE_LON = 37.7955, -122.3937
LIVE_START_LAT, LIVE_START_LON = 32.0853, 34.7818
LIVE_FINAL_LAT, LIVE_FINAL_LON = 32.1093, 34.8555

POLL_QUESTION = "Lunch where?"
POLL_OPTIONS = (("Pizza", 2), ("Sushi", 0))

REACTION_ON_BOB_MSG = "\U0001f44d"  # 👍, given by me
REACTION_ON_CAROL_MSG = "❤️"  # ❤️, given by Bob


def build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)


def build_wa_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(WA_SCHEMA_SQL)


def seed_msgstore(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO jid (_id, user, server, type) VALUES (?, ?, ?, ?)",
        [
            (JID_ALICE, ALICE_PHONE, "s.whatsapp.net", 0),
            (JID_BOB_PHONE, BOB_PHONE, "s.whatsapp.net", 0),
            (JID_BOB_LID, "bobslid1", "lid", 0),
            (JID_CAROL, CAROL_PHONE, "s.whatsapp.net", 0),
            (JID_GROUP, "groupphone1", "g.us", 1),
            (JID_BROADCAST, "bcast1", "broadcast", 1),
        ],
    )
    conn.execute("INSERT INTO jid_map (lid_row_id, jid_row_id) VALUES (?, ?)", (JID_BOB_LID, JID_BOB_PHONE))
    conn.executemany(
        "INSERT INTO chat (_id, jid_row_id, subject, created_timestamp) VALUES (?, ?, ?, ?)",
        [
            (CHAT_DIRECT, JID_ALICE, None, T0 - 100_000),
            (CHAT_GROUP, JID_GROUP, GROUP_SUBJECT, T0 - 100_000),
            (CHAT_BROADCAST, JID_BROADCAST, None, T0 - 100_000),
        ],
    )
    conn.executemany(
        "INSERT INTO message "
        "(_id, chat_row_id, from_me, timestamp, received_timestamp, message_type, text_data, starred, "
        "sender_jid_row_id, key_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (MSG_ALICE_HELLO, CHAT_DIRECT, 0, T0, T0 + 500, 0, "Hello there", 0, None, "k1"),
            (MSG_ME_REPLY_ALICE, CHAT_DIRECT, 1, T0 + 60_000, 0, 0, "Hi Alice reply", 0, None, "k2"),
            (MSG_ALICE_IMAGE, CHAT_DIRECT, 0, T0 + 120_000, T0 + 120_500, 1, None, 0, None, "k3"),
            (MSG_SYSTEM, CHAT_DIRECT, 0, T0 + 180_000, 0, 7, SYSTEM_TEXT, 0, None, "k4"),
            (MSG_BOB_GROUP_HELLO, CHAT_GROUP, 0, T0 + 10_000, 0, 0, "group hello from bob", 0, JID_BOB_LID, "k5"),
            (MSG_CAROL_GROUP_HELLO, CHAT_GROUP, 0, T0 + 20_000, 0, 0, CAROL_GROUP_TEXT, 1, JID_CAROL, "k6"),
            (MSG_ME_GROUP, CHAT_GROUP, 1, T0 + 30_000, 0, 0, "me in group", 0, None, "k7"),
            (MSG_BOB_GROUP_AUDIO, CHAT_GROUP, 0, T0 + 40_000, 0, 2, None, 0, JID_BOB_LID, "k8"),
            (MSG_BROADCAST, CHAT_BROADCAST, 1, T0 + 5_000, 0, 0, "broadcast message", 0, None, "k9"),
        ],
    )
    conn.executemany(
        "INSERT INTO message_add_on "
        "(_id, parent_message_row_id, chat_row_id, from_me, sender_jid_row_id, timestamp, message_add_on_type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (1, MSG_BOB_GROUP_HELLO, CHAT_GROUP, 1, None, T0 + 15_000, 56),
            (2, MSG_CAROL_GROUP_HELLO, CHAT_GROUP, 0, JID_BOB_LID, T0 + 25_000, 56),
        ],
    )
    conn.executemany(
        "INSERT INTO message_add_on_reaction (message_add_on_row_id, reaction) VALUES (?, ?)",
        [(1, REACTION_ON_BOB_MSG), (2, REACTION_ON_CAROL_MSG)],
    )
    conn.execute(
        "INSERT INTO message_quoted "
        "(message_row_id, key_id, chat_row_id, from_me, message_type, text_data, sender_jid_row_id, "
        "parent_message_chat_row_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (MSG_ME_GROUP, "k5", CHAT_GROUP, 0, 0, "group hello from bob", JID_BOB_LID, CHAT_GROUP, T0 + 30_000),
    )
    conn.execute(
        "INSERT INTO call_log (_id, timestamp, call_result, duration, video_call, from_me, jid_row_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, T0 + 50_000, 5, 120, 0, 1, JID_ALICE),
    )
    conn.commit()


def seed_attachment_messages(conn: sqlite3.Connection) -> None:
    """Opt-in extra: contact, location, poll, ... messages + their side-table rows.

    Kept out of the base seed so the message counts other tests assert on stay stable.
    """
    conn.executemany(
        "INSERT INTO message "
        "(_id, chat_row_id, from_me, timestamp, received_timestamp, message_type, text_data, starred, "
        "sender_jid_row_id, key_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (MSG_ALICE_CONTACT, CHAT_DIRECT, 0, T0 + 240_000, 0, 4, DAVE_NAME, 0, None, "k10"),
            (MSG_ME_CONTACTS, CHAT_DIRECT, 1, T0 + 300_000, 0, 14, MULTI_CONTACT_TEXT, 0, None, "k11"),
            (MSG_ALICE_LOCATION, CHAT_DIRECT, 0, T0 + 360_000, 0, 5, None, 0, None, "k12"),
            (MSG_ME_LIVE_LOCATION, CHAT_DIRECT, 1, T0 + 420_000, 0, 16, None, 0, None, "k13"),
            (MSG_ALICE_POLL, CHAT_DIRECT, 0, T0 + 480_000, 0, 66, POLL_QUESTION, 0, None, "k14"),
        ],
    )
    conn.execute(
        "INSERT INTO message_poll (message_row_id, selectable_options_count) VALUES (?, ?)", (MSG_ALICE_POLL, 1)
    )
    conn.executemany(
        "INSERT INTO message_poll_option (message_row_id, option_name, vote_total) VALUES (?, ?, ?)",
        [(MSG_ALICE_POLL, name, votes) for name, votes in POLL_OPTIONS],
    )
    conn.executemany(
        "INSERT INTO message_location "
        "(message_row_id, chat_row_id, latitude, longitude, place_name, place_address, "
        "live_location_share_duration, live_location_final_latitude, live_location_final_longitude) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (MSG_ALICE_LOCATION, CHAT_DIRECT, PLACE_LAT, PLACE_LON, PLACE_NAME, PLACE_ADDRESS, None, None, None),
            (
                MSG_ME_LIVE_LOCATION,
                CHAT_DIRECT,
                LIVE_START_LAT,
                LIVE_START_LON,
                None,
                None,
                900,
                LIVE_FINAL_LAT,
                LIVE_FINAL_LON,
            ),
        ],
    )
    conn.executemany(
        "INSERT INTO message_vcard (_id, message_row_id, vcard) VALUES (?, ?, ?)",
        [
            (1, MSG_ALICE_CONTACT, DAVE_VCARD),
            (2, MSG_ME_CONTACTS, ERIN_VCARD),
            (3, MSG_ME_CONTACTS, FRANK_VCARD),
        ],
    )
    conn.commit()


def local_date(ts_ms: int) -> str:
    """Local calendar date matching sqlite's `date(ts/1000, 'unixepoch', 'localtime')` conversion."""
    return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d")  # noqa: DTZ006 - deliberately local, not UTC


def seed_wa_contacts(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO wa_contacts (jid, display_name) VALUES (?, ?)",
        [
            (f"{ALICE_PHONE}@s.whatsapp.net", ALICE_NAME),
            (f"{BOB_PHONE}@s.whatsapp.net", BOB_NAME),
            (f"{CAROL_PHONE}@s.whatsapp.net", CAROL_NAME),
        ],
    )
    conn.commit()
