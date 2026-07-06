from narrative.models.sender import BROADCAST_SERVER, GROUP_SERVER, SenderRegistry


def test_resolve_sender_from_me_returns_me() -> None:
    registry = SenderRegistry(contacts={}, me_name="Me")
    sender = registry.resolve_sender(phone="", from_me=True)
    assert sender.sender_id == "me"
    assert sender.display_name == "Me"
    assert sender.phone == ""


def test_resolve_sender_known_contact() -> None:
    registry = SenderRegistry(contacts={"111": "Alice"})
    sender = registry.resolve_sender(phone="111", from_me=False)
    assert sender.display_name == "Alice"
    assert sender.sender_id == "111"
    assert sender.phone == "111"


def test_resolve_sender_unknown_contact_falls_back_to_phone() -> None:
    registry = SenderRegistry(contacts={})
    sender = registry.resolve_sender(phone="999", from_me=False)
    assert sender.display_name == "999"
    assert sender.sender_id == "999"


def test_resolve_sender_direct_chat_uses_chat_phone_when_sender_phone_empty() -> None:
    registry = SenderRegistry(contacts={"222": "Bob"})
    sender = registry.resolve_sender(phone="", from_me=False, chat_phone="222", is_group=False)
    assert sender.display_name == "Bob"
    assert sender.phone == "222"


def test_resolve_sender_group_chat_ignores_chat_phone_when_sender_phone_empty() -> None:
    registry = SenderRegistry(contacts={"222": "Bob"})
    sender = registry.resolve_sender(phone="", from_me=False, chat_phone="222", is_group=True)
    assert sender.display_name == "Unknown"
    assert sender.sender_id == "unknown"


def test_resolve_chat_name_prefers_subject() -> None:
    registry = SenderRegistry(contacts={})
    name = registry.resolve_chat_name("My Group", GROUP_SERVER, "555")
    assert name == "My Group"


def test_resolve_chat_name_group_fallback_without_subject() -> None:
    registry = SenderRegistry(contacts={})
    name = registry.resolve_chat_name(None, GROUP_SERVER, "555")
    assert name == "Group (555)"


def test_resolve_chat_name_direct_uses_contacts() -> None:
    registry = SenderRegistry(contacts={"333": "Carol"})
    name = registry.resolve_chat_name(None, "s.whatsapp.net", "333")
    assert name == "Carol"


def test_resolve_chat_name_direct_unknown_falls_back_to_phone() -> None:
    registry = SenderRegistry(contacts={})
    name = registry.resolve_chat_name(None, "s.whatsapp.net", "444")
    assert name == "444"


def test_resolve_chat_name_broadcast_server_is_not_group() -> None:
    registry = SenderRegistry(contacts={})
    name = registry.resolve_chat_name(None, BROADCAST_SERVER, "")
    assert name == "Unknown"


def test_me_name_property_reflects_constructor_arg() -> None:
    registry = SenderRegistry(contacts={}, me_name="Asaf")
    assert registry.me_name == "Asaf"


def test_as_dict_is_a_copy_not_a_reference() -> None:
    contacts = {"111": "Alice"}
    registry = SenderRegistry(contacts=contacts)
    result = registry.as_dict()
    result["222"] = "Injected"
    assert "222" not in registry.as_dict()
