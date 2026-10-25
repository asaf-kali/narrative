import sqlite3
from pathlib import Path

from seed_data import MSG_ALICE_HELLO, MSG_ALICE_POLL, POLL_OPTIONS

from narrative.db.polls import load_polls
from narrative.db.queries.polls import fetch_poll_options
from narrative.models.message import Poll, PollOption


def test_load_polls_returns_options_in_order_with_votes(attachments_msgstore_conn: sqlite3.Connection) -> None:
    polls = load_polls(attachments_msgstore_conn, message_ids={MSG_ALICE_POLL})
    expected_options = [PollOption(name=name, votes=votes) for name, votes in POLL_OPTIONS]
    assert polls == {MSG_ALICE_POLL: Poll(options=expected_options, multiple_choice=False)}


def test_load_polls_ignores_non_poll_messages(attachments_msgstore_conn: sqlite3.Connection) -> None:
    assert load_polls(attachments_msgstore_conn, message_ids={MSG_ALICE_HELLO}) == {}


def test_load_polls_without_poll_row_defaults_to_multiple_choice(attachments_msgstore_conn: sqlite3.Connection) -> None:
    attachments_msgstore_conn.execute("DELETE FROM message_poll")
    assert load_polls(attachments_msgstore_conn, message_ids={MSG_ALICE_POLL})[MSG_ALICE_POLL].multiple_choice


def test_fetch_poll_options_missing_tables_returns_empty(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "no_polls.db")
    conn.row_factory = sqlite3.Row
    assert list(fetch_poll_options(conn, message_ids={1})) == []
    conn.close()


def test_fetch_poll_options_empty_ids_returns_empty(attachments_msgstore_conn: sqlite3.Connection) -> None:
    assert list(fetch_poll_options(attachments_msgstore_conn, message_ids=set())) == []
