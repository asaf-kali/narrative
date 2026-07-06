from db.row_types import MessagesMetadata, RawMessageRow


def test_raw_message_row_ignores_extra_columns() -> None:
    row = RawMessageRow.model_validate(
        {
            "message_id": 1,
            "chat_row_id": 1,
            "from_me": 0,
            "timestamp": 123,
            "received_timestamp": 0,
            "message_type": 0,
            "text_data": "hi",
            "starred": 0,
            "sender_phone": "111",
            "sender_server": "s.whatsapp.net",
            "chat_subject": None,
            "chat_phone": "111",
            "chat_server": "s.whatsapp.net",
            "unexpected_column": "schema drift from a newer WhatsApp version",
        }
    )
    assert row.message_id == 1
    assert not hasattr(row, "unexpected_column")


def test_messages_metadata_roundtrip() -> None:
    meta = MessagesMetadata(total=5, available_sender_ids=["me", "111"], available_chat_ids=[1, 2])
    assert meta.total == 5
    assert meta.available_chat_ids == [1, 2]
