from unittest import mock

from fastapi.testclient import TestClient
from seed_data import CHAT_DIRECT, CHAT_GROUP, DAVE_NAME, ERIN_NAME, FRANK_NAME, MSG_ME_CONTACTS, MSG_ME_GROUP


def test_overview_returns_totals_and_breakdown(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_DIRECT}/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_messages"] == 3
    assert body["total_media"] == 1


def test_overview_empty_chat_returns_zeros(api_client: TestClient) -> None:
    resp = api_client.get("/api/chats/999/overview")
    body = resp.json()
    assert body["total_messages"] == 0
    assert body["sparkline"] == []


def test_timeline_daily(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_GROUP}/timeline", params={"period": "daily"})
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_timeline_monthly(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_GROUP}/timeline", params={"period": "monthly"})
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_timeline_empty_chat_returns_empty_list(api_client: TestClient) -> None:
    resp = api_client.get("/api/chats/999/timeline")
    assert resp.json() == []


def test_heatmap_shape(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_GROUP}/heatmap")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 7 * 24


def test_participants_excludes_below_threshold_by_default(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_GROUP}/participants")
    assert resp.status_code == 200
    assert resp.json() == []  # every participant has <5 messages in the seed data


def test_words_returns_frequencies(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_DIRECT}/words")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["frequencies"], list)


def test_emoji_extracts_from_group_chat(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_GROUP}/emoji")
    assert resp.status_code == 200
    body = resp.json()
    assert any(row["emoji"] == "\U0001f600" for row in body)


def test_chat_messages_endpoint_includes_reply_preview(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_GROUP}/messages")
    assert resp.status_code == 200
    body = resp.json()
    my_reply = next(m for m in body["messages"] if m["message_id"] == MSG_ME_GROUP)
    assert my_reply["reply_to"] is not None
    assert my_reply["reply_to"]["sender_name"] == "Bob Marley"


def test_chat_messages_empty_chat(api_client: TestClient) -> None:
    resp = api_client.get("/api/chats/999/messages")
    assert resp.json() == {"total": 0, "messages": []}


def test_media_breakdown_and_timeline(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_DIRECT}/media")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["breakdown"]) == 1  # one image message


def test_media_empty_chat(api_client: TestClient) -> None:
    resp = api_client.get("/api/chats/999/media")
    assert resp.json() == {"breakdown": [], "timeline": []}


def test_engagement_returns_all_four_sections(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_GROUP}/engagement")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"emoji_breakdown", "reaction_leaderboard", "top_reacted", "reply_leaderboard"}
    assert len(body["top_reacted"]) == 2


def test_global_network_coactivity_mode(api_client: TestClient) -> None:
    resp = api_client.get("/api/network")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "coactivity"


def test_global_network_reactions_mode(api_client: TestClient) -> None:
    resp = api_client.get("/api/network", params={"mode": "reactions"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "reactions"


def test_chat_network_coactivity_mode(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_GROUP}/network")
    assert resp.status_code == 200
    assert resp.json()["mode"] == "coactivity"


def test_chat_network_reactions_mode(api_client: TestClient) -> None:
    resp = api_client.get(f"/api/chats/{CHAT_GROUP}/network", params={"mode": "reactions"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "reactions"


def test_words_wordcloud_generation_failure_returns_empty_string(api_client: TestClient) -> None:
    """`_generate_wordcloud` swallows all errors and returns "" — verify that fallback path."""
    with mock.patch("wordcloud.WordCloud.generate", side_effect=RuntimeError("boom")):
        resp = api_client.get(f"/api/chats/{CHAT_DIRECT}/words")
    assert resp.status_code == 200
    assert resp.json()["wordcloud_png"] == ""


def test_chat_messages_endpoint_attaches_contact_cards(contacts_api_client: TestClient) -> None:
    resp = contacts_api_client.get(f"/api/chats/{CHAT_DIRECT}/messages")
    multi = next(m for m in resp.json()["messages"] if m["message_id"] == MSG_ME_CONTACTS)
    assert [c["name"] for c in multi["contacts"]] == [ERIN_NAME, FRANK_NAME]


def test_words_excludes_contact_card_names(contacts_api_client: TestClient) -> None:
    resp = contacts_api_client.get(f"/api/chats/{CHAT_DIRECT}/words")
    words = {w["word"] for w in resp.json()["frequencies"]}
    assert not words & set(DAVE_NAME.lower().split())


def test_media_breakdown_counts_both_contact_types(contacts_api_client: TestClient) -> None:
    resp = contacts_api_client.get(f"/api/chats/{CHAT_DIRECT}/media")
    breakdown = {b["type_label"]: b["count"] for b in resp.json()["breakdown"]}
    assert breakdown["Contact"] == 2
