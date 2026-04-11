"""ASGI entrypoint for uvicorn import-string mode (required for --reload).

Paths are passed via environment variables set by main.py before uvicorn starts.
"""

import logging
import os
from pathlib import Path

from api.server import create_api

logger = logging.getLogger(__name__)

_msgstore = os.environ.get("WHATSAPP_MSGSTORE", "")
_wadb = os.environ.get("WHATSAPP_WADB")
_contacts = os.environ.get("WHATSAPP_CONTACTS")
_local_code = os.environ.get("WHATSAPP_LOCAL_CODE")

app = create_api(
    msgstore_path=Path(_msgstore),
    wadb_path=Path(_wadb) if _wadb else None,
    contacts_path=Path(_contacts) if _contacts else None,
    local_code=_local_code or None,
)
