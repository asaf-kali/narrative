from fastapi.testclient import TestClient
from seed_data import ALICE_NAME, SeededPaths

from narrative.api.server import create_api


def test_create_api_lifespan_builds_sender_registry(seeded_db_paths: SeededPaths) -> None:
    api = create_api(
        msgstore_path=seeded_db_paths.msgstore,
        wadb_path=seeded_db_paths.wadb,
        contacts_path=None,
        local_code=None,
        search_dir=None,
    )
    with TestClient(api):
        assert api.state.sender_registry.as_dict()["111111111"] == ALICE_NAME


def test_create_api_cors_allows_dev_frontend_origin(api_client: TestClient) -> None:
    resp = api_client.options(
        "/api/chats",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_create_api_without_search_dir_has_no_semantic_state(seeded_db_paths: SeededPaths) -> None:
    api = create_api(
        msgstore_path=seeded_db_paths.msgstore,
        wadb_path=seeded_db_paths.wadb,
        contacts_path=None,
        local_code=None,
        search_dir=None,
    )
    with TestClient(api):
        assert not hasattr(api.state, "state_db")
