import pandas as pd

from narrative.analysis.content import build_word_cloud_text, emoji_counts, word_frequencies
from narrative.models.config import AnalysisConfig

_CONFIG = AnalysisConfig()


def _df(texts: list[str | None]) -> pd.DataFrame:
    return pd.DataFrame({"text_data": texts})


def test_word_frequencies_counts_and_excludes_stopwords() -> None:
    result = word_frequencies(_df(["the cat and the dog", "cat cat dog"]), _CONFIG)
    counts = dict(zip(result["word"], result["count"], strict=True))
    assert counts["cat"] == 3
    assert counts["dog"] == 2
    assert "the" not in counts
    assert "and" not in counts


def test_word_frequencies_strips_urls() -> None:
    result = word_frequencies(_df(["check https://example.com/path later"]), _CONFIG)
    words = set(result["word"])
    assert "check" in words
    assert "later" in words
    assert not any("example" in w or "http" in w for w in words)


def test_word_frequencies_excludes_whatsapp_system_phrases() -> None:
    result = word_frequencies(_df(["<Media omitted>", "This message was deleted"]), _CONFIG)
    assert result.empty


def test_word_frequencies_excludes_single_char_words() -> None:
    result = word_frequencies(_df(["a b pizza"]), _CONFIG)
    assert "a" not in set(result["word"])
    assert "b" not in set(result["word"])
    assert "pizza" in set(result["word"])


def test_word_frequencies_empty_text_column_returns_empty_df() -> None:
    result = word_frequencies(_df([None, None]), _CONFIG)
    assert result.empty
    assert list(result.columns) == ["word", "count"]


def test_emoji_counts_extracts_and_tallies() -> None:
    result = emoji_counts(_df(["I love pizza \U0001f600", "so good \U0001f600\U0001f600"]), _CONFIG)
    counts = dict(zip(result["emoji"], result["count"], strict=True))
    assert counts["\U0001f600"] == 3


def test_emoji_counts_empty_when_no_emoji() -> None:
    result = emoji_counts(_df(["plain text here"]), _CONFIG)
    assert result.empty


def test_build_word_cloud_text_joins_cleaned_words() -> None:
    text = build_word_cloud_text(_df(["Pizza world!", "the a"]))
    assert "pizza" in text
    assert "world" in text
    assert "the" not in text.split()


def test_build_word_cloud_text_empty_when_no_valid_text() -> None:
    assert build_word_cloud_text(_df([None])) == ""
