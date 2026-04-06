import csv
import logging
import re
import sqlite3
from pathlib import Path

from models.sender import SenderRegistry

logger = logging.getLogger(__name__)

_NON_DIGIT = re.compile(r"\D")
_PHONE_COLS = [f"Phone {i} - Value" for i in range(1, 5)]
_JID_SUFFIX = "@s.whatsapp.net"


def build_sender_registry(
    wadb: sqlite3.Connection | None,
    csv_path: Path | None,
) -> SenderRegistry:
    """Merge all contact sources into a single SenderRegistry.

    Priority (highest wins): CSV > wa_contacts > bare phone number.
    """
    contacts: dict[str, str] = {}
    if wadb is not None:
        contacts.update(_load_wa_contacts(wadb))
    if csv_path is not None:
        contacts.update(load_contacts_csv(csv_path))
    logger.info(f"SenderRegistry built: {len(contacts)} contacts")
    return SenderRegistry(contacts=contacts)


def load_contacts_csv(path: Path) -> dict[str, str]:
    """Parse a Google Contacts CSV export into {normalized_phone: display_name}.

    Phone numbers are stripped of all non-digit characters so they can be
    joined against WhatsApp's jid.user field (which is digits only, e.g.
    '972501234567').  Numbers exported in international format (+972 50-123-4567)
    will match reliably; local-format numbers (050-123-4567) will not unless
    they happen to share the same digit string as the JID.
    """
    contacts: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8-sig") as f:  # utf-8-sig strips BOM from Google export
            for row in csv.DictReader(f):
                name = _display_name(row)
                if not name:
                    continue
                for col in _PHONE_COLS:
                    phone = row.get(col, "").strip()
                    if not phone:
                        continue
                    normalized = _NON_DIGIT.sub("", phone)
                    if normalized:
                        contacts[normalized] = name
    except OSError:
        logger.exception(f"Could not read contacts CSV: {path}")
        return {}
    logger.info(f"Loaded {len(contacts)} phone→name entries from {path.name}")
    return contacts


def _load_wa_contacts(wadb: sqlite3.Connection) -> dict[str, str]:
    """Load display names from wa.db wa_contacts table."""
    try:
        rows = wadb.execute(
            "SELECT jid, display_name FROM wa_contacts WHERE display_name IS NOT NULL AND display_name != ''"
        ).fetchall()
        return {row["jid"].replace(_JID_SUFFIX, ""): row["display_name"] for row in rows}
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
