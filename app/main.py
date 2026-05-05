import datetime
import logging
import os
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

logging.captureWarnings(True)  # noqa: FBT003


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

try:
    from semantic_search.indexer import run as _run_index
except ImportError:
    _run_index = None

cli = typer.Typer(no_args_is_help=True)


@cli.command()
def serve(
    msgstore: Annotated[Path, typer.Option(help="Path to decrypted msgstore.db")] = Path("data/msgstore.db"),
    wadb: Annotated[Path | None, typer.Option(help="Path to decrypted wa.db (optional, for contact names)")] = None,
    contacts: Annotated[Path | None, typer.Option(help="Google Contacts CSV export (optional)")] = None,
    local_code: Annotated[str, typer.Option(help="Country code for local-format phone numbers (e.g. 972)")] = "972",
    search_dir: Annotated[Path, typer.Option(help="Semantic search index directory")] = Path("data/search"),
    port: Annotated[int, typer.Option(help="Port to run on")] = 8050,
    host: Annotated[str, typer.Option(help="Host to bind to")] = "127.0.0.1",
    reload: Annotated[bool, typer.Option("--reload", help="Enable auto-reload (development mode)")] = False,
) -> None:
    """Run the Narrative analytics server."""
    if not msgstore.exists():
        logger.error(f"msgstore.db not found: {msgstore}")
        raise typer.Exit(code=1)

    logger.info(f"Starting Narrative on http://{host}:{port}")

    if reload:
        # uvicorn requires an import string to enable --reload; pass paths via env vars
        os.environ["WHATSAPP_MSGSTORE"] = str(msgstore)
        if wadb:
            os.environ["WHATSAPP_WADB"] = str(wadb)
        if contacts:
            os.environ["WHATSAPP_CONTACTS"] = str(contacts)
        if local_code:
            os.environ["WHATSAPP_LOCAL_CODE"] = local_code
        os.environ["WHATSAPP_SEARCH_DIR"] = str(search_dir)
        uvicorn.run(
            "api.asgi:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=["app"],
            log_config=_UVICORN_LOG_CONFIG,
        )
    else:
        from api.server import create_api  # noqa: PLC0415

        api = create_api(
            msgstore_path=msgstore,
            wadb_path=wadb,
            contacts_path=contacts,
            local_code=local_code,
            search_dir=search_dir,
        )
        uvicorn.run(api, host=host, port=port, log_config=_UVICORN_LOG_CONFIG)


@cli.command()
def index(
    msgstore: Annotated[Path, typer.Option(help="Path to decrypted msgstore.db")] = Path("data/msgstore.db"),
    wadb: Annotated[Path | None, typer.Option(help="Path to decrypted wa.db (optional)")] = None,
    search_dir: Annotated[Path, typer.Option(help="Semantic search index output directory")] = Path("data/search"),
    gap_seconds: Annotated[int, typer.Option(help="Inactivity gap in seconds to split sessions (default: 15 min)")] = 15
    * 60,
    batch_size: Annotated[int, typer.Option(help="Embedding batch size")] = 32,
) -> None:
    """Build or incrementally update the semantic search index."""
    if _run_index is None:
        logger.error("Semantic search deps not installed — run: uv sync --group semantic")
        raise typer.Exit(code=1)

    if not msgstore.exists():
        logger.error(f"msgstore.db not found: {msgstore}")
        raise typer.Exit(code=1)

    wadb_path = wadb if wadb and wadb.exists() else None
    _run_index(
        msgstore_path=msgstore,
        wadb_path=wadb_path,
        search_dir=search_dir,
        gap_seconds=gap_seconds,
        batch_size=batch_size,
    )


if __name__ == "__main__":
    cli()
