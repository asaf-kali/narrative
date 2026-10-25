import sqlite3
from pathlib import Path

from seed_data import (
    LIVE_FINAL_LAT,
    LIVE_FINAL_LON,
    MSG_ALICE_HELLO,
    MSG_ALICE_LOCATION,
    MSG_ME_LIVE_LOCATION,
    PLACE_ADDRESS,
    PLACE_LAT,
    PLACE_LON,
    PLACE_NAME,
)

from narrative.db.locations import load_locations
from narrative.db.queries.locations import fetch_locations
from narrative.models.message import Location


def test_load_locations_static_pin_keeps_place(attachments_msgstore_conn: sqlite3.Connection) -> None:
    locations = load_locations(attachments_msgstore_conn, message_ids={MSG_ALICE_LOCATION})
    assert locations[MSG_ALICE_LOCATION] == Location(
        latitude=PLACE_LAT, longitude=PLACE_LON, name=PLACE_NAME, address=PLACE_ADDRESS, live=False
    )


def test_load_locations_live_share_uses_final_position(attachments_msgstore_conn: sqlite3.Connection) -> None:
    location = load_locations(attachments_msgstore_conn, message_ids={MSG_ME_LIVE_LOCATION})[MSG_ME_LIVE_LOCATION]
    assert (location.latitude, location.longitude) == (LIVE_FINAL_LAT, LIVE_FINAL_LON)
    assert location.live


def test_load_locations_ignores_non_location_messages(attachments_msgstore_conn: sqlite3.Connection) -> None:
    assert load_locations(attachments_msgstore_conn, message_ids={MSG_ALICE_HELLO}) == {}


def test_fetch_locations_empty_ids_returns_empty(attachments_msgstore_conn: sqlite3.Connection) -> None:
    assert list(fetch_locations(attachments_msgstore_conn, message_ids=set())) == []


def test_fetch_locations_missing_table_returns_empty(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "no_locations.db")
    conn.row_factory = sqlite3.Row
    assert list(fetch_locations(conn, message_ids={1})) == []
    conn.close()
