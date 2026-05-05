"""CLI tool to build or incrementally update the semantic search index."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
from db.connection import DBConnection
from db.contacts import build_sender_registry
from db.loaders import COL_CHAT_ROW_ID, COL_MESSAGE_ID, COL_TIMESTAMP, DataLoader
from models.config import AnalysisConfig
from semantic_search.chunker import Session, chunk_messages
from semantic_search.embedder import Embedder
from semantic_search.state import SessionMeta, StateDB
from semantic_search.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _ts_ms(df: pd.DataFrame) -> pd.Series[int]:
    ts = df[COL_TIMESTAMP]
    if pd.api.types.is_datetime64_any_dtype(ts):
        return ts.astype("int64") // 1_000_000  # type: ignore[no-any-return]
    return ts.astype("int64")  # type: ignore[no-any-return]


def _sessions_for_new_chats(full_df: pd.DataFrame, new_chats: set[int], gap_seconds: int) -> Iterator[Session]:
    if not new_chats:
        return
    logger.info(f"New chats: {len(new_chats)}")
    yield from chunk_messages(full_df[full_df[COL_CHAT_ROW_ID].isin(new_chats)], gap_seconds=gap_seconds)


def _sessions_for_updated_chat(
    full_df: pd.DataFrame,
    full_ts_ms: pd.Series[int],
    chat_id: int,
    max_indexed: int,
    gap_seconds: int,
    state: StateDB,
) -> tuple[Iterator[Session], list[str]]:
    chat_mask = full_df[COL_CHAT_ROW_ID] == chat_id
    new_df = full_df[chat_mask & (full_df[COL_MESSAGE_ID] > max_indexed)]
    if new_df.empty:
        return iter([]), []

    logger.info(f"Chat {chat_id}: {len(new_df)} new messages")
    to_delete: list[str] = []
    last = state.get_last_session(chat_id)
    if last is not None:
        boundary_mask = chat_mask & (full_ts_ms >= last.timestamp_start) & (full_df[COL_MESSAGE_ID] <= max_indexed)
        combined = pd.concat([full_df[boundary_mask], new_df]).drop_duplicates(COL_MESSAGE_ID)
        to_delete.append(last.session_id)
    else:
        combined = new_df

    return chunk_messages(combined, gap_seconds=gap_seconds), to_delete


def _embed_and_write(
    sessions: list[Session],
    to_delete: list[str],
    all_chats: set[int],
    full_df: pd.DataFrame,
    state: StateDB,
    store: VectorStore,
    embedder: Embedder,
    batch_size: int,
    is_first_run: bool,
) -> None:
    logger.info(f"Embedding {len(sessions)} sessions")
    vectors = embedder.embed([s.embed_text for s in sessions], batch_size=batch_size)

    rows: list[dict[str, object]] = [
        {
            "session_id": s.session_id,
            "chat_id": s.chat_id,
            "chat_name": s.chat_name,
            "timestamp_start": s.timestamp_start,
            "timestamp_end": s.timestamp_end,
            "vector": v,
        }
        for s, v in zip(sessions, vectors, strict=True)
    ]

    if to_delete:
        store.delete_sessions(to_delete)
        for sid in to_delete:
            state.delete_session(sid)

    store.upsert_sessions(rows)
    state.insert_sessions(
        [
            SessionMeta(
                session_id=s.session_id,
                chat_id=s.chat_id,
                min_message_id=s.min_message_id,
                max_message_id=s.max_message_id,
                timestamp_start=s.timestamp_start,
                timestamp_end=s.timestamp_end,
            )
            for s in sessions
        ]
    )

    for chat_id in all_chats:
        chat_max_id = int(full_df[full_df[COL_CHAT_ROW_ID] == chat_id][COL_MESSAGE_ID].max())
        state.upsert_state(chat_id, chat_max_id)

    if is_first_run:
        store.build_index()

    logger.info(f"Done — indexed {len(sessions)} sessions across {len(all_chats)} chats")


def _run(
    msgstore_path: Path,
    wadb_path: Path | None,
    search_dir: Path,
    gap_seconds: int,
    batch_size: int,
) -> None:
    state = StateDB(search_dir)
    store = VectorStore.open(search_dir)
    embedder = Embedder()

    with DBConnection(msgstore_path=msgstore_path, wadb_path=wadb_path) as db:
        registry = build_sender_registry(wadb=db.wadb, csv_path=None, msgstore=db.msgstore, local_code=None)
        loader = DataLoader(db=db, registry=registry)
        full_df = loader.load_messages(AnalysisConfig(exclude_system=True))

    if full_df.empty:
        logger.info("No messages found — nothing to index")
        return

    full_ts_ms = _ts_ms(full_df)
    known_chats = set(state.all_chat_ids())
    all_chats = {int(c) for c in full_df[COL_CHAT_ROW_ID].unique()}

    to_delete: list[str] = []
    session_iters: list[Iterator[Session]] = [_sessions_for_new_chats(full_df, all_chats - known_chats, gap_seconds)]

    for chat_id in known_chats:
        new_s, new_del = _sessions_for_updated_chat(
            full_df, full_ts_ms, chat_id, state.get_max_indexed(chat_id), gap_seconds, state
        )
        session_iters.append(new_s)
        to_delete.extend(new_del)

    sessions = [s for it in session_iters for s in it]
    if not sessions:
        logger.info("Index is up to date — nothing to embed")
        state.close()
        return

    _embed_and_write(
        sessions=sessions,
        to_delete=to_delete,
        all_chats=all_chats,
        full_df=full_df,
        state=state,
        store=store,
        embedder=embedder,
        batch_size=batch_size,
        is_first_run=not known_chats,
    )
    state.close()


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build or update the semantic search index.")
    parser.add_argument("--msgstore", type=Path, default=Path("data/msgstore.db"))
    parser.add_argument("--wadb", type=Path, default=None)
    parser.add_argument("--search-dir", type=Path, default=Path("data/search"), dest="search_dir")
    parser.add_argument("--gap-seconds", type=int, default=15 * 60, dest="gap_seconds")
    parser.add_argument("--batch-size", type=int, default=32, dest="batch_size")
    parsed = parser.parse_args(args)

    if not parsed.msgstore.exists():
        logger.error(f"msgstore.db not found: {parsed.msgstore}")
        sys.exit(1)

    wadb = parsed.wadb if parsed.wadb and parsed.wadb.exists() else None
    _run(
        msgstore_path=parsed.msgstore,
        wadb_path=wadb,
        search_dir=parsed.search_dir,
        gap_seconds=parsed.gap_seconds,
        batch_size=parsed.batch_size,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logging.captureWarnings(True)  # noqa: FBT003
    main()
