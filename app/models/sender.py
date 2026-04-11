import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)

GROUP_SERVER = "g.us"
BROADCAST_SERVER = "broadcast"


class Sender(BaseModel):
    sender_id: str  # "me" | phone digits (e.g. "972521234567")
    display_name: str  # best-resolved name
    phone: str  # raw digits, empty string for "me"


class SenderRegistry:
    def __init__(self, contacts: dict[str, str], me_name: str = "Me") -> None:
        self._contacts = contacts  # {phone_digits: display_name}
        self._me = Sender(sender_id="me", display_name=me_name, phone="")

    def resolve_sender(
        self,
        phone: str,
        from_me: bool,
        chat_phone: str = "",
        is_group: bool = True,
    ) -> Sender:
        if from_me:
            return self._me
        effective_phone = phone or (chat_phone if not is_group else "")
        name = self._contacts.get(effective_phone) or effective_phone or "Unknown"
        return Sender(
            sender_id=effective_phone or "unknown",
            display_name=name,
            phone=effective_phone,
        )

    def resolve_chat_name(
        self,
        chat_subject: str | None,
        chat_server: str,
        chat_phone: str,
    ) -> str:
        if chat_subject:
            return chat_subject
        if chat_server == GROUP_SERVER:
            return f"Group ({chat_phone})"
        return self._contacts.get(chat_phone) or chat_phone or "Unknown"

    @property
    def me_name(self) -> str:
        return self._me.display_name

    def as_dict(self) -> dict[str, str]:
        """Back-compat for DataFrame pipeline: return {phone: display_name}."""
        return dict(self._contacts)
