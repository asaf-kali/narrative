"""Build or incrementally update the semantic search index."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from db.connection import DBConnection
from db.contacts import build_sender_registry
from db.loaders import COL_CHAT_NAME, DataLoader
from db.queries.messages import count_messages
from semantic_search.chunker import Session, chunk_chat_streaming
from semantic_search.embedder import Embedder
from semantic_search.state import SessionMeta, StateDB
from semantic_search.vector_store import VectorStore

logger = logging.getLogger(__name__)

_MIN_INDEX_ROWS = 256  # LanceDB requires this many rows before building an ANN index


def run(
    msgstore_path: Path,
    wadb_path: Path | None,
    search_dir: Path,
    gap_seconds: int,
    batch_size: int,
    chunk_size: int = 500,
) -> None:
    state = StateDB(search_dir)
    store = VectorStore.open(search_dir)
    embedder = Embedder()

    with DBConnection(msgstore_path=msgstore_path, wadb_path=wadb_path) as db:
        registry = build_sender_registry(wadb=db.wadb, csv_path=None, msgstore=db.msgstore, local_code=None)
        loader = DataLoader(db=db, registry=registry)

        total = count_messages(db.msgstore)
        logger.info(f"Messages in DB: {total}")

        known_chats = set(state.all_chat_ids())
        all_chat_ids = _get_all_chat_ids(db.msgstore)
        is_first_run = not known_chats
        total_sessions = 0

        for i, chat_id in enumerate(all_chat_ids, 1):
            n_sessions = _index_chat(
                chat_id=chat_id,
                conn=db.msgstore,
                loader=loader,
                state=state,
                store=store,
                embedder=embedder,
                known_chats=known_chats,
                gap_seconds=gap_seconds,
                batch_size=batch_size,
                chunk_size=chunk_size,
            )
            total_sessions += n_sessions
            logger.info(f"[{i}/{len(all_chat_ids)}] chat {chat_id}: {n_sessions} sessions")

    if is_first_run and total_sessions >= _MIN_INDEX_ROWS:
        store.build_index()
    state.close()
    logger.info(f"Done — {total_sessions} sessions across {len(all_chat_ids)} chats")


# ── private helpers ──────────────────────────────────────────────────────────


def _index_chat(
    chat_id: int,
    conn: sqlite3.Connection,
    loader: DataLoader,
    state: StateDB,
    store: VectorStore,
    embedder: Embedder,
    known_chats: set[int],
    gap_seconds: int,
    batch_size: int,
    chunk_size: int,
) -> int:
    max_indexed = state.get_max_indexed(chat_id) if chat_id in known_chats else 0
    last_session = state.get_last_session(chat_id) if chat_id in known_chats else None

    chunk_iter = loader.iter_chat_message_chunks(chat_id, chunk_size, after_id=max_indexed)
    first_chunk = next(chunk_iter, None)
    if first_chunk is None:
        return 0

    to_delete: list[str] = []
    if last_session is not None:
        boundary = loader.load_boundary_rows(chat_id, last_session.min_message_id, last_session.max_message_id)
        if boundary:
            first_chunk = boundary + first_chunk
            to_delete = [last_session.session_id]

    def _full_iter() -> Iterator[list[dict[str, object]]]:
        yield first_chunk
        yield from chunk_iter

    chat_name = str(first_chunk[0].get(COL_CHAT_NAME, ""))
    sessions_written = 0
    batch: list[Session] = []
    batch_to_delete = to_delete

    for session in chunk_chat_streaming(_full_iter(), chat_id, chat_name, gap_seconds):
        batch.append(session)
        if len(batch) >= batch_size:
            _flush(batch, batch_to_delete, store, state, embedder, batch_size)
            batch_to_delete = []
            sessions_written += len(batch)
            batch = []

    if batch:
        _flush(batch, batch_to_delete, store, state, embedder, batch_size)
        sessions_written += len(batch)

    state.upsert_state(chat_id, _get_max_message_id(conn, chat_id))
    return sessions_written


def _flush(
    sessions: list[Session],
    to_delete: list[str],
    store: VectorStore,
    state: StateDB,
    embedder: Embedder,
    batch_size: int,
) -> None:
    vectors = embedder.embed([s.embed_text for s in sessions], batch_size=batch_size)
    if to_delete:
        store.delete_sessions(to_delete)
        for sid in to_delete:
            state.delete_session(sid)
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


def _get_all_chat_ids(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute("SELECT DISTINCT chat_row_id FROM message WHERE chat_row_id > 0").fetchall()
    return [int(r[0]) for r in rows]


def _get_max_message_id(conn: sqlite3.Connection, chat_id: int) -> int:
    row = conn.execute("SELECT MAX(_id) FROM message WHERE chat_row_id = ?", (chat_id,)).fetchone()
    return int(row[0]) if row and row[0] is not None else 0
