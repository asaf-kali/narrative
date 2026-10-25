import pytest

from narrative.models.message import AUDIO_TYPES, CONTACT_TYPES, MEDIA_TYPES, MessageType, message_display_text


def test_message_type_values() -> None:
    assert MessageType.TEXT.value == 0
    assert MessageType.IMAGE.value == 1
    assert MessageType.AUDIO.value == 2
    assert MessageType.SYSTEM.value == 7
    assert MessageType.DOCUMENT.value == 9
    assert MessageType.GIF.value == 13
    assert MessageType.REVOKED.value == 15
    assert MessageType.LIVE_LOCATION.value == 16
    assert MessageType.STICKER.value == 20


def test_media_types_excludes_audio_and_text() -> None:
    assert MessageType.AUDIO not in MEDIA_TYPES
    assert MessageType.TEXT not in MEDIA_TYPES
    assert MessageType.IMAGE in MEDIA_TYPES
    assert MessageType.VIDEO in MEDIA_TYPES
    assert MessageType.DOCUMENT in MEDIA_TYPES
    assert MessageType.STICKER in MEDIA_TYPES
    assert MessageType.GIF in MEDIA_TYPES


def test_media_types_excludes_deleted_messages() -> None:
    assert MessageType.REVOKED not in MEDIA_TYPES
    assert MessageType.ADMIN_REVOKED not in MEDIA_TYPES


def test_view_once_media_counts_as_media_or_audio() -> None:
    assert {MessageType.VIEW_ONCE_IMAGE, MessageType.VIEW_ONCE_VIDEO} <= MEDIA_TYPES
    assert MessageType.VIEW_ONCE_AUDIO in AUDIO_TYPES


def test_audio_types_contains_voice_notes() -> None:
    assert {MessageType.AUDIO, MessageType.VIEW_ONCE_AUDIO} == AUDIO_TYPES


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
        (None, MessageType.REVOKED, "[Deleted]"),
        (None, MessageType.ADMIN_REVOKED, "[Deleted by admin]"),
        (None, MessageType.CALL, "[Call]"),
        (None, MessageType.ALBUM, "[Album]"),
        ("Lunch?", MessageType.POLL, "[Poll] Lunch?"),
        ("Party", MessageType.EVENT, "[Event] Party"),
        ("Your order shipped", MessageType.TEMPLATE_TEXT, "Your order shipped"),
        ("Dave", MessageType.CONTACT, "[Contact] Dave"),
        (None, MessageType.CONTACT, "[Contact]"),
        ("2 contacts", MessageType.MULTI_CONTACT, "[Contacts] 2 contacts"),
        ("", MessageType.MULTI_CONTACT, "[Contacts]"),
    ],
)
def test_message_display_text(text_data: str | None, message_type: MessageType, expected: str | None) -> None:
    assert message_display_text(text_data=text_data, message_type=message_type) == expected
