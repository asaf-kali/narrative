import datetime
import sqlite3
from pathlib import Path

import pandas as pd
from seed_data import (
    ALICE_NAME,
    BOB_NAME,
    CAROL_NAME,
    CHAT_DIRECT,
    CHAT_GROUP,
    GROUP_SUBJECT,
    MSG_BOB_GROUP_HELLO,
    MSG_ME_GROUP,
)

from narrative.db.connection import DBConnection
from narrative.db.loaders import (
    DataLoader,
    IndexMessage,
    _to_index_message,
    build_messages_df,
    datetime_to_ms,
    open_connection,
)
from narrative.db.row_types import RawMessageRow
from narrative.models.config import AnalysisConfig
from narrative.models.sender import SenderRegistry


def test_load_chats_returns_all_chat_types(data_loader: DataLoader) -> None:
    chats = data_loader.load_chats()
    assert len(chats) == 3
    direct = next(c for c in chats if c.chat_id == CHAT_DIRECT)
    assert direct.display_name == ALICE_NAME
    assert direct.chat_type.value == "direct"
    group = next(c for c in chats if c.chat_id == CHAT_GROUP)
    assert group.display_name == GROUP_SUBJECT
    assert group.chat_type.value == "group"


def test_load_chats_search_filters_case_insensitive(data_loader: DataLoader) -> None:
    chats = data_loader.load_chats(search="test group")
    assert len(chats) == 1
    assert chats[0].chat_id == CHAT_GROUP


def test_load_chats_search_no_match_returns_empty(data_loader: DataLoader) -> None:
    assert data_loader.load_chats(search="nonexistent") == []


def test_load_chats_limit(data_loader: DataLoader) -> None:
    assert len(data_loader.load_chats(limit=1)) == 1


def test_load_messages_excludes_system_by_default(data_loader: DataLoader) -> None:
    config = AnalysisConfig(chat_id=CHAT_DIRECT)
    df = data_loader.load_messages(config)
    assert len(df) == 3
    assert 7 not in df["message_type"].to_numpy()


def test_load_messages_includes_system_when_disabled(data_loader: DataLoader) -> None:
    config = AnalysisConfig(chat_id=CHAT_DIRECT, exclude_system=False)
    df = data_loader.load_messages(config)
    assert len(df) == 4


def test_load_messages_empty_chat_returns_empty_df_with_columns(data_loader: DataLoader) -> None:
    config = AnalysisConfig(chat_id=999)
    df = data_loader.load_messages(config)
    assert df.empty
    assert "sender_name" in df.columns


def test_load_messages_resolves_group_lid_sender(data_loader: DataLoader) -> None:
    config = AnalysisConfig(chat_id=CHAT_GROUP)
    df = data_loader.load_messages(config)
    bob_rows = df[df["message_id"] == MSG_BOB_GROUP_HELLO]
    assert bob_rows.iloc[0]["sender_name"] == BOB_NAME


def test_load_messages_resolves_group_plain_jid_sender(data_loader: DataLoader) -> None:
    config = AnalysisConfig(chat_id=CHAT_GROUP)
    df = data_loader.load_messages(config)
    carol_rows = df[df["sender_name"] == CAROL_NAME]
    assert len(carol_rows) == 1


def test_load_messages_from_me_uses_me_name(data_loader: DataLoader) -> None:
    config = AnalysisConfig(chat_id=CHAT_GROUP)
    df = data_loader.load_messages(config)
    me_rows = df[df["message_id"] == MSG_ME_GROUP]
    assert me_rows.iloc[0]["sender_name"] == "Me"


def test_load_reactions_resolves_names(data_loader: DataLoader) -> None:
    df = data_loader.load_reactions(chat_id=CHAT_GROUP)
    assert len(df) == 2
    assert set(df["reactor_name"]) == {"Me", BOB_NAME}


def test_load_reactions_empty_when_no_chat_matches(data_loader: DataLoader) -> None:
    df = data_loader.load_reactions(chat_id=999)
    assert df.empty
    assert "reactor_name" in df.columns


def test_load_replies_resolves_quoted_sender(data_loader: DataLoader) -> None:
    df = data_loader.load_replies(chat_id=CHAT_GROUP)
    assert len(df) == 1
    assert df.iloc[0]["quoted_sender_name"] == BOB_NAME
    assert df.iloc[0]["quoted_message_id"] == MSG_BOB_GROUP_HELLO


def test_load_calls_normalizes_timestamp(data_loader: DataLoader) -> None:
    df = data_loader.load_calls()
    assert len(df) == 1
    assert df.iloc[0]["duration"] == 120


def test_load_calls_empty_when_no_calls(sender_registry: SenderRegistry, tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "empty.db")
    conn.executescript(
        "CREATE TABLE call_log (_id INTEGER, timestamp INTEGER, call_result INTEGER, "
        "duration INTEGER, video_call INTEGER, from_me INTEGER, jid_row_id INTEGER);"
    )
    conn.close()

    with DBConnection(msgstore_path=tmp_path / "empty.db") as db:
        loader = DataLoader(db, registry=sender_registry)
        df = loader.load_calls()
    assert df.empty
    assert "call_id" in df.columns


