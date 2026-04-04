import pandas as pd
from analysis.timeline import active_days_count, daily_timeline, hourly_heatmap, monthly_timeline
from models.config import AnalysisConfig


def test_daily_timeline_shape(sample_messages_df: pd.DataFrame) -> None:
    config = AnalysisConfig()
    result = daily_timeline(sample_messages_df, config)
    assert not result.empty
    assert "date" in result.columns
    assert "count" in result.columns
    assert "sender_name" in result.columns


def test_monthly_timeline_shape(sample_messages_df: pd.DataFrame) -> None:
    config = AnalysisConfig()
    result = monthly_timeline(sample_messages_df, config)
    assert not result.empty
    assert "month" in result.columns


def test_hourly_heatmap_dimensions(sample_messages_df: pd.DataFrame) -> None:
    config = AnalysisConfig()
    heatmap = hourly_heatmap(sample_messages_df, config)
    assert heatmap.shape[1] == 24
    assert heatmap.shape[0] == 7


def test_active_days_count(sample_messages_df: pd.DataFrame) -> None:
    count = active_days_count(sample_messages_df)
    assert count >= 1


def test_empty_df_returns_empty(sample_messages_df: pd.DataFrame) -> None:
    empty = pd.DataFrame(columns=sample_messages_df.columns)
    config = AnalysisConfig()
    assert daily_timeline(empty, config).empty
    assert monthly_timeline(empty, config).empty
    assert active_days_count(empty) == 0
