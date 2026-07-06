import sqlite3
from pathlib import Path

from narrative.db.contacts import (
    _display_name,
    _parse_phone,
    _resolve_lids,
    _row_phones,
    build_sender_registry,
    load_contacts_csv,
)


def test_parse_phone_strips_non_digits() -> None:
    assert _parse_phone("+1 (234) 567-8901", local_code=None) == "12345678901"


def test_parse_phone_removes_00_international_prefix() -> None:
    assert _parse_phone("00972501234567", local_code=None) == "972501234567"


def test_parse_phone_local_code_swaps_leading_zero() -> None:
    assert _parse_phone("0541234567", local_code="972") == "972541234567"


def test_parse_phone_no_local_code_leaves_leading_zero() -> None:
    assert _parse_phone("0541234567", local_code=None) == "0541234567"


def test_parse_phone_too_short_returns_none() -> None:
    assert _parse_phone("12345", local_code=None) is None


def test_parse_phone_too_long_returns_none() -> None:
    assert _parse_phone("1" * 16, local_code=None) is None


def test_parse_phone_boundary_lengths_are_valid() -> None:
    assert _parse_phone("1234567", local_code=None) == "1234567"  # 7 digits, min bound
    assert _parse_phone("1" * 15, local_code=None) == "1" * 15  # 15 digits, max bound


def test_row_phones_splits_multi_value_cell() -> None:
    row = {"Phone 1": "0541234567 ::: 0549876543"}
    phones = _row_phones(row, local_code=None)
    assert phones == {"0541234567", "0549876543"}


def test_row_phones_skips_empty_values() -> None:
    row = {"Phone 1": "", "Phone 2": "0541234567"}
    assert _row_phones(row, local_code=None) == {"0541234567"}


def test_display_name_prefers_first_middle_last() -> None:
    row = {"First Name": "Ada", "Middle Name": "", "Last Name": "Lovelace"}
    assert _display_name(row) == "Ada Lovelace"


def test_display_name_falls_back_to_nickname() -> None:
    row = {"First Name": "", "Middle Name": "", "Last Name": "", "Nickname": "Bugsy"}
    assert _display_name(row) == "Bugsy"


def test_display_name_falls_back_to_organization() -> None:
    row = {"First Name": "", "Nickname": "", "Organization Name": "Acme Corp"}
    assert _display_name(row) == "Acme Corp"


def test_display_name_empty_when_nothing_present() -> None:
    assert _display_name({}) == ""


def test_load_contacts_csv_parses_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "contacts.csv"
    csv_path.write_text(
        "First Name,Last Name,Phone 1 - Value\nAda,Lovelace,0541234567\nGrace,Hopper,0549876543\n",
        encoding="utf-8",
    )
    contacts = load_contacts_csv(csv_path, local_code="972")
    assert contacts == {"972541234567": "Ada Lovelace", "972549876543": "Grace Hopper"}


def test_load_contacts_csv_strips_bom(tmp_path: Path) -> None:
    csv_path = tmp_path / "contacts.csv"
    csv_path.write_bytes(b"\xef\xbb\xbfFirst Name,Phone 1 - Value\nAda,0541234567\n")
    contacts = load_contacts_csv(csv_path, local_code="972")
    assert contacts == {"972541234567": "Ada"}


def test_load_contacts_csv_duplicate_phone_keeps_first(tmp_path: Path) -> None:
    csv_path = tmp_path / "contacts.csv"
    csv_path.write_text(
        "First Name,Phone 1 - Value\nAda,0541234567\nEve,0541234567\n",
        encoding="utf-8",
    )
    contacts = load_contacts_csv(csv_path, local_code="972")
    assert contacts == {"972541234567": "Ada"}


def test_load_contacts_csv_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_contacts_csv(tmp_path / "missing.csv", local_code=None) == {}


def test_load_contacts_csv_row_without_name_is_skipped(tmp_path: Path) -> None:
    csv_path = tmp_path / "contacts.csv"
    csv_path.write_text("First Name,Phone 1 - Value\n,0541234567\n", encoding="utf-8")
    assert load_contacts_csv(csv_path, local_code=None) == {}


def test_resolve_lids_maps_named_and_phone_only(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "msgstore.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE jid (_id INTEGER PRIMARY KEY, user TEXT, server TEXT, type INTEGER);"
        "CREATE TABLE jid_map (lid_row_id INTEGER, jid_row_id INTEGER);"
    )
    conn.executemany(
        "INSERT INTO jid (_id, user, server, type) VALUES (?, ?, ?, ?)",
        [
            (1, "lidnamed", "lid", 0),
            (2, "111", "s.whatsapp.net", 0),
            (3, "lidunnamed", "lid", 0),
            (4, "222", "s.whatsapp.net", 0),
        ],
    )
    conn.executemany("INSERT INTO jid_map (lid_row_id, jid_row_id) VALUES (?, ?)", [(1, 2), (3, 4)])
    conn.commit()

    resolved = _resolve_lids(conn, contacts={"111": "Alice"})
    assert resolved == {"lidnamed": "Alice", "lidunnamed": "222"}
    conn.close()


def test_resolve_lids_missing_jid_map_returns_empty(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "msgstore.db")
    conn.executescript("CREATE TABLE jid (_id INTEGER PRIMARY KEY, user TEXT, server TEXT, type INTEGER);")
    conn.commit()
    assert _resolve_lids(conn, contacts={}) == {}
    conn.close()


def test_build_sender_registry_priority_csv_over_wa_contacts(tmp_path: Path) -> None:
    wadb = sqlite3.connect(tmp_path / "wa.db")
    wadb.row_factory = sqlite3.Row
    wadb.executescript("CREATE TABLE wa_contacts (jid TEXT, display_name TEXT);")
    wadb.execute("INSERT INTO wa_contacts (jid, display_name) VALUES (?, ?)", ("1234567@s.whatsapp.net", "WA Name"))
    wadb.commit()

    csv_path = tmp_path / "contacts.csv"
    csv_path.write_text("First Name,Phone 1 - Value\nCSV Name,1234567\n", encoding="utf-8")

    registry = build_sender_registry(wadb=wadb, csv_path=csv_path, msgstore=None)
    assert registry.as_dict()["1234567"] == "CSV Name"
    wadb.close()


def test_build_sender_registry_no_sources_returns_empty_registry() -> None:
    registry = build_sender_registry(wadb=None, csv_path=None, msgstore=None)
    assert registry.as_dict() == {}
