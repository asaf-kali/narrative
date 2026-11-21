import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from narrative.db import cached
from narrative.db.loaders import chat_summaries
from narrative.models.chat import ChatSort, ChatSummary
from narrative.models.sender import SenderRegistry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chats", response_model=list[ChatSummary])
def list_chats(
    request: Request,
    search: Annotated[str | None, Query(description="Filter chats by name (case-insensitive)")] = None,
    sort: Annotated[ChatSort, Query(description="Order, always descending")] = ChatSort.LAST_MESSAGE,
    hide_empty: Annotated[bool, Query(description="Drop chats with no (non-system) messages")] = False,
    limit: Annotated[int, Query(ge=1)] = 100,
) -> list[ChatSummary]:
    msgstore: Path = request.app.state.msgstore_path
    registry: SenderRegistry = request.app.state.sender_registry
    rows = cached.chat_rows(msgstore_path=msgstore)
    return chat_summaries(rows=rows, registry=registry, search=search, sort=sort, hide_empty=hide_empty, limit=limit)


@router.get("/chats/{chat_id}", response_model=ChatSummary)
def get_chat(request: Request, chat_id: int) -> ChatSummary:
    msgstore: Path = request.app.state.msgstore_path
    registry: SenderRegistry = request.app.state.sender_registry
    rows = [r for r in cached.chat_rows(msgstore_path=msgstore) if r.chat_id == chat_id]
    summaries = chat_summaries(rows=rows, registry=registry)
    if not summaries:
        raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")
    return summaries[0]
