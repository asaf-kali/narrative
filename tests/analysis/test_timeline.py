import pandas as pd

from narrative.analysis.timeline import active_days_count, daily_timeline, hourly_heatmap, monthly_timeline
from narrative.models.config import AnalysisConfig

_CONFIG = AnalysisConfig()


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"]).date,
            "month": ["2024-01", "2024-01", "2024-01"],
            "day_of_week": ["Monday", "Monday", "Tuesday"],
            "hour": [9, 9, 14],
            "sender_name": ["Alice", "Bob", "Alice"],
        }
    )


def test_daily_timeline_groups_by_date_and_sender() -> None:
    result = daily_timeline(_df(), _CONFIG)
    assert len(result) == 3
    assert set(result.columns) == {"date", "sender_name", "count"}


def test_daily_timeline_empty_df() -> None:
    result = daily_timeline(pd.DataFrame(), _CONFIG)
    assert result.empty
    assert list(result.columns) == ["date", "sender_name", "count"]


def test_daily_timeline_sorted_by_date() -> None:
    result = daily_timeline(_df(), _CONFIG)
    dates = result["date"].tolist()
    assert dates == sorted(dates)


def test_monthly_timeline_groups_by_month_and_sender() -> None:
    result = monthly_timeline(_df(), _CONFIG)
    total = result["count"].sum()
    assert total == 3


def test_monthly_timeline_empty_df() -> None:
    result = monthly_timeline(pd.DataFrame(), _CONFIG)
    assert result.empty


def test_hourly_heatmap_shape_and_counts() -> None:
    heatmap = hourly_heatmap(_df(), _CONFIG)
    assert heatmap.shape == (7, 24)
    assert heatmap.loc["Monday", 9] == 2
    assert heatmap.loc["Tuesday", 14] == 1
    assert heatmap.loc["Sunday", 0] == 0


def test_hourly_heatmap_empty_df_returns_zero_grid() -> None:
    heatmap = hourly_heatmap(pd.DataFrame(), _CONFIG)
    assert heatmap.shape == (7, 24)
    assert (heatmap == 0).all().all()


def test_active_days_count() -> None:
    assert active_days_count(_df()) == 2


def test_active_days_count_empty_df_returns_zero() -> None:
    assert active_days_count(pd.DataFrame()) == 0
