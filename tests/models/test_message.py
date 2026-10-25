import pytest

from narrative.models.message import AUDIO_TYPES, CONTACT_TYPES, MEDIA_TYPES, MessageType, message_display_text


def test_message_type_values() -> None:
    assert MessageType.TEXT.value == 0
    assert MessageType.IMAGE.value == 1
    assert MessageType.AUDIO.value == 2
    assert MessageType.SYSTEM.value == 7
    assert MessageType.DOCUMENT.value == 9
    assert MessageType.STICKER.value == 13
    assert MessageType.GIF.value == 15


def test_media_types_excludes_audio_and_text() -> None:
    assert MessageType.AUDIO not in MEDIA_TYPES
    assert MessageType.TEXT not in MEDIA_TYPES
    assert MessageType.IMAGE in MEDIA_TYPES
    assert MessageType.VIDEO in MEDIA_TYPES
    assert MessageType.DOCUMENT in MEDIA_TYPES
    assert MessageType.STICKER in MEDIA_TYPES
    assert MessageType.GIF in MEDIA_TYPES


def test_audio_types_contains_only_audio() -> None:
    assert {MessageType.AUDIO} == AUDIO_TYPES


def test_contact_types() -> None:
    assert MessageType.CONTACT.value == 4
    assert MessageType.MULTI_CONTACT.value == 14
    assert {MessageType.CONTACT, MessageType.MULTI_CONTACT} == CONTACT_TYPES


@pytest.mark.parametrize(
    ("text_data", "message_type", "expected"),
    [
        ("hello", MessageType.TEXT, "hello"),
        (None, MessageType.TEXT, None),
        ("a caption", MessageType.IMAGE, "a caption"),
        (None, MessageType.IMAGE, "[Image]"),
        ("Dave", MessageType.CONTACT, "[Contact] Dave"),
        (None, MessageType.CONTACT, "[Contact]"),
        ("2 contacts", MessageType.MULTI_CONTACT, "[Contacts] 2 contacts"),
        ("", MessageType.MULTI_CONTACT, "[Contacts]"),
    ],
)
def test_message_display_text(text_data: str | None, message_type: MessageType, expected: str | None) -> None:
    assert message_display_text(text_data=text_data, message_type=message_type) == expected
