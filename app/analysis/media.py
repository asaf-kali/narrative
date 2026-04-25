import logging

import pandas as pd
from analysis.base import analysis  # ty: ignore[unresolved-import]
from models.config import AnalysisConfig  # ty: ignore[unresolved-import]
from models.message import MessageType  # ty: ignore[unresolved-import]

logger = logging.getLogger(__name__)

_TYPE_LABELS: dict[int, str] = {
    MessageType.IMAGE.value: "Image",
    MessageType.VIDEO.value: "Video",
    MessageType.AUDIO.value: "Voice Note",
    MessageType.DOCUMENT.value: "Document",
    MessageType.STICKER.value: "Sticker",
    MessageType.GIF.value: "GIF",
    MessageType.CONTACT.value: "Contact",
    MessageType.LOCATION.value: "Location",
}

_MEDIA_TYPE_VALUES: frozenset[int] = frozenset(_TYPE_LABELS.keys())


@analysis(name="media_breakdown", label="Media Breakdown", page="media")
def media_breakdown(df: pd.DataFrame, _config: AnalysisConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["type_label", "count"])
    media_df = df[df["message_type"].isin(_MEDIA_TYPE_VALUES)].copy()
    if media_df.empty:
        return pd.DataFrame(columns=["type_label", "count"])
    media_df["type_label"] = media_df["message_type"].map(_TYPE_LABELS).fillna("Other")
    counts = media_df.groupby("type_label").size().reset_index(name="count")
    return counts.sort_values("count", ascending=False)


@analysis(name="media_over_time", label="Media Over Time", page="media")
def media_over_time(df: pd.DataFrame, _config: AnalysisConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "type_label", "count"])
    media_df = df[df["message_type"].isin(_MEDIA_TYPE_VALUES)].copy()
    if media_df.empty:
        return pd.DataFrame(columns=["month", "type_label", "count"])
    media_df["type_label"] = media_df["message_type"].map(_TYPE_LABELS).fillna("Other")
    counts = media_df.groupby(["month", "type_label"]).size().reset_index(name="count")
    return counts.sort_values("month")
