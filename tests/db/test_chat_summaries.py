from narrative.db.loaders import chat_summaries
from narrative.db.row_types import RawChatRow
from narrative.models.chat import ChatSort
from narrative.models.sender import SenderRegistry

_REGISTRY = SenderRegistry(contacts={})


def _row(chat_id: int, subject: str, *, total: int, mine: int, last_ts: int | None) -> RawChatRow:
    return RawChatRow(
        chat_id=chat_id,
        chat_subject=subject,
        created_timestamp=None,
        chat_phone=str(chat_id),
        chat_server="g.us",
        message_count=total,
        my_message_count=mine,
        first_timestamp=last_ts,
        last_timestamp=last_ts,
    )


_ROWS = [
    _row(1, "alpha", total=10, mine=1, last_ts=3_000),
    _row(2, "beta", total=50, mine=0, last_ts=1_000),
    _row(3, "gamma", total=5, mine=4, last_ts=2_000),
    _row(4, "alpha empty", total=0, mine=0, last_ts=None),
]


def _ids(sort: ChatSort, *, search: str | None = None, hide_empty: bool = False, limit: int | None = 100) -> list[int]:
    summaries = chat_summaries(
        rows=_ROWS, registry=_REGISTRY, search=search, sort=sort, hide_empty=hide_empty, limit=limit
    )
    return [s.chat_id for s in summaries]


def test_sort_by_last_message_puts_never_active_last() -> None:
    assert _ids(ChatSort.LAST_MESSAGE) == [1, 3, 2, 4]


def test_sort_by_message_count() -> None:
    assert _ids(ChatSort.MESSAGES) == [2, 1, 3, 4]


def test_sort_by_mine() -> None:
    assert _ids(ChatSort.MINE) == [3, 1, 2, 4]


def test_hide_empty_drops_chats_without_messages() -> None:
    assert _ids(ChatSort.LAST_MESSAGE, hide_empty=True) == [1, 3, 2]


def test_search_is_limited_too() -> None:
    assert _ids(ChatSort.LAST_MESSAGE, search="ALPHA", limit=1) == [1]


def test_no_limit_returns_everything() -> None:
    assert len(_ids(ChatSort.LAST_MESSAGE, limit=None)) == len(_ROWS)
