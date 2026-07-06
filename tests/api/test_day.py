from fastapi.testclient import TestClient
from seed_data import T0, local_date


def test_day_detail_returns_messages_for_date(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/day/{local_date(T0)}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_messages"] == 8
    assert body["active_chats"] == 3


def test_day_detail_no_messages_returns_zeros(api_client: TestClient) -> None:
    resp = api_client.get("/api/day/1999-01-01")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_messages"] == 0
    assert body["messages"] == []


def test_day_detail_invalid_date_returns_400(api_client: TestClient) -> None:
    resp = api_client.get("/api/day/not-a-date")
    assert resp.status_code == 400


def test_day_detail_media_message_uses_type_label(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/day/{local_date(T0)}")
    body = resp.json()
    texts = [m["text"] for m in body["messages"]]
    assert "[Image]" in texts
    assert "[Audio]" in texts