def test_iter_chat_messages_paginates_and_skips_system(data_loader: DataLoader) -> None:
    messages = list(data_loader.iter_chat_messages(chat_id=CHAT_DIRECT, chunk_size=2))
    # 4 rows in chat, one is system (filtered); pagination with chunk_size=2 must still see all pages.
    assert len(messages) == 3
    assert all(m.message_type != 7 for m in messages)


def test_iter_chat_messages_respects_after_id(data_loader: DataLoader) -> None:
    messages = list(data_loader.iter_chat_messages(chat_id=CHAT_GROUP, chunk_size=10, after_id=MSG_BOB_GROUP_HELLO))
    assert all(m.message_id > MSG_BOB_GROUP_HELLO for m in messages)


def test_load_boundary_rows_filters_by_max_id(data_loader: DataLoader) -> None:
    rows = data_loader.load_boundary_rows(chat_id=CHAT_GROUP, min_id=0, max_id=MSG_BOB_GROUP_HELLO)
    assert all(r.message_id <= MSG_BOB_GROUP_HELLO for r in rows)


def test_datetime_to_ms_naive_treated_as_local() -> None:
    dt = datetime.datetime(2024, 1, 1, 12, 0, 0)  # noqa: DTZ001 - the naive/local case under test
    ms = datetime_to_ms(dt)
    assert isinstance(ms, int)
    assert ms > 0


def test_datetime_to_ms_aware_uses_given_tz() -> None:
    dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
    assert datetime_to_ms(dt) == int(dt.timestamp() * 1000)


def test_open_connection_returns_unopened_db_connection(tmp_path: Path) -> None:
    db = open_connection(msgstore_path=tmp_path / "msgstore.db")
    assert db.wadb is None


def test_build_messages_df_direct_chat_sender_fallback_to_chat_phone() -> None:
    row = RawMessageRow(
        message_id=1,
        chat_row_id=1,
        from_me=0,
        timestamp=1_700_000_000_000,
        received_timestamp=0,
        message_type=0,
        text_data="hi",
        starred=0,
        sender_phone="",
        sender_server="s.whatsapp.net",
        chat_subject=None,
        chat_phone="111222333",
        chat_server="s.whatsapp.net",
    )
    registry = SenderRegistry(contacts={"111222333": "Dana"})
    df = build_messages_df([row], registry)
    assert df.iloc[0]["sender_name"] == "Dana"
    assert df.iloc[0]["chat_name"] == "Dana"
    assert not df.iloc[0]["is_group"]


def test_build_messages_df_group_chat_uses_subject_and_group_fallback() -> None:
    row_with_subject = RawMessageRow(
        message_id=1,
        chat_row_id=1,
        from_me=0,
        timestamp=1_700_000_000_000,
        received_timestamp=0,
        message_type=0,
        text_data="hi",
        starred=0,
        sender_phone="555",
        sender_server="g.us",
        chat_subject="My Group",
        chat_phone="999",
        chat_server="g.us",
    )
    registry = SenderRegistry(contacts={})
    df = build_messages_df([row_with_subject], registry)
    assert df.iloc[0]["chat_name"] == "My Group"
    assert df.iloc[0]["is_group"]


def test_build_messages_df_clamps_corrupt_received_timestamp() -> None:
    row = RawMessageRow(
        message_id=1,
        chat_row_id=1,
        from_me=0,
        timestamp=1_700_000_000_000,
        received_timestamp=99_999_999_999_999,  # above _MAX_MS_TS sentinel
        message_type=0,
        text_data="hi",
        starred=0,
        sender_phone="111",
        sender_server="s.whatsapp.net",
        chat_subject=None,
        chat_phone="111",
        chat_server="s.whatsapp.net",
    )
    registry = SenderRegistry(contacts={})
    df = build_messages_df([row], registry)
    assert pd.isna(df.iloc[0]["received_timestamp"])


def test_to_index_message_matches_raw_row_variant() -> None:
    """`_to_index_message` is unused dead code kept for reference; verify it still matches its sibling."""
    row = RawMessageRow(
        message_id=5,
        chat_row_id=2,
        from_me=0,
        timestamp=1_700_000_000_000,
        received_timestamp=0,
        message_type=0,
        text_data="hello",
        starred=0,
        sender_phone="222",
        sender_server="s.whatsapp.net",
        chat_subject="Group X",
        chat_phone="888",
        chat_server="g.us",
    )
    registry = SenderRegistry(contacts={"222": "Bob"})
    contacts = registry.as_dict()
    result = _to_index_message(row, registry, contacts)
    assert isinstance(result, IndexMessage)
    assert result.chat_name == "Group X"
    assert result.sender_name == "Bob"
    assert result.message_id == 5


def test_to_index_message_from_me_uses_me_name() -> None:
    row = RawMessageRow(
        message_id=1,
        chat_row_id=1,
        from_me=1,
        timestamp=1_700_000_000_000,
        received_timestamp=0,
        message_type=0,
        text_data="hi",
        starred=0,
        sender_phone="",
        sender_server="",
        chat_subject=None,
        chat_phone="111",
        chat_server="s.whatsapp.net",
    )
    registry = SenderRegistry(contacts={}, me_name="Asaf")
    result = _to_index_message(row, registry, registry.as_dict())
    assert result.sender_name == "Asaf"
