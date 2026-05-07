"""Build or incrementally update the semantic search index."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from types import TracebackType
from typing import Self

from db.connection import DBConnection
from db.contacts import build_sender_registry
from db.loaders import DataLoader, IndexMessage
from db.queries.messages import count_messages
from semantic_search.chunker import Session, iterate_sessions
from semantic_search.embedder import Embedder
from semantic_search.session import SessionMeta, SessionRecord
from semantic_search.state import StateDB
from semantic_search.vector_store import VectorStore

logger = logging.getLogger(__name__)

_MIN_INDEX_ROWS = 256  # LanceDB requires this many rows before building an ANN index


@dataclass
class _ChatStream:
    messages: Iterator[IndexMessage]
    chat_name: str
    to_delete: list[str]


class Indexer:
    def __init__(
        self,
        msgstore_path: Path,
        wadb_path: Path | None,
        search_dir: Path,
        gap_seconds: int,
        batch_size: int,
        chunk_size: int = 500,
    ) -> None:
        self._msgstore_path = msgstore_path
        self._wadb_path = wadb_path
        self._state = StateDB(search_dir)
        self._store = VectorStore.open(search_dir)
        self._embedder = Embedder()
        self._gap_seconds = gap_seconds
        self._batch_size = batch_size
        self._chunk_size = chunk_size

    def __enter__(self) -> Self:
        self._db = DBConnection(msgstore_path=self._msgstore_path, wadb_path=self._wadb_path).__enter__()
        registry = build_sender_registry(wadb=self._db.wadb, csv_path=None, msgstore=self._db.msgstore, local_code=None)
        self._loader = DataLoader(db=self._db, registry=registry)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._db.__exit__(exc_type, exc_val, exc_tb)
        self._state.close()

    def run(self) -> None:
        known_chats = set(self._state.all_chat_ids())
        all_chat_ids = _get_all_chat_ids(self._db.msgstore)
        is_first_run = not known_chats

        total = count_messages(self._db.msgstore)
        logger.info(f"Messages in DB: {total}")

        total_sessions = 0
        for i, chat_id in enumerate(all_chat_ids, 1):
            n = self._index_chat(chat_id=chat_id, known_chats=known_chats)
            total_sessions += n
            logger.info(f"[{i}/{len(all_chat_ids)}] chat {chat_id}: {n} sessions")

        if is_first_run and total_sessions >= _MIN_INDEX_ROWS:
            self._store.build_index()
        logger.info(f"Done — {total_sessions} sessions across {len(all_chat_ids)} chats")

    def _index_chat(self, chat_id: int, known_chats: set[int]) -> int:
        stream = self._open_chat_stream(chat_id=chat_id, known_chats=known_chats)
        if stream is None:
            return 0
        return self._write_sessions(stream=stream, chat_id=chat_id)

    def _open_chat_stream(self, chat_id: int, known_chats: set[int]) -> _ChatStream | None:
        max_indexed = self._state.get_max_indexed(chat_id) if chat_id in known_chats else 0
        last_session = self._state.get_last_session(chat_id) if chat_id in known_chats else None

        new_messages = self._loader.iter_chat_messages(
            chat_id=chat_id, chunk_size=self._chunk_size, after_id=max_indexed
        )
        first_msg = next(new_messages, None)
        if first_msg is None:
            return None

        to_delete: list[str] = []
        boundary: list[IndexMessage] = []
        if last_session is not None:
            boundary = self._loader.load_boundary_rows(
                chat_id=chat_id,
                min_id=last_session.min_message_id,
                max_id=last_session.max_message_id,
            )
            if boundary:
                to_delete = [last_session.session_id]

        all_messages = chain(boundary, [first_msg], new_messages)
        return _ChatStream(messages=all_messages, chat_name=first_msg.chat_name, to_delete=to_delete)

    def _write_sessions(self, stream: _ChatStream, chat_id: int) -> int:
        sessions_written = 0
        batch: list[Session] = []
        batch_to_delete = stream.to_delete

        for session in iterate_sessions(
            messages=stream.messages, chat_id=chat_id, chat_name=stream.chat_name, gap_seconds=self._gap_seconds
        ):
            batch.append(session)
            if len(batch) >= self._batch_size:
                self._flush(sessions=batch, to_delete=batch_to_delete)
                batch_to_delete = []
                sessions_written += len(batch)
                batch = []

        if batch:
            self._flush(sessions=batch, to_delete=batch_to_delete)
            sessions_written += len(batch)

        max_id = _get_max_message_id(conn=self._db.msgstore, chat_id=chat_id)
        self._state.upsert_state(chat_id=chat_id, max_id=max_id)
        return sessions_written

    def _flush(self, sessions: list[Session], to_delete: list[str]) -> None:
        vectors = self._embedder.embed([s.embed_text for s in sessions], batch_size=self._batch_size)
        if to_delete:
            self._store.delete_sessions(to_delete)
            for sid in to_delete:
                self._state.delete_session(sid)
        session_records = [
            SessionRecord(
                session_id=s.session_id,
                chat_id=s.chat_id,
                chat_name=s.chat_name,
                timestamp_start=s.timestamp_start,
                timestamp_end=s.timestamp_end,
                vector=v,
            )
            for s, v in zip(sessions, vectors, strict=True)
        ]
        self._store.upsert_sessions(session_records)
        session_metadatas = [
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
        self._state.insert_sessions(session_metadatas)


# ── module-level entry point (called by main.py) ─────────────────────────────


def run(
    msgstore_path: Path,
    wadb_path: Path | None,
    search_dir: Path,
    gap_seconds: int,
    batch_size: int,
    chunk_size: int = 500,
) -> None:
    with Indexer(
        msgstore_path=msgstore_path,
        wadb_path=wadb_path,
        search_dir=search_dir,
        gap_seconds=gap_seconds,
        batch_size=batch_size,
        chunk_size=chunk_size,
    ) as indexer:
        indexer.run()


# ── private helpers ──────────────────────────────────────────────────────────


def _get_all_chat_ids(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute("SELECT DISTINCT chat_row_id FROM message WHERE chat_row_id > 0").fetchall()
    return [int(r[0]) for r in rows]


def _get_max_message_id(conn: sqlite3.Connection, chat_id: int) -> int:
    row = conn.execute("SELECT MAX(_id) FROM message WHERE chat_row_id = ?", (chat_id,)).fetchone()
    return int(row[0]) if row and row[0] is not None else 0
