from datetime import UTC, datetime

from semantic_search.session import Session, SessionMeta, SessionRecord


def test_session_roundtrip() -> None:
    session = Session(
        session_id="abc123",
        chat_id=1,
        chat_name="Test Group",
        timestamp_start=datetime(2024, 1, 1, tzinfo=UTC),
        timestamp_end=datetime(2024, 1, 1, 0, 5, tzinfo=UTC),
        min_message_id=1,
        max_message_id=5,
        message_count=5,
        embed_text="hello world",
        display_text="Alice: hello world",
    )
    assert session.message_count == 5
    assert session.chat_name == "Test Group"


def test_session_meta_roundtrip() -> None:
    meta = SessionMeta(
        session_id="abc123",
        chat_id=1,
        min_message_id=1,
        max_message_id=5,
        timestamp_start=datetime(2024, 1, 1, tzinfo=UTC),
        timestamp_end=datetime(2024, 1, 1, 0, 5, tzinfo=UTC),
    )
    assert meta.session_id == "abc123"


def test_session_record_roundtrip() -> None:
    record = SessionRecord(
        session_id="abc123",
        chat_id=1,
        chat_name="Test Group",
        timestamp_start=datetime(2024, 1, 1, tzinfo=UTC),
        timestamp_end=datetime(2024, 1, 1, 0, 5, tzinfo=UTC),
        text="hello world",
        vector=[0.1, 0.2, 0.3],
    )
    assert len(record.vector) == 3
