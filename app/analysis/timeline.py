import logging

import pandas as pd
from analysis.base import analysis
from models.config import AnalysisConfig

logger = logging.getLogger(__name__)

_DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_HOURS = list(range(24))


@analysis(name="daily_timeline", label="Daily Timeline", page="timeline")
def daily_timeline(df: pd.DataFrame, _config: AnalysisConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", "sender_name", "count"])
    daily = df.groupby(["date", "sender_name"]).size().reset_index(name="count")
    daily["date"] = pd.to_datetime(daily["date"])
    return daily.sort_values("date")


@analysis(name="monthly_timeline", label="Monthly Timeline", page="timeline")
def monthly_timeline(df: pd.DataFrame, _config: AnalysisConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "sender_name", "count"])
    monthly = df.groupby(["month", "sender_name"]).size().reset_index(name="count")
    return monthly.sort_values("month")


@analysis(name="hourly_heatmap", label="Activity Heatmap", page="timeline")
def hourly_heatmap(df: pd.DataFrame, _config: AnalysisConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(0, index=_DAYS_ORDER, columns=_HOURS)
    return (
        df.groupby(["day_of_week", "hour"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=_DAYS_ORDER, columns=_HOURS, fill_value=0)
    )


def active_days_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    return int(df["date"].nunique())
