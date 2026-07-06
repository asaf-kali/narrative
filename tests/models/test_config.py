from datetime import UTC, datetime

from models.config import AnalysisConfig


def test_cache_key_includes_all_filter_fields() -> None:
    config = AnalysisConfig(
        chat_id=5,
        date_from=datetime(2024, 1, 1, tzinfo=UTC),
        date_to=datetime(2024, 2, 1, tzinfo=UTC),
        exclude_system=False,
    )
    assert config.cache_key() == "5|2024-01-01 00:00:00+00:00|2024-02-01 00:00:00+00:00|False"


def test_cache_key_defaults() -> None:
    config = AnalysisConfig()
    assert config.cache_key() == "None|None|None|True"


def test_cache_key_differs_between_distinct_configs() -> None:
    a = AnalysisConfig(chat_id=1)
    b = AnalysisConfig(chat_id=2)
    assert a.cache_key() != b.cache_key()


def test_default_min_messages_for_participant() -> None:
    assert AnalysisConfig().min_messages_for_participant == 5
