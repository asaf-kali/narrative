import logging
import sqlite3

from narrative.db.queries.polls import fetch_poll_options
from narrative.db.row_types import RawPollOptionRow
from narrative.models.message import Poll, PollOption

logger = logging.getLogger(__name__)

PollsByMessage = dict[int, Poll]


def load_polls(conn: sqlite3.Connection, message_ids: set[int]) -> PollsByMessage:
    """Map each poll message id to its options (in creation order) and vote totals."""
    polls: PollsByMessage = {}
    for row in fetch_poll_options(conn, message_ids=message_ids):
        poll = polls.setdefault(row.message_id, _empty_poll(row=row))
        option = PollOption(name=row.option_name or "", votes=row.vote_total or 0)
        poll.options.append(option)
    return polls


def _empty_poll(row: RawPollOptionRow) -> Poll:
    return Poll(options=[], multiple_choice=row.selectable_options_count != 1)
