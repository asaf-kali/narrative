import logging

import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ReplyPreview(BaseModel):
    quoted_message_id: int | None
    sender_name: str
    text: str | None
    message_type: int


_LEADERBOARD_COLUMNS = ["sender_name", "replies_received", "replies_sent"]


def reply_leaderboard(messages_df: pd.DataFrame, replies_df: pd.DataFrame) -> pd.DataFrame:
    """Per participant: replies received (their messages got quoted) and replies sent."""
    if messages_df.empty or replies_df.empty:
        return pd.DataFrame(columns=_LEADERBOARD_COLUMNS)
    authors = messages_df[["message_id", "sender_name"]].drop_duplicates("message_id")
    sent_join = replies_df.merge(authors, on="message_id", how="inner")
    sent = sent_join.groupby("sender_name").size().reset_index(name="replies_sent")
    received = (
        replies_df.groupby("quoted_sender_name")
        .size()
        .reset_index(name="replies_received")
        .rename(columns={"quoted_sender_name": "sender_name"})
    )
    merged = received.merge(sent, on="sender_name", how="outer").fillna(0)
    merged["replies_received"] = merged["replies_received"].astype(int)
    merged["replies_sent"] = merged["replies_sent"].astype(int)
    return merged.sort_values(["replies_received", "replies_sent"], ascending=False)


def replies_by_message(replies_df: pd.DataFrame) -> dict[int, ReplyPreview]:
    """Map each reply message id to a preview of the message it quoted."""
    if replies_df.empty:
        return {}
    result: dict[int, ReplyPreview] = {}
    for _, row in replies_df.iterrows():
        result[int(row["message_id"])] = _row_to_preview(row)
    return result


def _row_to_preview(row: pd.Series) -> ReplyPreview:
    quoted_id = row["quoted_message_id"]
    text = row["quoted_text"]
    return ReplyPreview(
        quoted_message_id=int(quoted_id) if pd.notna(quoted_id) else None,
        sender_name=str(row["quoted_sender_name"]),
        text=str(text) if pd.notna(text) else None,
        message_type=int(row["quoted_type"]),
    )
