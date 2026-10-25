import logging
import sqlite3

from narrative.db.queries.locations import fetch_locations
from narrative.db.row_types import RawLocationRow
from narrative.models.message import Location

logger = logging.getLogger(__name__)

LocationsByMessage = dict[int, Location]


def load_locations(conn: sqlite3.Connection, message_ids: set[int]) -> LocationsByMessage:
    """Map each location message id to its (last known) position."""
    return {row.message_id: _to_location(row=row) for row in fetch_locations(conn, message_ids=message_ids)}


def _to_location(row: RawLocationRow) -> Location:
    latitude, longitude = row.latitude, row.longitude
    if row.final_latitude and row.final_longitude:
        latitude, longitude = row.final_latitude, row.final_longitude
    return Location(
        latitude=latitude,
        longitude=longitude,
        name=row.place_name or None,
        address=row.place_address or None,
        live=row.live_share_duration is not None,
    )
