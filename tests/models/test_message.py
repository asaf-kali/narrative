from narrative.models.message import AUDIO_TYPES, MEDIA_TYPES, MessageType


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
