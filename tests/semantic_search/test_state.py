from datetime import UTC, datetime
from pathlib import Path

from narrative.semantic_search.session import Session
from narrative.semantic_search.state import StateDB


def _session(session_id: str, chat_id: int, min_id: int, max_id: int) -> Session:
    return Session(
        session_id=session_id,
        chat_id=chat_id,
        chat_name="Test Group",
        timestamp_start=datetime(2024, 1, 1, tzinfo=UTC),
        timestamp_end=datetime(2024, 1, 1, 0, 5, tzinfo=UTC),
        min_message_id=min_id,
        max_message_id=max_id,
        message_count=max_id - min_id + 1,
        embed_text="hello",
        display_text="Alice: hello",
    )


def test_get_max_indexed_defaults_to_zero(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "search")
    assert db.get_max_indexed(chat_id=1) == 0
    db.close()


def test_upsert_state_then_get_max_indexed(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "search")
    db.upsert_state(chat_id=1, max_id=10)
    assert db.get_max_indexed(chat_id=1) == 10
    db.upsert_state(chat_id=1, max_id=20)
    assert db.get_max_indexed(chat_id=1) == 20
    db.close()


def test_insert_sessions_and_count(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "search")
    db.insert_sessions([_session("s1", 1, 1, 5), _session("s2", 1, 6, 10)])
    assert db.count_sessions_for_chat(chat_id=1) == 2
    db.close()


def test_delete_session_removes_it(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "search")
    db.insert_sessions([_session("s1", 1, 1, 5)])
    db.delete_session("s1")
    assert db.count_sessions_for_chat(chat_id=1) == 0
    db.close()


def test_get_last_session_returns_highest_max_message_id(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "search")
    db.insert_sessions([_session("s1", 1, 1, 5), _session("s2", 1, 6, 10)])
    last = db.get_last_session(chat_id=1)
    assert last is not None
    assert last.session_id == "s2"
    db.close()


def test_get_last_session_none_when_no_sessions(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "search")
    assert db.get_last_session(chat_id=1) is None
    db.close()


def test_all_chat_ids_lists_indexed_chats(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "search")
    db.upsert_state(chat_id=1, max_id=5)
    db.upsert_state(chat_id=2, max_id=8)
    assert set(db.all_chat_ids()) == {1, 2}
    db.close()


def test_count_sessions_for_chat_zero_when_none(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "search")
    assert db.count_sessions_for_chat(chat_id=999) == 0
    db.close()


def test_state_db_creates_search_dir(tmp_path: Path) -> None:
    search_dir = tmp_path / "nested" / "search"
    StateDB(search_dir).close()
    assert search_dir.exists()
    assert (search_dir / "state.db").exists()
