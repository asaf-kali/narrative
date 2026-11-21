import pandas as pd
from pydantic import BaseModel, ConfigDict


class InteractionFrames(BaseModel):
    """Raw interaction tables, as returned by DataLoader.load_replies/load_reactions/load_mentions."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    replies: pd.DataFrame
    reactions: pd.DataFrame
    mentions: pd.DataFrame
