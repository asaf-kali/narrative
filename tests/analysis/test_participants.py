import pandas as pd
from analysis.participants import per_sender_stats
from models.config import AnalysisConfig


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sender_name": ["Alice"] * 5 + ["Bob", "Bob"],
            "text_data": ["hello world"] * 5 + ["hi", None],
            "message_type": [0] * 5 + [0, 1],
            "sender_phone": ["111"] * 5 + ["222", "222"],
        }
    )


def test_per_sender_stats_computes_messages_words_media() -> None:
    config = AnalysisConfig(min_messages_for_participant=1)
    result = per_sender_stats(_df(), config).set_index("sender_name")
    assert result.loc["Alice", "messages"] == 5
    assert result.loc["Alice", "words"] == 10
    assert result.loc["Alice", "avg_words"] == 2.0
    assert result.loc["Bob", "messages"] == 2
    assert result.loc["Bob", "media"] == 1
    assert result.loc["Bob", "words"] == 1


def test_per_sender_stats_pct_sums_to_100() -> None:
    config = AnalysisConfig(min_messages_for_participant=1)
    result = per_sender_stats(_df(), config)
    assert result["pct"].sum() == 100.0


def test_per_sender_stats_filters_below_min_messages_threshold() -> None:
    result = per_sender_stats(_df(), AnalysisConfig())  # default min_messages_for_participant=5
    assert set(result["sender_name"]) == {"Alice"}


def test_per_sender_stats_sorted_by_messages_descending() -> None:
    config = AnalysisConfig(min_messages_for_participant=1)
    result = per_sender_stats(_df(), config)
    assert result["messages"].tolist() == sorted(result["messages"].tolist(), reverse=True)


def test_per_sender_stats_empty_df() -> None:
    result = per_sender_stats(pd.DataFrame(), AnalysisConfig())
    assert result.empty
    assert "sender_name" in result.columns


def test_per_sender_stats_includes_sender_phone_for_id_building() -> None:
    config = AnalysisConfig(min_messages_for_participant=1)
    result = per_sender_stats(_df(), config).set_index("sender_name")
    assert result.loc["Alice", "sender_phone"] == "111"
