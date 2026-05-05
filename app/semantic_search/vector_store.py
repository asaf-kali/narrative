from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import lancedb
import pandas as pd
import pyarrow as pa

if TYPE_CHECKING:
    from lancedb.table import Table

logger = logging.getLogger(__name__)

_TABLE_NAME = "sessions"
_MIN_INDEX_ROWS = 256

SCHEMA = pa.schema(
    [
        pa.field("session_id", pa.string()),
        pa.field("chat_id", pa.int32()),
        pa.field("chat_name", pa.string()),
        pa.field("timestamp_start", pa.int64()),
        pa.field("timestamp_end", pa.int64()),
        pa.field("vector", pa.list_(pa.float32(), 1024)),
    ]
)


@dataclass
class SearchHit:
    session_id: str
    chat_id: int
    chat_name: str
    timestamp_start: int  # ms UTC
    timestamp_end: int  # ms UTC
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

    def upsert_sessions(self, rows: list[dict[str, object]]) -> None:
        if not rows:
            return
        df = pd.DataFrame(rows)
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

    def search(
        self,
        query_vec: list[float],
        limit: int = 10,
        chat_id_filter: int | None = None,
    ) -> list[SearchHit]:
        query = self._table.search(query_vec, vector_column_name="vector").limit(limit).metric("cosine")
        if chat_id_filter is not None:
            query = query.where(f"chat_id = {chat_id_filter}", prefilter=True)
        results = query.to_list()
        return [
            SearchHit(
                session_id=str(r["session_id"]),
                chat_id=int(r["chat_id"]),
                chat_name=str(r["chat_name"]),
                timestamp_start=int(r["timestamp_start"]),
                timestamp_end=int(r["timestamp_end"]),
                score=float(1.0 - r.get("_distance", 0.0)),
            )
            for r in results
        ]
