import pandas as pd
from analysis.participants import per_sender_stats
from models.config import AnalysisConfig


def test_per_sender_stats_returns_df(sample_messages_df: pd.DataFrame) -> None:
    config = AnalysisConfig(min_messages_for_participant=1)
    result = per_sender_stats(sample_messages_df, config)
    assert not result.empty
    assert "sender_name" in result.columns
    assert "messages" in result.columns
    assert "pct" in result.columns


def test_percentages_sum_to_100(sample_messages_df: pd.DataFrame) -> None:
    config = AnalysisConfig(min_messages_for_participant=1)
    result = per_sender_stats(sample_messages_df, config)
    assert abs(result["pct"].sum() - 100.0) < 0.1


def test_min_messages_filter(sample_messages_df: pd.DataFrame) -> None:
    config_low = AnalysisConfig(min_messages_for_participant=1)
    config_high = AnalysisConfig(min_messages_for_participant=100)
    result_low = per_sender_stats(sample_messages_df, config_low)
    result_high = per_sender_stats(sample_messages_df, config_high)
    assert len(result_low) > len(result_high)


def test_empty_df_returns_empty(sample_messages_df: pd.DataFrame) -> None:
    empty = pd.DataFrame(columns=sample_messages_df.columns)
    config = AnalysisConfig()
    result = per_sender_stats(empty, config)
    assert result.empty
