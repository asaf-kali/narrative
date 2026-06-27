from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import lancedb
import pandas as pd
import pyarrow as pa
from pydantic import BaseModel
from semantic_search.session import SessionRecord

if TYPE_CHECKING:
    from lancedb.table import Table

logger = logging.getLogger(__name__)

_TABLE_NAME = "sessions"
_MIN_INDEX_ROWS = 256

# IVF_PQ is lossy; a wide probe + exact refine pass recovers most of the recall it drops.
_NPROBES = 20
_REFINE_FACTOR = 10

SCHEMA = pa.schema(
    [
        pa.field("session_id", pa.string()),
        pa.field("chat_id", pa.int32()),
        pa.field("chat_name", pa.string()),
        pa.field("timestamp_start", pa.int64()),
        pa.field("timestamp_end", pa.int64()),
        pa.field("text", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), 1024)),
    ]
)


class SearchHit(BaseModel):
    session_id: str
    chat_id: int
    chat_name: str
    timestamp_start: datetime
    timestamp_end: datetime
    text: str
    score: float


class VectorStore:
    def __init__(self, db: lancedb.DBConnection, table: Table) -> None:
        self._db = db
        self._table = table

    @classmethod
    def open(cls, search_dir: Path) -> VectorStore:
        lance_dir = search_dir / "lance"
        lance_dir.mkdir(parents=True, exist_ok=True)
        db = lancedb.connect(str(lance_dir))

        if _TABLE_NAME in db.table_names():
            table = db.open_table(_TABLE_NAME)
        else:
            table = db.create_table(_TABLE_NAME, schema=SCHEMA)

        return cls(db=db, table=table)

    def upsert_sessions(self, records: list[SessionRecord]) -> None:
        if not records:
            return
        df = pd.DataFrame(
            [
                {
                    "session_id": r.session_id,
                    "chat_id": r.chat_id,
                    "chat_name": r.chat_name,
                    "timestamp_start": int(r.timestamp_start.timestamp() * 1000),
                    "timestamp_end": int(r.timestamp_end.timestamp() * 1000),
                    "text": r.text,
                    "vector": r.vector,
                }
                for r in records
            ]
        )
        existing_ids = set(df["session_id"].tolist())
        id_expr = ", ".join(repr(sid) for sid in existing_ids)
        with contextlib.suppress(Exception):
            self._table.delete(f"session_id IN ({id_expr})")
        self._table.add(df)

    def delete_sessions(self, session_ids: list[str]) -> None:
        if not session_ids:
            return
        id_list = ", ".join(repr(sid) for sid in session_ids)
        self._table.delete(f"session_id IN ({id_list})")

    def build_index(self) -> None:
        count = self._table.count_rows()
        if count < _MIN_INDEX_ROWS:
            logger.info(f"Skipping ANN index build — only {count} rows")
            return
        logger.info("Building ANN index")
        self._table.create_index(metric="cosine", vector_column_name="vector", replace=True)
        logger.info("ANN index built")

    def build_fts_index(self) -> None:
        count = self._table.count_rows()
        if count == 0:
            return
        logger.info("Building full-text index")
        self._table.create_fts_index("text", replace=True, use_tantivy=False)
        logger.info("Full-text index built")

    def search(
        self,
        query_vec: list[float],
        limit: int = 10,
        chat_id_filter: int | None = None,
    ) -> list[SearchHit]:
        query = self._table.search(query_vec, vector_column_name="vector").metric("cosine").limit(limit)
        if self._has_index(column="vector"):
            query = query.nprobes(_NPROBES).refine_factor(_REFINE_FACTOR)
        if chat_id_filter is not None:
            query = query.where(f"chat_id = {chat_id_filter}", prefilter=True)
        results = query.to_list()
        return [self._row_to_hit(row=r, score=float(1.0 - r.get("_distance", 0.0))) for r in results]

    def search_text(
        self,
        query: str,
        limit: int = 10,
        chat_id_filter: int | None = None,
    ) -> list[SearchHit]:
        """BM25 full-text retrieval to widen the rerank candidate pool.

        Adds lexical (exact-term) matches the dense vector may miss. Best-effort:
        returns [] if no FTS index exists or the query cannot be parsed.
        """
        if not self._has_index(column="text"):
            return []
        with contextlib.suppress(Exception):
            fts = self._table.search(query, query_type="fts").limit(limit)
            if chat_id_filter is not None:
                fts = fts.where(f"chat_id = {chat_id_filter}")
            results = fts.to_list()
            return [self._row_to_hit(row=r, score=float(r.get("_score", 0.0))) for r in results]
        return []

    def _has_index(self, column: str) -> bool:
        with contextlib.suppress(Exception):
            return any(column in idx.columns for idx in self._table.list_indices())
        return False

    @staticmethod
    def _row_to_hit(row: dict[str, Any], score: float) -> SearchHit:
        return SearchHit(
            session_id=str(row["session_id"]),
            chat_id=int(row["chat_id"]),
            chat_name=str(row["chat_name"]),
            timestamp_start=datetime.fromtimestamp(int(row["timestamp_start"]) / 1000, tz=UTC),
            timestamp_end=datetime.fromtimestamp(int(row["timestamp_end"]) / 1000, tz=UTC),
            text=str(row.get("text", "")),
            score=score,
        )
