"""Memoized whole-database aggregate queries.

msgstore.db is opened read-only and never changes while the server runs, so results that
scan every message (chat list, daily counts, sender counts, browse metadata) are computed
once per DB path and reused for the server's lifetime.
"""

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from narrative.db.connection import DBConnection
from narrative.db.loaders import DataLoader
from narrative.db.queries.chats import fetch_chats
from narrative.db.queries.messages import fetch_messages_metadata, fetch_sender_counts
from narrative.db.queries.stats import fetch_daily_counts
from narrative.db.row_types import MessagesMetadata, RawChatRow, RawSenderCount
from narrative.models.interactions import InteractionFrames
from narrative.tracing import span

logger = logging.getLogger(__name__)


class DailyCount(BaseModel):
    day: str
    count: int


class MetadataFilters(BaseModel):
    """Hashable browse filters, so they can key the metadata cache."""

    model_config = ConfigDict(frozen=True)

    chat_ids: frozenset[int] | None = None
    sender_ids: frozenset[str] | None = None
    date_from_ms: int | None = None
    date_to_ms: int | None = None
    search: str | None = None


_SINGLE_DB_CACHE_SIZE = 4
_METADATA_CACHE_SIZE = 256
_INTERACTIONS_CACHE_SIZE = 16


@lru_cache(maxsize=_SINGLE_DB_CACHE_SIZE)
def chat_rows(msgstore_path: Path) -> list[RawChatRow]:
    with span("db.chats"), DBConnection(msgstore_path=msgstore_path) as db:
        return list(fetch_chats(db.msgstore))


@lru_cache(maxsize=_SINGLE_DB_CACHE_SIZE)
def daily_counts(msgstore_path: Path) -> list[DailyCount]:
    with span("db.daily_counts"), DBConnection(msgstore_path=msgstore_path) as db:
        rows = fetch_daily_counts(db.msgstore)
    return [DailyCount(day=str(row["day"]), count=int(row["count"])) for row in rows]


@lru_cache(maxsize=_SINGLE_DB_CACHE_SIZE)
def sender_counts(msgstore_path: Path) -> list[RawSenderCount]:
    with span("db.sender_counts"), DBConnection(msgstore_path=msgstore_path) as db:
        return fetch_sender_counts(db.msgstore)


@lru_cache(maxsize=_METADATA_CACHE_SIZE)
def messages_metadata(msgstore_path: Path, filters: MetadataFilters) -> MessagesMetadata:
    chat_ids = sorted(filters.chat_ids) if filters.chat_ids else None
    sender_ids = sorted(filters.sender_ids) if filters.sender_ids else None
    with span("db.metadata"), DBConnection(msgstore_path=msgstore_path) as db:
        return fetch_messages_metadata(
            db.msgstore,
            chat_ids=chat_ids,
            date_from_ms=filters.date_from_ms,
            date_to_ms=filters.date_to_ms,
            sender_ids=sender_ids,
            search=filters.search,
        )


@lru_cache(maxsize=_INTERACTIONS_CACHE_SIZE)
def interactions(msgstore_path: Path, chat_id: int | None) -> InteractionFrames:
    """Load replies, reactions and mentions (whole DB, or one chat); ids need no contact registry."""
    with span("db.interactions"), DBConnection(msgstore_path=msgstore_path) as db:
        return DataLoader(db).load_interactions(chat_id=chat_id)


def clear_caches() -> None:
    for cached in (chat_rows, daily_counts, sender_counts, messages_metadata, interactions):
        cached.cache_clear()
