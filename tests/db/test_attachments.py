import sqlite3

from seed_data import (
    CHAT_DIRECT,
    DAVE_NAME,
    DAVE_PHONE,
    MSG_ALICE_CONTACT,
    MSG_ALICE_HELLO,
    MSG_ALICE_LOCATION,
    PLACE_NAME,
)

from narrative.db.attachments import MessageAttachments, load_message_attachments
from narrative.db.queries.messages import fetch_messages_page


def test_load_message_attachments_collects_each_kind(attachments_msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_messages_page(attachments_msgstore_conn, chat_id=CHAT_DIRECT)
    attachments = load_message_attachments(attachments_msgstore_conn, rows=rows)
    contact_fields = attachments.fields_for(MSG_ALICE_CONTACT)
    assert contact_fields["contacts"] == [{"name": DAVE_NAME, "phones": [DAVE_PHONE]}]
    assert contact_fields["location"] is None
    assert attachments.fields_for(MSG_ALICE_LOCATION)["location"]["name"] == PLACE_NAME


def test_fields_for_message_without_attachments_is_all_none() -> None:
    fields = MessageAttachments().fields_for(MSG_ALICE_HELLO)
    assert set(fields.values()) == {None}
