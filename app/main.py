import logging
import os
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from logger import configure_logging

_LOG_CONFIG_DICT = configure_logging()
logger = logging.getLogger(__name__)

try:
    from semantic_search.indexer import run as _run_index
    from semantic_search.indexer import run_chat as _run_chat
except ImportError:
    _run_index = None
    _run_chat = None

cli = typer.Typer(no_args_is_help=True)
DEFAULT_INACTIVE_GAP_SECONDS = 60 * 60 * 2  # 2 hours

_ArgMsgstore = Annotated[Path, typer.Option(help="Path to decrypted msgstore.db")]
_ArgWadb = Annotated[Path | None, typer.Option(help="Path to decrypted wa.db (optional, for contact names)")]
_ArgContacts = Annotated[Path | None, typer.Option(help="Google Contacts CSV export (optional)")]
_ArgLocalCode = Annotated[str, typer.Option(help="Country code for local-format phone numbers (e.g. 972)")]
_ArgSearchDir = Annotated[Path, typer.Option(help="Semantic search index directory")]
_ArgPort = Annotated[int, typer.Option(help="Port to run on")]
_ArgHost = Annotated[str, typer.Option(help="Host to bind to")]
_ArgReload = Annotated[bool, typer.Option("--reload", help="Enable auto-reload (development mode)")]


@cli.command()
def serve(
    msgstore: _ArgMsgstore = Path("data/msgstore.db"),
    wadb: _ArgWadb = None,
    contacts: _ArgContacts = None,
    local_code: _ArgLocalCode = "972",
    search_dir: _ArgSearchDir = Path("data/search"),
    port: _ArgPort = 8050,
    host: _ArgHost = "127.0.0.1",
    reload: _ArgReload = False,
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
            log_config=_LOG_CONFIG_DICT,
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
        uvicorn.run(api, host=host, port=port, log_config=_LOG_CONFIG_DICT)


_ArgGapSeconds = Annotated[
    int, typer.Option(help=f"Inactivity gap in seconds to split sessions (default: {DEFAULT_INACTIVE_GAP_SECONDS})")
]
_ArgBatchSize = Annotated[int, typer.Option(help="Embedding batch size")]
_ArgChunkSize = Annotated[int, typer.Option(help="Messages read per DB chunk (streaming)")]
_ArgChatId = Annotated[int | None, typer.Option(help="Index only this chat ID (skip all others)")]
_ArgMinSessionChars = Annotated[
    int,
    typer.Option(help="Min text chars to flush a session on gap; keep appending if below threshold (0 = disabled)"),
]


@cli.command()
def index(
    msgstore: _ArgMsgstore = Path("data/msgstore.db"),
    wadb: _ArgWadb = None,
    search_dir: _ArgSearchDir = Path("data/search"),
    gap_seconds: _ArgGapSeconds = DEFAULT_INACTIVE_GAP_SECONDS,
    batch_size: _ArgBatchSize = 32,
    chunk_size: _ArgChunkSize = 500,
    chat_id: _ArgChatId = None,
    min_session_chars: _ArgMinSessionChars = 500,
) -> None:
    """Build or incrementally update the semantic search index."""
    if not msgstore.exists():
        logger.error(f"msgstore.db not found: {msgstore}")
        raise typer.Exit(code=1)

    wadb_path = wadb if wadb and wadb.exists() else None
    if chat_id is not None:
        if _run_chat is None:
            logger.error("Semantic search deps not installed — run: uv sync --group semantic")
            raise typer.Exit(code=1)
        _run_chat(
            chat_id=chat_id,
            msgstore_path=msgstore,
            wadb_path=wadb_path,
            search_dir=search_dir,
            gap_seconds=gap_seconds,
            batch_size=batch_size,
            chunk_size=chunk_size,
            min_session_chars=min_session_chars,
        )
    else:
        if _run_index is None:
            logger.error("Semantic search deps not installed — run: uv sync --group semantic")
            raise typer.Exit(code=1)
        _run_index(
            msgstore_path=msgstore,
            wadb_path=wadb_path,
            search_dir=search_dir,
            gap_seconds=gap_seconds,
            batch_size=batch_size,
            chunk_size=chunk_size,
            min_session_chars=min_session_chars,
        )


if __name__ == "__main__":
    cli()
