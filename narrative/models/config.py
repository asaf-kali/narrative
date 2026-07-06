import logging
from datetime import datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AnalysisConfig(BaseModel):
    chat_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    exclude_system: bool = True
    min_messages_for_participant: int = 5

    def cache_key(self) -> str:
        return f"{self.chat_id}|{self.date_from}|{self.date_to}|{self.exclude_system}"
