from narrative.models.chat import ChatSummary, ChatType


def test_chat_type_values() -> None:
    assert ChatType.DIRECT.value == "direct"
    assert ChatType.GROUP.value == "group"
    assert ChatType.BROADCAST.value == "broadcast"


def test_chat_summary_allows_optional_fields_none() -> None:
    summary = ChatSummary(
        chat_id=1,
        display_name="Alice",
        chat_type=ChatType.DIRECT,
        message_count=10,
        participant_count=None,
        date_first=None,
        date_last=None,
        phone="111",
        is_lid=False,
    )
    assert summary.participant_count is None
    assert summary.date_first is None
    assert summary.phone == "111"
