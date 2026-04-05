import csv
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_NON_DIGIT = re.compile(r"\D")
_PHONE_COLS = [f"Phone {i} - Value" for i in range(1, 5)]


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


def _display_name(row: dict[str, str]) -> str:
    parts = [row.get("First Name", ""), row.get("Middle Name", ""), row.get("Last Name", "")]
    name = " ".join(p.strip() for p in parts if p.strip())
    if not name:
        name = row.get("Nickname", "").strip()
    if not name:
        name = row.get("Organization Name", "").strip()
    return name
