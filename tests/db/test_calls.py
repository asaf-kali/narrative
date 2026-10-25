import sqlite3
from pathlib import Path

from seed_data import CALL_COMPLETED_DURATION, MSG_ALICE_HELLO, MSG_ALICE_MISSED_CALL, MSG_ME_CALL

from narrative.db.calls import load_message_calls
from narrative.db.queries.calls import fetch_message_calls
from narrative.models.message import CallInfo


def test_load_message_calls_maps_outcome_and_type(attachments_msgstore_conn: sqlite3.Connection) -> None:
    calls = load_message_calls(attachments_msgstore_conn, message_ids={MSG_ME_CALL, MSG_ALICE_MISSED_CALL})
    assert calls == {
        MSG_ME_CALL: CallInfo(video=False, duration_seconds=CALL_COMPLETED_DURATION, outcome="completed"),
        MSG_ALICE_MISSED_CALL: CallInfo(video=True, duration_seconds=0, outcome="missed"),
    }


def test_load_message_calls_unknown_result(attachments_msgstore_conn: sqlite3.Connection) -> None:
    attachments_msgstore_conn.execute("UPDATE call_log SET call_result = 99")
    calls = load_message_calls(attachments_msgstore_conn, message_ids={MSG_ME_CALL})
    assert calls[MSG_ME_CALL].outcome == "unknown"


def test_load_message_calls_ignores_non_call_messages(attachments_msgstore_conn: sqlite3.Connection) -> None:
    assert load_message_calls(attachments_msgstore_conn, message_ids={MSG_ALICE_HELLO}) == {}


def test_fetch_message_calls_empty_ids_returns_empty(attachments_msgstore_conn: sqlite3.Connection) -> None:
    assert list(fetch_message_calls(attachments_msgstore_conn, message_ids=set())) == []


def test_fetch_message_calls_missing_table_returns_empty(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "no_calls.db")
    conn.row_factory = sqlite3.Row
    assert list(fetch_message_calls(conn, message_ids={1})) == []
    conn.close()
