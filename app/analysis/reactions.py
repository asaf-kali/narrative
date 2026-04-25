import logging

import pandas as pd
from analysis.base import analysis  # ty: ignore[unresolved-import]
from models.config import AnalysisConfig  # ty: ignore[unresolved-import]

logger = logging.getLogger(__name__)


@analysis(name="reaction_leaderboard", label="Reaction Leaderboard", page="reactions")
def reaction_leaderboard(df: pd.DataFrame, _config: AnalysisConfig) -> pd.DataFrame:
    if df.empty or "emoji" not in df.columns:
        return pd.DataFrame(columns=["sender_name", "reactions_received", "reactions_given"])
    return df


def merge_reactions(messages_df: pd.DataFrame, reactions_df: pd.DataFrame) -> pd.DataFrame:
    if reactions_df.empty:
        messages_df["reactions_received"] = 0
        return messages_df
    received = (
        reactions_df.groupby("parent_message_id")
        .size()
        .reset_index(name="reactions_received")
        .rename(columns={"parent_message_id": "message_id"})
    )
    return messages_df.merge(received, on="message_id", how="left").fillna({"reactions_received": 0})
