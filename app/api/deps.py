import logging
from pathlib import Path
from typing import cast

import cache
import pandas as pd
from db.loaders import DataLoader, open_connection
from fastapi import Request
from models.config import AnalysisConfig

logger = logging.getLogger(__name__)


def get_df(request: Request, config: AnalysisConfig) -> pd.DataFrame:
    key = config.cache_key()
    cached = cache.get_cached(key)
    if cached is not None:
        logger.debug(f"Cache hit: {key}")
        return cast("pd.DataFrame", cached)
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    logger.info(f"Loading messages for chat_id={config.chat_id}")
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        df = DataLoader(db).load_messages(config)
    logger.info(f"Loaded {len(df)} messages")
    cache.set_cached(key, df)
    return cast("pd.DataFrame", df)
