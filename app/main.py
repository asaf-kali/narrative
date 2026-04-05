import argparse
import logging
import sys
from pathlib import Path

import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="WhatsApp Analyzer — local dashboard for decrypted WhatsApp databases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --msgstore ../etc/msgstore.db --wadb ../etc/wa.db
  python main.py --msgstore ../etc/msgstore.db --port 8050

All processing is local. No data is sent to any external service.
""",
    )
    parser.add_argument("--msgstore", type=Path, default=None, help="Path to decrypted msgstore.db")
    parser.add_argument("--wadb", type=Path, default=None, help="Path to decrypted wa.db (optional, for contact names)")
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

    from api.server import create_api  # noqa: PLC0415

    api = create_api(msgstore_path=parsed.msgstore, wadb_path=parsed.wadb)
    logger.info(f"Starting WhatsApp Analyzer on http://{parsed.host}:{parsed.port}")
    uvicorn.run(api, host=parsed.host, port=parsed.port, reload=parsed.reload)


if __name__ == "__main__":
    main()
