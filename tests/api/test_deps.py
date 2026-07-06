from unittest import mock

from db.loaders import DataLoader
from fastapi.testclient import TestClient
from seed_data import CHAT_DIRECT


def test_get_df_caches_across_calls(api_client: TestClient) -> None:
    """Hitting the overview endpoint twice with the same config must only load from DB once."""
    with mock.patch.object(DataLoader, "load_messages", wraps=DataLoader.load_messages, autospec=True) as spy:
        api_client.get(f"/api/chats/{CHAT_DIRECT}/overview")
        api_client.get(f"/api/chats/{CHAT_DIRECT}/overview")
    assert spy.call_count == 1


def test_get_df_distinguishes_by_config_cache_key(api_client: TestClient) -> None:
    with mock.patch.object(DataLoader, "load_messages", wraps=DataLoader.load_messages, autospec=True) as spy:
        api_client.get(f"/api/chats/{CHAT_DIRECT}/overview")
        api_client.get("/api/chats/999/overview")
    assert spy.call_count == 2


def test_get_df_returns_dataframe_with_expected_shape(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_DIRECT}/overview")
    assert resp.status_code == 200
    assert resp.json()["total_messages"] == 3
