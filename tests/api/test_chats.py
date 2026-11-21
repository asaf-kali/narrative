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


def test_list_chats_includes_my_message_count(api_client: TestClient) -> None:
    body = api_client.get("/api/chats").json()
    group = next(c for c in body if c["chat_id"] == CHAT_GROUP)
    assert group["my_message_count"] == 1  # "me in group"


def test_list_chats_sort_by_message_count(api_client: TestClient) -> None:
    body = api_client.get("/api/chats", params={"sort": "messages"}).json()
    counts = [c["message_count"] for c in body]
    assert counts == sorted(counts, reverse=True)


def test_list_chats_sort_by_mine(api_client: TestClient) -> None:
    body = api_client.get("/api/chats", params={"sort": "mine"}).json()
    counts = [c["my_message_count"] for c in body]
    assert counts == sorted(counts, reverse=True)


def test_list_chats_rejects_unknown_sort(api_client: TestClient) -> None:
    assert api_client.get("/api/chats", params={"sort": "bogus"}).status_code == 422


def test_list_chats_limit_applies(api_client: TestClient) -> None:
    assert len(api_client.get("/api/chats", params={"limit": 2}).json()) == 2


def test_get_chat_by_id(api_client: TestClient) -> None:
    body = api_client.get(f"/api/chats/{CHAT_GROUP}").json()
    assert body["display_name"] == GROUP_SUBJECT


def test_get_chat_unknown_id_is_404(api_client: TestClient) -> None:
    assert api_client.get("/api/chats/999").status_code == 404
