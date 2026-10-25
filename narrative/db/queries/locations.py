import logging
import sqlite3
from collections.abc import Generator

from narrative.db.row_types import RawLocationRow

logger = logging.getLogger(__name__)

# message_location holds static pins (message_type 5) and live shares (16).
# Live shares keep the start point in latitude/longitude and the last update in
# live_location_final_*; static pins may carry a place name/address.
_LOCATIONS_SQL = """
SELECT
    message_row_id                 AS message_id,
    latitude,
    longitude,
    place_name,
    place_address,
    live_location_share_duration   AS live_share_duration,
    live_location_final_latitude   AS final_latitude,
    live_location_final_longitude  AS final_longitude
FROM message_location
WHERE message_row_id IN ({placeholders})
  AND latitude IS NOT NULL
  AND longitude IS NOT NULL
"""


def fetch_locations(conn: sqlite3.Connection, message_ids: set[int]) -> Generator[RawLocationRow]:
    if not message_ids:
        return
    placeholders = ",".join("?" * len(message_ids))
    sql = _LOCATIONS_SQL.format(placeholders=placeholders)
    try:
        for row in conn.execute(sql, sorted(message_ids)):
            yield RawLocationRow.model_validate(dict(row))
    except sqlite3.OperationalError:
        logger.debug("message_location table not found — skipping.")
