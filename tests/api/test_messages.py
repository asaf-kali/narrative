from fastapi.testclient import TestClient
from seed_data import CHAT_DIRECT, CHAT_GROUP, MSG_BOB_GROUP_HELLO


def test_messages_bounds_global(api_client: TestClient) -> None:
    resp = api_client.get("/api/messages/bounds")
    assert resp.status_code == 200
    body = resp.json()
    assert body["first_ts"] is not None
    assert body["last_ts"] is not None


def test_messages_bounds_scoped_to_chat(api_client: TestClient) -> None:
    resp = api_client.get("/api/messages/bounds", params={"chat_id": 999})
    assert resp.json() == {"first_ts": None, "last_ts": None}


def test_messages_metadata_totals(api_client: TestClient) -> None:
    resp = api_client.get("/api/messages/metadata")
    body = resp.json()
    assert body["total"] == 8
    assert "me" in body["available_sender_ids"]


def test_get_global_messages_returns_engagement_annotations(api_client: TestClient) -> None:
    resp = api_client.get("/api/messages", params={"chat_ids": [CHAT_GROUP]})
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    bob_msg = next(m for m in messages if m["message_id"] == MSG_BOB_GROUP_HELLO)
    assert bob_msg["reactions"] is not None
    assert bob_msg["reactions"]["total"] == 1


def test_get_global_messages_empty_result(api_client: TestClient) -> None:
    resp = api_client.get("/api/messages", params={"chat_ids": [999]})
    assert resp.json() == {"messages": []}


def test_get_global_messages_media_uses_type_label(api_client: TestClient) -> None:
    resp = api_client.get("/api/messages", params={"chat_ids": [CHAT_DIRECT]})
    messages = resp.json()["messages"]
    assert any(m["text"] == "[Image]" for m in messages)


def test_get_senders_resolves_names(api_client: TestClient) -> None:
    resp = api_client.get("/api/senders")
    assert resp.status_code == 200
    body = resp.json()
    me = next(s for s in body if s["sender_id"] == "me")
    assert me["sender_name"] == "Me"


def test_get_senders_filters_by_sender_ids(api_client: TestClient) -> None:
    resp = api_client.get("/api/senders", params={"sender_ids": ["me"]})
    body = resp.json()
    assert len(body) == 1
    assert body[0]["sender_id"] == "me"
