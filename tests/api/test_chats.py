from fastapi.testclient import TestClient
from seed_data import CHAT_BROADCAST, CHAT_DIRECT, CHAT_GROUP, GROUP_SUBJECT


def test_list_chats_returns_all(api_client: TestClient) -> None:
    resp = api_client.get("/api/chats")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    ids = {c["chat_id"] for c in body}
    assert ids == {CHAT_DIRECT, CHAT_GROUP, CHAT_BROADCAST}


def test_list_chats_search_filters(api_client: TestClient) -> None:
    resp = api_client.get("/api/chats", params={"search": "test group"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["display_name"] == GROUP_SUBJECT


def test_list_chats_search_no_match(api_client: TestClient) -> None:
    resp = api_client.get("/api/chats", params={"search": "zzz"})
    assert resp.json() == []
