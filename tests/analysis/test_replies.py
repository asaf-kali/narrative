import pandas as pd

from narrative.analysis.replies import replies_by_message, reply_leaderboard


def _messages_df() -> pd.DataFrame:
    return pd.DataFrame({"message_id": [1, 2], "sender_name": ["Alice", "Bob"]})


def _replies_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "message_id": [2],
            "quoted_message_id": [1],
            "quoted_sender_name": ["Alice"],
            "quoted_text": ["hello"],
            "quoted_type": [0],
        }
    )


def test_reply_leaderboard_received_and_sent() -> None:
    result = reply_leaderboard(_messages_df(), _replies_df()).set_index("sender_name")
    assert result.loc["Alice", "replies_received"] == 1
    assert result.loc["Bob", "replies_sent"] == 1


def test_reply_leaderboard_empty_when_no_replies() -> None:
    assert reply_leaderboard(_messages_df(), pd.DataFrame()).empty


def test_replies_by_message_builds_preview() -> None:
    result = replies_by_message(_replies_df())
    preview = result[2]
    assert preview.quoted_message_id == 1
    assert preview.sender_name == "Alice"
    assert preview.text == "hello"
    assert preview.message_type == 0


def test_replies_by_message_none_quoted_id_when_nan() -> None:
    df = pd.DataFrame(
        {
            "message_id": [5],
            "quoted_message_id": [None],
            "quoted_sender_name": ["Carol"],
            "quoted_text": [None],
            "quoted_type": [0],
        }
    )
    preview = replies_by_message(df)[5]
    assert preview.quoted_message_id is None
    assert preview.text is None


def test_replies_by_message_empty_returns_empty_dict() -> None:
    assert replies_by_message(pd.DataFrame()) == {}
