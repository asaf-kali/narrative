import logging

import pandas as pd
from analysis.base import analysis
from models.config import AnalysisConfig
from models.message import AUDIO_TYPES, MEDIA_TYPES

logger = logging.getLogger(__name__)


@analysis(name="per_sender_stats", label="Participant Stats", page="participants")
def per_sender_stats(df: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["sender_name", "messages", "words", "avg_words", "media", "audio", "pct"])

    media_mask = df["message_type"].isin({t.value for t in MEDIA_TYPES})
    audio_mask = df["message_type"].isin({t.value for t in AUDIO_TYPES})
    text_mask = df["text_data"].notna()

    stats: pd.DataFrame = (
        df.groupby("sender_name")  # type: ignore[call-overload]
        .apply(
            lambda g: pd.Series(
                {
                    "messages": len(g),
                    "words": g.loc[g["text_data"].notna(), "text_data"].str.split().str.len().sum(),
                    "media": media_mask.loc[g.index].sum(),
                    "audio": audio_mask.loc[g.index].sum(),
                    "has_text": text_mask.loc[g.index].sum(),
                    # first non-empty phone; used by API to build a stable sender_id
                    "sender_phone": g.loc[g["sender_phone"].notna() & (g["sender_phone"] != ""), "sender_phone"].iloc[0]
                    if (g["sender_phone"] != "").any()
                    else "",
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )

    total = max(stats["messages"].sum(), 1)
    stats["pct"] = (stats["messages"] / total * 100).round(1)
    stats["avg_words"] = (stats["words"] / stats["has_text"].clip(lower=1)).round(1)

    min_msgs = config.min_messages_for_participant
    stats = stats[stats["messages"] >= min_msgs]
    return stats.sort_values("messages", ascending=False).drop(columns=["has_text"])
