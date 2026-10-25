import logging
import sqlite3

from narrative.db.queries.calls import fetch_message_calls
from narrative.db.row_types import RawMessageCallRow
from narrative.models.message import CallInfo, CallOutcome

logger = logging.getLogger(__name__)

CallsByMessage = dict[int, CallInfo]

# call_log.call_result values (see queries/calls.py).
_OUTCOMES: dict[int, CallOutcome] = {2: "missed", 3: "busy", 4: "declined", 5: "completed"}


def load_message_calls(conn: sqlite3.Connection, message_ids: set[int]) -> CallsByMessage:
    """Map each in-chat call message id to its call's type, duration and outcome."""
    return {row.message_id: _to_call_info(row=row) for row in fetch_message_calls(conn, message_ids=message_ids)}


def _to_call_info(row: RawMessageCallRow) -> CallInfo:
    outcome = _OUTCOMES.get(row.call_result or 0, "unknown")
    return CallInfo(video=bool(row.is_video), duration_seconds=row.duration or 0, outcome=outcome)
