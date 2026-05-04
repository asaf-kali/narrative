import argparse
import datetime
import logging
import os
import sys
from pathlib import Path

import uvicorn


class _Formatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: ARG002, N802
        return (
            datetime.datetime.fromtimestamp(record.created, tz=datetime.UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S.")
            + f"{record.msecs:03.0f}"
        )


_FMT = "[%(asctime)s] [%(levelname)-4.4s] %(message)s [%(name)s] [%(filename)s:%(lineno)d]"

_handler = logging.StreamHandler()
_handler.setFormatter(_Formatter(_FMT))
logging.basicConfig(level=logging.INFO, handlers=[_handler])

logger = logging.getLogger(__name__)

# Passed to uvicorn so the worker process inherits the same logging setup.
# uvicorn.access is silenced (no handlers, no propagation); everything else
# routes through the root logger which uses our custom formatter above.
_UVICORN_LOG_CONFIG: dict[str, object] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"()": _Formatter, "fmt": _FMT},
    },
    "handlers": {
        "default": {"class": "logging.StreamHandler", "formatter": "default"},
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": [], "level": "WARNING", "propagate": False},
    },
}


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Narrative — local analytics dashboard for WhatsApp chat history from decrypted SQLite databases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --msgstore ../data/msgstore.db --wadb ../data/wa.db
  python main.py --msgstore ../data/msgstore.db --port 8050

All processing is local. No data is sent to any external service.
""",
    )
    parser.add_argument(
        "--msgstore",
        type=Path,
        default="data/msgstore.db",
        help="Path to decrypted msgstore.db",
    )
    parser.add_argument(
        "--wadb",
        type=Path,
        default="data/wa.db",
        help="Path to decrypted wa.db (optional, for contact names)",
    )
    parser.add_argument(
        "--contacts",
        type=Path,
        default="data/contacts.csv",
        help="Google Contacts CSV export (optional, overrides wa.db for names)",
    )
    parser.add_argument(
        "--local-code",
        default="972",
        help="Country code for local-format phone numbers in contacts CSV (e.g. 972). "
        "When set, numbers starting with 0 are converted: '054...' → '<code>54...'",
    )
    parser.add_argument(
        "--search-dir",
        type=Path,
        default=None,
        help="Directory containing the semantic search index (optional)",
    )
    parser.add_argument("--port", type=int, default=8050, help="Port to run on (default: 8050)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development mode)")

    parsed, _ = parser.parse_known_args(args)

    if parsed.msgstore is None:
        parser.print_help()
        return

    if not parsed.msgstore.exists():
        logger.error(f"msgstore.db not found: {parsed.msgstore}")
        sys.exit(1)

    logger.info(f"Starting Narrative on http://{parsed.host}:{parsed.port}")

    if parsed.reload:
        # uvicorn requires an import string to enable --reload; pass paths via env vars
        os.environ["WHATSAPP_MSGSTORE"] = str(parsed.msgstore)
        if parsed.wadb:
            os.environ["WHATSAPP_WADB"] = str(parsed.wadb)
        if parsed.contacts:
            os.environ["WHATSAPP_CONTACTS"] = str(parsed.contacts)
        if parsed.local_code:
            os.environ["WHATSAPP_LOCAL_CODE"] = parsed.local_code
        uvicorn.run(
            "api.asgi:app",
            host=parsed.host,
            port=parsed.port,
            reload=True,
            reload_dirs=["app"],
            log_config=_UVICORN_LOG_CONFIG,
        )
    else:
        from api.server import create_api  # noqa: PLC0415

        api = create_api(
            msgstore_path=parsed.msgstore,
            wadb_path=parsed.wadb,
            contacts_path=parsed.contacts,
            local_code=parsed.local_code,
            search_dir=parsed.search_dir,
        )
        uvicorn.run(api, host=parsed.host, port=parsed.port, log_config=_UVICORN_LOG_CONFIG)


if __name__ == "__main__":
    main()
