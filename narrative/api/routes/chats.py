import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query, Request

from narrative.db import cached
from narrative.db.loaders import chat_summaries
from narrative.models.chat import ChatSummary
from narrative.models.sender import SenderRegistry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chats", response_model=list[ChatSummary])
def list_chats(
    request: Request,
    search: Annotated[str | None, Query(description="Filter chats by name (case-insensitive)")] = None,
) -> list[ChatSummary]:
    msgstore: Path = request.app.state.msgstore_path
    registry: SenderRegistry = request.app.state.sender_registry
    rows = cached.chat_rows(msgstore_path=msgstore)
    return chat_summaries(rows=rows, registry=registry, search=search)
