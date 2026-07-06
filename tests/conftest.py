from __future__ import annotations

import random
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from seed_data import SeededPaths, build_schema, build_wa_schema, seed_msgstore, seed_wa_contacts

from narrative import cache
from narrative.api.server import create_api
from narrative.db.connection import DBConnection
from narrative.db.contacts import build_sender_registry
from narrative.db.loaders import DataLoader
from narrative.models.config import AnalysisConfig
from narrative.models.sender import SenderRegistry


@pytest.fixture(autouse=True)
def _deterministic_random() -> None:
    """Network label-propagation shuffles with the global RNG — pin it for stable assertions."""
    random.seed(0)


@pytest.fixture(autouse=True)
def _clean_module_cache() -> Iterator[None]:
    """`app/cache.py` is a process-wide singleton keyed only on AnalysisConfig — isolate tests from it."""
    cache.clear_cache()
    yield
    cache.clear_cache()


@pytest.fixture
def msgstore_conn() -> Iterator[sqlite3.Connection]:
    """In-memory msgstore.db connection, seeded — for query-layer (app/db/queries) tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    build_schema(conn)
    seed_msgstore(conn)
    yield conn
    conn.close()


@pytest.fixture
def seeded_db_paths(tmp_path: Path) -> SeededPaths:
    """Real msgstore.db + wa.db files on disk, seeded — required by DBConnection (uses `mode=ro` URI)."""
    msgstore_path = tmp_path / "msgstore.db"
    wadb_path = tmp_path / "wa.db"

    msgstore_conn = sqlite3.connect(msgstore_path)
    build_schema(msgstore_conn)
    seed_msgstore(msgstore_conn)
    msgstore_conn.close()

    wadb_conn = sqlite3.connect(wadb_path)
    build_wa_schema(wadb_conn)
    seed_wa_contacts(wadb_conn)
    wadb_conn.close()

    return SeededPaths(msgstore=msgstore_path, wadb=wadb_path)


@pytest.fixture
def db_connection(seeded_db_paths: SeededPaths) -> Iterator[DBConnection]:
    with DBConnection(msgstore_path=seeded_db_paths.msgstore, wadb_path=seeded_db_paths.wadb) as db:
        yield db


@pytest.fixture
def sender_registry(seeded_db_paths: SeededPaths) -> SenderRegistry:
    with DBConnection(msgstore_path=seeded_db_paths.msgstore, wadb_path=seeded_db_paths.wadb) as db:
        return build_sender_registry(wadb=db.wadb, csv_path=None, msgstore=db.msgstore)


@pytest.fixture
def data_loader(db_connection: DBConnection, sender_registry: SenderRegistry) -> DataLoader:
    return DataLoader(db_connection, registry=sender_registry)


@pytest.fixture
def all_messages_df(data_loader: DataLoader) -> pd.DataFrame:
    """Full, unfiltered messages DataFrame (system messages included) for analysis-layer tests."""
    config = AnalysisConfig(chat_id=None, exclude_system=False)
    df: pd.DataFrame = data_loader.load_messages(config)
    return df


@pytest.fixture
def api_client(seeded_db_paths: SeededPaths) -> Iterator[TestClient]:
    api = create_api(
        msgstore_path=seeded_db_paths.msgstore,
        wadb_path=seeded_db_paths.wadb,
        contacts_path=None,
        local_code=None,
        search_dir=None,
    )
    with TestClient(api) as client:
        yield client
