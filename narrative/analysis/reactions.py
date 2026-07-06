import logging
from typing import cast

import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EmojiCount(BaseModel):
    emoji: str
    count: int


class MessageReactions(BaseModel):
    emojis: list[EmojiCount]
    total: int
    reactors: list[str]


_LEADERBOARD_COLUMNS = ["sender_name", "reactions_received", "reactions_given"]
_TOP_REACTED_COLUMNS = ["message_id", "sender_name", "text", "message_type", "emojis", "total", "timestamp"]


def reaction_leaderboard(messages_df: pd.DataFrame, reactions_df: pd.DataFrame) -> pd.DataFrame:
    """Per participant: reactions received (on their messages) and reactions given."""
    if messages_df.empty or reactions_df.empty:
        return pd.DataFrame(columns=_LEADERBOARD_COLUMNS)
    authors = messages_df[["message_id", "sender_name"]].drop_duplicates("message_id")
    received_join = reactions_df.merge(authors, left_on="parent_message_id", right_on="message_id", how="inner")
    received = received_join.groupby("sender_name").size().reset_index(name="reactions_received")
    given = (
        reactions_df.groupby("reactor_name")
        .size()
        .reset_index(name="reactions_given")
        .rename(columns={"reactor_name": "sender_name"})
    )
    merged = received.merge(given, on="sender_name", how="outer").fillna(0)
    merged["reactions_received"] = merged["reactions_received"].astype(int)
    merged["reactions_given"] = merged["reactions_given"].astype(int)
    return merged.sort_values(["reactions_received", "reactions_given"], ascending=False)


def emoji_reaction_breakdown(reactions_df: pd.DataFrame) -> pd.DataFrame:
    """Count of each emoji used as a reaction."""
    if reactions_df.empty:
        return pd.DataFrame(columns=["emoji", "count"])
    counts = reactions_df.groupby("emoji").size().reset_index(name="count")
    return counts.sort_values("count", ascending=False)


def reactions_by_message(reactions_df: pd.DataFrame) -> dict[int, MessageReactions]:
    """Map each reacted-to message id to its emoji breakdown + reactor names."""
    if reactions_df.empty:
        return {}
    result: dict[int, MessageReactions] = {}
    for parent_id, group in reactions_df.groupby("parent_message_id"):
        emoji_counts = group["emoji"].value_counts()
        emojis = [EmojiCount(emoji=str(emoji), count=int(count)) for emoji, count in emoji_counts.items()]
        reactors = [name for name in group["reactor_name"].unique().tolist() if name]
        message_id = int(cast("int", parent_id))
        result[message_id] = MessageReactions(emojis=emojis, total=len(group), reactors=reactors)
    return result


def top_reacted_messages(messages_df: pd.DataFrame, reactions_df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    """Messages with the most reactions, annotated with author, text and emoji summary."""
    if messages_df.empty or reactions_df.empty:
        return pd.DataFrame(columns=_TOP_REACTED_COLUMNS)
    by_message = reactions_by_message(reactions_df)
    if not by_message:
        return pd.DataFrame(columns=_TOP_REACTED_COLUMNS)
    indexed = messages_df.drop_duplicates("message_id").set_index("message_id")
    rows = [_top_reacted_row(mid, reactions, indexed) for mid, reactions in by_message.items()]
    valid = [row for row in rows if row is not None]
    df = pd.DataFrame(valid, columns=_TOP_REACTED_COLUMNS)
    return df.sort_values("total", ascending=False).head(limit)


def merge_reactions(messages_df: pd.DataFrame, reactions_df: pd.DataFrame) -> pd.DataFrame:
    """Attach a scalar reactions_received count onto the messages DataFrame."""
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


def _top_reacted_row(message_id: int, reactions: MessageReactions, indexed: pd.DataFrame) -> dict[str, object] | None:
    if message_id not in indexed.index:
        return None
    message = indexed.loc[message_id]
    text = message.get("text_data")
    emoji_summary = " ".join(f"{item.emoji} {item.count}" for item in reactions.emojis)
    return {
        "message_id": message_id,
        "sender_name": str(message["sender_name"]),
        "text": str(text) if pd.notna(text) else None,
        "message_type": int(message["message_type"]),  # ty: ignore[invalid-argument-type]
        "emojis": emoji_summary,
        "total": reactions.total,
        "timestamp": message["timestamp"].strftime("%Y-%m-%dT%H:%M:%S"),
    }
