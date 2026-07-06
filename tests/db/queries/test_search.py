import sqlite3

from narrative.db.queries.search import _escape_like, search_messages


def test_escape_like_escapes_percent_underscore_backslash() -> None:
    assert _escape_like("50%_off\\") == "50\\%\\_off\\\\"


def test_escape_like_leaves_plain_text_untouched() -> None:
    assert _escape_like("hello world") == "hello world"


def test_search_messages_matches_substring(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(search_messages(msgstore_conn, "carol"))
    assert len(rows) == 1
    assert "carol" in rows[0].text_data.lower()


def test_search_messages_only_matches_text_type(msgstore_conn: sqlite3.Connection) -> None:
    # "hello" appears in three text messages (Alice, Bob, Carol) but never in media placeholders
    rows = list(search_messages(msgstore_conn, "hello"))
    assert len(rows) == 3
    assert all(r.text_data for r in rows)


def test_search_messages_respects_limit(msgstore_conn: sqlite3.Connection) -> None:
    rows = list(search_messages(msgstore_conn, "hello", limit=1))
    assert len(rows) == 1


def test_search_messages_no_match_returns_empty(msgstore_conn: sqlite3.Connection) -> None:
    assert list(search_messages(msgstore_conn, "nonexistentword")) == []


def test_search_messages_percent_in_query_is_literal(msgstore_conn: sqlite3.Connection) -> None:
    """A literal '%' in the user's query must not act as a SQL wildcard."""
    assert list(search_messages(msgstore_conn, "100%")) == []
