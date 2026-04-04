import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="WhatsApp Analyzer — local dashboard for decrypted WhatsApp databases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --msgstore ../etc/msgstore.db --wadb ../etc/wa.db
  python main.py --msgstore ../etc/msgstore.db --port 8080

All processing is local. No data is sent to any external service.
""",
    )
    parser.add_argument("--msgstore", type=Path, default=None, help="Path to decrypted msgstore.db")
    parser.add_argument("--wadb", type=Path, default=None, help="Path to decrypted wa.db (optional, for contact names)")
    parser.add_argument("--port", type=int, default=8050, help="Port to run the dashboard on (default: 8050)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")

    parsed, _ = parser.parse_known_args(args)

    if parsed.msgstore is None:
        parser.print_help()
        return

    if not parsed.msgstore.exists():
        logger.error(f"msgstore.db not found: {parsed.msgstore}")
        sys.exit(1)

    from ui.app_factory import create_app  # noqa: PLC0415
    from ui.callbacks.charts import configure_paths  # noqa: PLC0415

    configure_paths(parsed.msgstore, parsed.wadb)

    debug = bool({"true": True, "1": True}.get(__import__("os").environ.get("DASH_DEBUG", "false").lower(), False))
    app = create_app(msgstore_path=parsed.msgstore, wadb_path=parsed.wadb)
    logger.info(f"Starting WhatsApp Analyzer on http://{parsed.host}:{parsed.port}")
    app.run(host=parsed.host, port=parsed.port, debug=debug)


if __name__ == "__main__":
    main()
