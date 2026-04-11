import csv
import logging
import re
import sqlite3
from pathlib import Path

from models.sender import SenderRegistry

logger = logging.getLogger(__name__)

_NON_DIGIT = re.compile(r"\D")
_MIN_PHONE_DIGITS = 7
_MAX_PHONE_DIGITS = 15


def build_sender_registry(
    wadb: sqlite3.Connection | None,
    csv_path: Path | None,
    msgstore: sqlite3.Connection | None = None,
) -> SenderRegistry:
    """Merge all contact sources into a single SenderRegistry.

    Priority (highest wins): CSV > wa_contacts > bare phone number.
    LID JIDs (WhatsApp privacy IDs) are resolved via jid_map in msgstore.
    """
    contacts: dict[str, str] = {}
    if wadb is not None:
        contacts.update(_load_wa_contacts(wadb))
    if csv_path is not None:
        contacts.update(load_contacts_csv(csv_path))
    if msgstore is not None:
        contacts.update(_resolve_lids(msgstore, contacts))
    logger.info(f"SenderRegistry built: {len(contacts)} contacts")
    return SenderRegistry(contacts=contacts)


def load_contacts_csv(path: Path) -> dict[str, str]:
    """Parse a Google Contacts CSV export into {normalized_phone: display_name}.

    Scans every column in each row; values whose digit-only form falls within
    [_MIN_PHONE_DIGITS, _MAX_PHONE_DIGITS] are treated as phone numbers.
    Numbers exported in international format (+972 50-123-4567) will match
    reliably; local-format numbers (050-123-4567) will not unless they happen
    to share the same digit string as the JID.
    """
    contacts: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8-sig") as f:  # utf-8-sig strips BOM from Google export
            for row in csv.DictReader(f):
                _add_csv_row(contacts, row)
    except OSError:
        logger.exception(f"Could not read contacts CSV: {path}")
        return {}
    logger.info(f"Loaded {len(contacts)} phone→name entries from {path.name}")
    return contacts


def _parse_phone(value: str) -> str | None:
    """Return digit-only form of value if it looks like a phone number, else None.

    Strips leading '00' (European international prefix) so that '00972...' normalises
    to '972...' the same way '+972...' does — matching WhatsApp JID format.
    """
    normalized = _NON_DIGIT.sub("", value.strip())
    normalized = normalized.removeprefix("00")
    if _MIN_PHONE_DIGITS <= len(normalized) <= _MAX_PHONE_DIGITS:
        return normalized
    return None


def _row_phones(row: dict[str, str]) -> set[str]:
    """Extract all phone-like values from a CSV row."""
    phones = set()
    for value in row.values():
        if not value:
            continue
        phone = _parse_phone(value)
        if phone:
            phones.add(phone)
    return phones


def _add_contact(contacts: dict[str, str], phone: str, name: str) -> None:
    """Insert phone→name, warning and skipping if the phone is already mapped to a different name."""
    if phone.startswith("0"):
        right_part = phone.lstrip("0")
        phone = f"972{right_part}"
    if phone not in contacts:
        contacts[phone] = name
        return
    if contacts[phone] != name:
        logger.warning(f"Duplicate phone {phone}: keeping '{contacts[phone]}', skipping '{name}'")


def _add_csv_row(contacts: dict[str, str], row: dict[str, str]) -> None:
    """Resolve name and phones from one CSV row and merge into contacts."""
    name = _display_name(row)
    if not name:
        return
    for phone in _row_phones(row):
        _add_contact(contacts, phone, name)


def _resolve_lids(msgstore: sqlite3.Connection, contacts: dict[str, str]) -> dict[str, str]:
    """Build {lid_user: display_name} for LIDs whose phone is already in contacts.

    jid_map maps lid_row_id → jid_row_id (the real phone JID), allowing LID-based
    chats to be resolved via the existing contacts dict.
    """
    try:
        rows = msgstore.execute("""
            SELECT lid_jid.user AS lid_user, phone_jid.user AS phone_user
            FROM jid_map jm
            JOIN jid lid_jid   ON jm.lid_row_id = lid_jid._id
            JOIN jid phone_jid ON jm.jid_row_id  = phone_jid._id
            WHERE lid_jid.server = 'lid'
              AND phone_jid.server = 's.whatsapp.net'
        """).fetchall()
    except sqlite3.OperationalError:
        logger.debug("jid_map not available — skipping LID resolution.")
        return {}

    resolved: dict[str, str] = {}
    for row in rows:
        name = contacts.get(row["phone_user"])
        if name:
            resolved[row["lid_user"]] = name
    logger.info(f"Resolved {len(resolved)} LID contacts via jid_map")
    return resolved


def _load_wa_contacts(wadb: sqlite3.Connection) -> dict[str, str]:
    """Load display names from wa.db wa_contacts table."""
    try:
        rows = wadb.execute(
            "SELECT jid, display_name FROM wa_contacts WHERE display_name IS NOT NULL AND display_name != ''"
        ).fetchall()
        return {row["jid"].split("@")[0]: row["display_name"] for row in rows}
    except sqlite3.OperationalError:
        logger.debug("wa_contacts table not found — no contact name resolution from wa.db.")
        return {}


def _display_name(row: dict[str, str]) -> str:
    parts = [row.get("First Name", ""), row.get("Middle Name", ""), row.get("Last Name", "")]
    name = " ".join(p.strip() for p in parts if p.strip())
    if not name:
        name = row.get("Nickname", "").strip()
    if not name:
        name = row.get("Organization Name", "").strip()
    return name
