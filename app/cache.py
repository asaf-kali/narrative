import logging
from collections import OrderedDict

import pandas as pd

logger = logging.getLogger(__name__)

_MAX_SIZE = 20


class _LRUCache:
    def __init__(self, max_size: int) -> None:
        self._max_size = max_size
        self._store: OrderedDict[str, pd.DataFrame] = OrderedDict()

    def get(self, key: str) -> pd.DataFrame | None:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def set(self, key: str, df: pd.DataFrame) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        else:
            self._store[key] = df
            if len(self._store) > self._max_size:
                evicted = self._store.popitem(last=False)
                logger.debug(f"Cache evicted key: {evicted[0]}")

    def clear(self) -> None:
        self._store.clear()


_cache = _LRUCache(max_size=_MAX_SIZE)


def get_cached(key: str) -> pd.DataFrame | None:
    return _cache.get(key)


def set_cached(key: str, df: pd.DataFrame) -> None:
    _cache.set(key, df)


def clear_cache() -> None:
    _cache.clear()
