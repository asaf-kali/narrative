"""Build or incrementally update the semantic search index."""

from __future__ import annotations

import logging
import sqlite3
import statistics
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from types import TracebackType
from typing import Self

import tqdm as tqdm_lib
from db.connection import DBConnection
from db.contacts import build_sender_registry
from db.loaders import DataLoader, IndexMessage
from db.queries.messages import count_messages, count_messages_for_chat, get_max_message_id_for_chat
from semantic_search.chunker import iterate_sessions
from semantic_search.embedder import Embedder
from semantic_search.session import Session, SessionRecord
from semantic_search.state import StateDB
from semantic_search.vector_store import VectorStore
from tqdm.contrib.logging import logging_redirect_tqdm

logger = logging.getLogger(__name__)

_MIN_INDEX_ROWS = 256  # LanceDB requires this many rows before building an ANN index


@dataclass
class _IndexStats:
    message_counts: list[int] = field(default_factory=list)
    durations_sec: list[float] = field(default_factory=list)
    embed_time_sec: float = 0.0

    @property
    def session_count(self) -> int:
        return len(self.message_counts)

    def record_batch(self, sessions: list[Session], embed_elapsed: float) -> None:
        for s in sessions:
            self.message_counts.append(s.message_count)
            self.durations_sec.append((s.timestamp_end - s.timestamp_start).total_seconds())
        self.embed_time_sec += embed_elapsed

    def merge(self, other: _IndexStats) -> None:
        self.message_counts.extend(other.message_counts)
        self.durations_sec.extend(other.durations_sec)
        self.embed_time_sec += other.embed_time_sec

    def inline_str(self) -> str:
        if not self.message_counts:
            return "no sessions"
        avg_msgs = statistics.mean(self.message_counts)
        med_msgs = statistics.median(self.message_counts)
        avg_dur = statistics.mean(self.durations_sec)
        med_dur = statistics.median(self.durations_sec)
        return (
            f"msgs avg={avg_msgs:.1f} med={med_msgs:.0f} | "
            f"dur avg={avg_dur:.0f}s med={med_dur:.0f}s | "
            f"embed={self.embed_time_sec:.1f}s"
        )

    def log_summary(self) -> None:
        n = self.session_count
        if n == 0:
            logger.info("Index stats: no sessions written")
            return
        logger.info(f"Index stats: {n} sessions | {self.inline_str()}")


@dataclass
class _ChatStream:
    messages: Iterator[IndexMessage]
    chat_name: str
    to_delete: list[str]
    total_messages: int


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
        conn = DBConnection(msgstore_path=self._msgstore_path, wadb_path=self._wadb_path)
        self._db = conn.__enter__()
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

        global_stats = _IndexStats()
        with logging_redirect_tqdm():
            for i, chat_id in enumerate(all_chat_ids, 1):
                chat_stats = self._index_chat(chat_id=chat_id, known_chats=known_chats)
                global_stats.merge(chat_stats)
                n = chat_stats.session_count
                log_prefix = f"{i}/{len(all_chat_ids)}] chat {chat_id}"
                if n:
                    logger.info(f"[{log_prefix}: {n} sessions | {chat_stats.inline_str()}")
                else:
                    logger.info(f"[{log_prefix}: up to date")

        if is_first_run and global_stats.session_count >= _MIN_INDEX_ROWS:
            self._store.build_index()
        logger.info(f"Done — {global_stats.session_count} sessions across {len(all_chat_ids)} chats")
        global_stats.log_summary()

    def index_single_chat(self, chat_id: int) -> None:
        known_chats = set(self._state.all_chat_ids())
        with logging_redirect_tqdm():
            chat_stats = self._index_chat(chat_id=chat_id, known_chats=known_chats)
        n = chat_stats.session_count
        if n:
            logger.info(f"chat {chat_id}: {n} sessions | {chat_stats.inline_str()}")
        else:
            logger.info(f"chat {chat_id}: up to date")
        chat_stats.log_summary()

    def _index_chat(self, chat_id: int, known_chats: set[int]) -> _IndexStats:
        stream = self._open_chat_stream(chat_id=chat_id, known_chats=known_chats)
        if stream is None:
            return _IndexStats()
        return self._index_sessions(stream=stream, chat_id=chat_id)

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

        new_count = count_messages_for_chat(conn=self._db.msgstore, chat_id=chat_id, after_id=max_indexed)
        total_messages = new_count + len(boundary)
        all_messages = chain(boundary, [first_msg], new_messages)
        return _ChatStream(
            messages=all_messages,
            chat_name=first_msg.chat_name,
            to_delete=to_delete,
            total_messages=total_messages,
        )

    def _index_sessions(self, stream: _ChatStream, chat_id: int) -> _IndexStats:
        stats = _IndexStats()
        batch: list[Session] = []
        batch_to_delete = stream.to_delete

        progress = tqdm_lib.tqdm(
            stream.messages,
            total=stream.total_messages,
            desc=f"Chat {chat_id}",
            unit="msg",
            file=sys.stdout,
            leave=False,
            dynamic_ncols=True,
        )
        session_iterator = iterate_sessions(
            messages=progress, chat_id=chat_id, chat_name=stream.chat_name, gap_seconds=self._gap_seconds
        )
        for session in session_iterator:
            batch.append(session)
            if len(batch) >= self._batch_size:
                self._flush(sessions=batch, to_delete=batch_to_delete, stats=stats)
                batch_to_delete = []
                batch = []

        if batch:
            self._flush(sessions=batch, to_delete=batch_to_delete, stats=stats)

        max_id = get_max_message_id_for_chat(conn=self._db.msgstore, chat_id=chat_id)
        self._state.upsert_state(chat_id=chat_id, max_id=max_id)
        return stats

    def _flush(self, sessions: list[Session], to_delete: list[str], stats: _IndexStats) -> None:
        embed_start = time.monotonic()
        vectors = self._embedder.embed([s.embed_text for s in sessions], batch_size=self._batch_size)
        embed_elapsed = time.monotonic() - embed_start
        stats.record_batch(sessions=sessions, embed_elapsed=embed_elapsed)
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
        self._state.insert_sessions(sessions)


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


def run_chat(
    chat_id: int,
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
        indexer.index_single_chat(chat_id=chat_id)


# ── private helpers ──────────────────────────────────────────────────────────


def _get_all_chat_ids(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute("SELECT DISTINCT chat_row_id FROM message WHERE chat_row_id > 0").fetchall()
    return [int(r[0]) for r in rows]
