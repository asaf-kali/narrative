import logging
from pathlib import Path
from typing import Annotated

from db.loaders import DataLoader, open_connection  # ty: ignore[unresolved-import]
from fastapi import APIRouter, Query, Request
from models.chat import ChatSummary  # ty: ignore[unresolved-import]
from models.sender import SenderRegistry  # ty: ignore[unresolved-import]

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chats", response_model=list[ChatSummary])
def list_chats(
    request: Request,
    search: Annotated[str | None, Query(description="Filter chats by name (case-insensitive)")] = None,
) -> list[ChatSummary]:
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry
    logger.info("Loading chat list (search=%r)", search)
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        chats: list[ChatSummary] = DataLoader(db, registry=registry).load_chats(search=search)
    logger.info("Returning %d chats", len(chats))
    return chats
