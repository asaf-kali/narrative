import sqlite3

from seed_data import (
    DAVE_NAME,
    DAVE_PHONE,
    ERIN_NAME,
    ERIN_PHONES,
    FRANK_NAME,
    MSG_ALICE_CONTACT,
    MSG_ME_CONTACTS,
)

from narrative.db.vcards import load_contact_cards, parse_vcard
from narrative.models.message import ContactCard


def test_parse_vcard_reads_name_and_group_prefixed_phone() -> None:
    vcard = "BEGIN:VCARD\nVERSION:3.0\nFN:Dave\nitem1.TEL;waid=15550100:+1 555-0100\nEND:VCARD"
    assert parse_vcard(vcard=vcard) == ContactCard(name="Dave", phones=["+1 555-0100"])


def test_parse_vcard_collects_multiple_phones_in_order() -> None:
    vcard = "BEGIN:VCARD\nFN:Erin\nTEL;type=CELL:111\ntel;type=WORK:222\nEND:VCARD"
    assert parse_vcard(vcard=vcard).phones == ["111", "222"]


def test_parse_vcard_unfolds_continuation_lines() -> None:
    vcard = "BEGIN:VCARD\r\nFN:Very Long\r\n  Name\r\nEND:VCARD"
    assert parse_vcard(vcard=vcard).name == "Very Long Name"


def test_parse_vcard_unescapes_text_values() -> None:
    vcard = "BEGIN:VCARD\nFN:Smith\\, John\\; Jr\\nIII\nEND:VCARD"
    assert parse_vcard(vcard=vcard).name == "Smith, John; Jr III"


def test_parse_vcard_without_name_or_phone_falls_back() -> None:
    card = parse_vcard(vcard="BEGIN:VCARD\nVERSION:3.0\nEND:VCARD")
    assert card == ContactCard(name="Unknown contact", phones=[])


def test_load_contact_cards_groups_by_message(contacts_msgstore_conn: sqlite3.Connection) -> None:
    cards = load_contact_cards(contacts_msgstore_conn, message_ids={MSG_ALICE_CONTACT, MSG_ME_CONTACTS})
    assert cards == {
        MSG_ALICE_CONTACT: [ContactCard(name=DAVE_NAME, phones=[DAVE_PHONE])],
        MSG_ME_CONTACTS: [
            ContactCard(name=ERIN_NAME, phones=list(ERIN_PHONES)),
            ContactCard(name=FRANK_NAME, phones=[]),
        ],
    }


def test_load_contact_cards_no_ids_returns_empty(contacts_msgstore_conn: sqlite3.Connection) -> None:
    assert load_contact_cards(contacts_msgstore_conn, message_ids=set()) == {}
