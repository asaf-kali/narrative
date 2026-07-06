import pandas as pd

from narrative.analysis.reactions import (
    emoji_reaction_breakdown,
    merge_reactions,
    reaction_leaderboard,
    reactions_by_message,
    top_reacted_messages,
)


def _messages_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "message_id": [1, 2],
            "sender_name": ["Alice", "Bob"],
            "text_data": ["hello", "world"],
            "message_type": [0, 0],
            "timestamp": pd.to_datetime(["2024-01-10T09:00:00", "2024-01-10T09:05:00"]),
        }
    )


def _reactions_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "parent_message_id": [1, 1, 2],
            "reactor_name": ["Bob", "Bob", "Alice"],
            "emoji": ["\U0001f44d", "❤️", "\U0001f44d"],
        }
    )


def test_reaction_leaderboard_received_and_given() -> None:
    result = reaction_leaderboard(_messages_df(), _reactions_df()).set_index("sender_name")
    assert result.loc["Alice", "reactions_received"] == 2
    assert result.loc["Alice", "reactions_given"] == 1
    assert result.loc["Bob", "reactions_received"] == 1
    assert result.loc["Bob", "reactions_given"] == 2


def test_reaction_leaderboard_empty_when_no_reactions() -> None:
    result = reaction_leaderboard(_messages_df(), pd.DataFrame())
    assert result.empty


def test_emoji_reaction_breakdown_counts() -> None:
    result = emoji_reaction_breakdown(_reactions_df()).set_index("emoji")
    assert result.loc["\U0001f44d", "count"] == 2
    assert result.loc["❤️", "count"] == 1


def test_emoji_reaction_breakdown_empty() -> None:
    result = emoji_reaction_breakdown(pd.DataFrame())
    assert result.empty


def test_reactions_by_message_groups_emojis_and_reactors() -> None:
    result = reactions_by_message(_reactions_df())
    assert result[1].total == 2
    assert set(result[1].reactors) == {"Bob"}
    emoji_map = {e.emoji: e.count for e in result[1].emojis}
    assert emoji_map["\U0001f44d"] == 1
    assert emoji_map["❤️"] == 1


def test_reactions_by_message_empty_returns_empty_dict() -> None:
    assert reactions_by_message(pd.DataFrame()) == {}


def test_top_reacted_messages_ranks_by_total() -> None:
    result = top_reacted_messages(_messages_df(), _reactions_df())
    assert result.iloc[0]["message_id"] == 1
    assert result.iloc[0]["total"] == 2
    assert result.iloc[0]["sender_name"] == "Alice"


def test_top_reacted_messages_respects_limit() -> None:
    result = top_reacted_messages(_messages_df(), _reactions_df(), limit=1)
    assert len(result) == 1


def test_top_reacted_messages_empty_when_no_reactions() -> None:
    result = top_reacted_messages(_messages_df(), pd.DataFrame())
    assert result.empty


def test_merge_reactions_attaches_received_count() -> None:
    result = merge_reactions(_messages_df(), _reactions_df())
    row1 = result[result["message_id"] == 1].iloc[0]
    assert row1["reactions_received"] == 2


def test_merge_reactions_zero_when_no_reactions() -> None:
    result = merge_reactions(_messages_df(), pd.DataFrame())
    assert (result["reactions_received"] == 0).all()
