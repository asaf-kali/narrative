from fastapi.testclient import TestClient


def test_daily_counts_excludes_system(api_client: TestClient) -> None:
    resp = api_client.get("/api/stats/daily")
    assert resp.status_code == 200
    body = resp.json()
    assert sum(row["count"] for row in body) == 8
    assert all(isinstance(row["date"], str) for row in body)
