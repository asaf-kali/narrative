import sqlite3

from seed_data import CHAT_DIRECT, DAVE_NAME, DAVE_PHONE, MSG_ALICE_CONTACT, MSG_ALICE_HELLO

from narrative.db.attachments import MessageAttachments, load_message_attachments
from narrative.db.queries.messages import fetch_messages_page


def test_load_message_attachments_collects_contact_cards(contacts_msgstore_conn: sqlite3.Connection) -> None:
    rows = fetch_messages_page(contacts_msgstore_conn, chat_id=CHAT_DIRECT)
    attachments = load_message_attachments(contacts_msgstore_conn, rows=rows)
    assert attachments.fields_for(MSG_ALICE_CONTACT) == {"contacts": [{"name": DAVE_NAME, "phones": [DAVE_PHONE]}]}


def test_fields_for_message_without_attachments_is_all_none() -> None:
    assert MessageAttachments().fields_for(MSG_ALICE_HELLO) == {"contacts": None}
