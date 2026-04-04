import logging
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Self

logger = logging.getLogger(__name__)


class DBConnection:
    def __init__(self, msgstore_path: Path, wadb_path: Path | None = None) -> None:
        self._msgstore_path = msgstore_path
        self._wadb_path = wadb_path
        self._msgstore_conn: sqlite3.Connection | None = None
        self._wadb_conn: sqlite3.Connection | None = None

    @property
    def msgstore(self) -> sqlite3.Connection:
        if self._msgstore_conn is None:
            raise RuntimeError("DBConnection not opened — use as a context manager.")
        return self._msgstore_conn

    @property
    def wadb(self) -> sqlite3.Connection | None:
        return self._wadb_conn

    def __enter__(self) -> Self:
        logger.debug(f"Opening msgstore.db at {self._msgstore_path}")
        self._msgstore_conn = sqlite3.connect(
            f"file:{self._msgstore_path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        self._msgstore_conn.row_factory = sqlite3.Row

        if self._wadb_path and self._wadb_path.exists():
            logger.debug(f"Opening wa.db at {self._wadb_path}")
            self._wadb_conn = sqlite3.connect(
                f"file:{self._wadb_path}?mode=ro",
                uri=True,
                check_same_thread=False,
            )
            self._wadb_conn.row_factory = sqlite3.Row

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._msgstore_conn:
            self._msgstore_conn.close()
            self._msgstore_conn = None
        if self._wadb_conn:
            self._wadb_conn.close()
            self._wadb_conn = None
