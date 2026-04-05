import logging
from pathlib import Path
from typing import cast

from db.loaders import DataLoader, open_connection
from fastapi import APIRouter, Request
from models.chat import ChatSummary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chats", response_model=list[ChatSummary])
def list_chats(request: Request) -> list[ChatSummary]:
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    contact_names: dict[str, str] | None = request.app.state.contact_names
    logger.info("Loading chat list")
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        chats = DataLoader(db, contact_names=contact_names).load_chats()
    logger.info(f"Returning {len(chats)} chats")
    return cast("list[ChatSummary]", chats)
