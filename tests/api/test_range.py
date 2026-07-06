from datetime import UTC, datetime

from fastapi.testclient import TestClient
from seed_data import T0


def test_range_detail_returns_messages_in_window(api_client: TestClient) -> None:
    date_from = datetime.fromtimestamp((T0 - 1_000) / 1000, tz=UTC).isoformat()
    date_to = datetime.fromtimestamp((T0 + 200_000) / 1000, tz=UTC).isoformat()
    resp = api_client.get("/api/range", params={"date_from": date_from, "date_to": date_to})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_messages"] == 8
    assert len(body["buckets"]) == 30


def test_range_detail_empty_window_returns_zero_messages(api_client: TestClient) -> None:
    date_from = datetime.fromtimestamp((T0 + 10_000_000) / 1000, tz=UTC).isoformat()
    date_to = datetime.fromtimestamp((T0 + 20_000_000) / 1000, tz=UTC).isoformat()
    resp = api_client.get("/api/range", params={"date_from": date_from, "date_to": date_to})
    body = resp.json()
    assert body["total_messages"] == 0
    assert body["messages"] == []
    assert len(body["buckets"]) == 30


def test_range_detail_missing_params_returns_422(api_client: TestClient) -> None:
    resp = api_client.get("/api/range")
    assert resp.status_code == 422
