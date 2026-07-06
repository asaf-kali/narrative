import hashlib

from db.loaders import IndexMessage
from models.message import MessageType
from semantic_search.chunker import iterate_sessions

_TEXT = int(MessageType.TEXT)
_IMAGE = int(MessageType.IMAGE)


def _msg(message_id: int, timestamp: int, text_data: str | None = "hi", message_type: int = _TEXT) -> IndexMessage:
    return IndexMessage(
        message_id=message_id,
        chat_row_id=1,
        timestamp=timestamp,
        message_type=message_type,
        text_data=text_data,
        chat_name="Test Group",
        sender_name="Alice",
    )


def test_iterate_sessions_no_gap_single_session() -> None:
    messages = [_msg(1, 0), _msg(2, 1000), _msg(3, 2000)]
    sessions = list(iterate_sessions(messages, chat_id=1, chat_name="G", gap_seconds=60))
    assert len(sessions) == 1
    assert sessions[0].message_count == 3
    assert sessions[0].min_message_id == 1
    assert sessions[0].max_message_id == 3


def test_iterate_sessions_gap_splits_when_min_chars_met() -> None:
    ten_minutes_ms = 10 * 60 * 1000
    messages = [_msg(1, 0, text_data="hello world"), _msg(2, ten_minutes_ms, text_data="second session")]
    sessions = list(iterate_sessions(messages, chat_id=1, chat_name="G", gap_seconds=60, min_session_chars=0))
    assert len(sessions) == 2
    assert sessions[0].max_message_id == 1
    assert sessions[1].min_message_id == 2


def test_iterate_sessions_gap_does_not_split_below_min_chars() -> None:
    ten_minutes_ms = 10 * 60 * 1000
    messages = [_msg(1, 0, text_data="hi"), _msg(2, ten_minutes_ms, text_data="second")]
    sessions = list(iterate_sessions(messages, chat_id=1, chat_name="G", gap_seconds=60, min_session_chars=1000))
    assert len(sessions) == 1
    assert sessions[0].message_count == 2


def test_iterate_sessions_max_session_messages_forces_split() -> None:
    messages = [_msg(i, i * 100) for i in range(1, 6)]
    sessions = list(iterate_sessions(messages, chat_id=1, chat_name="G", gap_seconds=3600, max_session_messages=2))
    assert [s.message_count for s in sessions] == [2, 2, 1]


def test_iterate_sessions_all_media_buffer_yields_no_session() -> None:
    messages = [_msg(1, 0, text_data=None, message_type=_IMAGE), _msg(2, 100, text_data=None, message_type=_IMAGE)]
    sessions = list(iterate_sessions(messages, chat_id=1, chat_name="G", gap_seconds=60))
    assert sessions == []


def test_iterate_sessions_embed_text_excludes_sender_names() -> None:
    messages = [_msg(1, 0, text_data="hello"), _msg(2, 100, text_data="world")]
    sessions = list(iterate_sessions(messages, chat_id=1, chat_name="G", gap_seconds=60))
    assert sessions[0].embed_text == "hello\nworld"
    assert sessions[0].display_text == "Alice: hello\nAlice: world"


def test_iterate_sessions_session_id_is_deterministic_hash() -> None:
    messages = [_msg(7, 0)]
    sessions = list(iterate_sessions(messages, chat_id=42, chat_name="G", gap_seconds=60))
    expected = hashlib.sha256(b"42:7").hexdigest()[:16]
    assert sessions[0].session_id == expected


def test_iterate_sessions_empty_input_yields_nothing() -> None:
    assert list(iterate_sessions(iter([]), chat_id=1, chat_name="G", gap_seconds=60)) == []
