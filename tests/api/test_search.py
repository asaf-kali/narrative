from fastapi.testclient import TestClient


def test_search_returns_matches(api_client: TestClient) -> None:
    resp = api_client.get("/api/search", params={"q": "carol"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert "carol" in body[0]["text"].lower()


def test_search_query_too_short_returns_400(api_client: TestClient) -> None:
    resp = api_client.get("/api/search", params={"q": "a"})
    assert resp.status_code == 400


def test_search_no_match_returns_empty_list(api_client: TestClient) -> None:
    resp = api_client.get("/api/search", params={"q": "nonexistentword"})
    assert resp.json() == []


def test_search_respects_limit(api_client: TestClient) -> None:
    resp = api_client.get("/api/search", params={"q": "hello", "limit": 1})
    assert len(resp.json()) == 1
