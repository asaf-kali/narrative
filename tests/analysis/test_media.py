import pandas as pd

from narrative.analysis.media import media_breakdown, media_over_time
from narrative.models.config import AnalysisConfig
from narrative.models.message import MessageType

_CONFIG = AnalysisConfig()


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "message_type": [
                MessageType.IMAGE.value,
                MessageType.IMAGE.value,
                MessageType.AUDIO.value,
                MessageType.TEXT.value,
                MessageType.STICKER.value,
            ],
            "month": ["2024-01", "2024-01", "2024-01", "2024-01", "2024-02"],
        }
    )


def test_media_breakdown_counts_by_type_excludes_text() -> None:
    result = media_breakdown(_df(), _CONFIG).set_index("type_label")
    assert result.loc["Image", "count"] == 2
    assert result.loc["Voice Note", "count"] == 1
    assert "Text" not in result.index


def test_media_breakdown_sorted_descending() -> None:
    result = media_breakdown(_df(), _CONFIG)
    assert result["count"].tolist() == sorted(result["count"].tolist(), reverse=True)


def test_media_breakdown_empty_df() -> None:
    result = media_breakdown(pd.DataFrame(), _CONFIG)
    assert result.empty
    assert list(result.columns) == ["type_label", "count"]


def test_media_breakdown_no_media_messages_returns_empty() -> None:
    df = pd.DataFrame({"message_type": [MessageType.TEXT.value], "month": ["2024-01"]})
    result = media_breakdown(df, _CONFIG)
    assert result.empty


def test_media_over_time_groups_by_month_and_type() -> None:
    result = media_over_time(_df(), _CONFIG)
    jan_image = result[(result["month"] == "2024-01") & (result["type_label"] == "Image")]
    assert jan_image["count"].iloc[0] == 2


def test_media_over_time_empty_df() -> None:
    result = media_over_time(pd.DataFrame(), _CONFIG)
    assert result.empty
    assert list(result.columns) == ["month", "type_label", "count"]
