import logging
import threading
from pathlib import Path
from typing import cast

import cache  # ty: ignore[unresolved-import]
import pandas as pd
from db.loaders import DataLoader, open_connection  # ty: ignore[unresolved-import]
from fastapi import Request
from models.config import AnalysisConfig  # ty: ignore[unresolved-import]
from models.sender import SenderRegistry  # ty: ignore[unresolved-import]

logger = logging.getLogger(__name__)

# Per-key locks prevent concurrent requests from loading the same DataFrame twice.
_key_locks: dict[str, threading.Lock] = {}
_registry_lock = threading.Lock()


def _get_key_lock(key: str) -> threading.Lock:
    with _registry_lock:
        if key not in _key_locks:
            _key_locks[key] = threading.Lock()
        return _key_locks[key]


def get_df(request: Request, config: AnalysisConfig) -> pd.DataFrame:
    key = config.cache_key()
    cached = cache.get_cached(key)
    if cached is not None:
        return cast("pd.DataFrame", cached)

    with _get_key_lock(key):
        # Re-check after acquiring the lock — another thread may have loaded it.
        cached = cache.get_cached(key)
        if cached is not None:
            return cast("pd.DataFrame", cached)

        msgstore: Path = request.app.state.msgstore_path
        wadb: Path | None = request.app.state.wadb_path
        registry: SenderRegistry = request.app.state.sender_registry
        logger.info(f"Loading messages for chat_id [{config.chat_id}]")
        with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
            df = DataLoader(db, registry=registry).load_messages(config)
        logger.info(f"Loaded {len(df)} messages")
        cache.set_cached(key, df)
        return cast("pd.DataFrame", df)
