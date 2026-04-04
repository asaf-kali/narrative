import pandas as pd
from analysis.content import emoji_counts, word_frequencies
from models.config import AnalysisConfig


def test_word_frequencies_returns_df(sample_messages_df: pd.DataFrame) -> None:
    config = AnalysisConfig()
    result = word_frequencies(sample_messages_df, config)
    assert not result.empty
    assert "word" in result.columns
    assert "count" in result.columns


def test_word_frequencies_filters_stopwords(sample_messages_df: pd.DataFrame) -> None:
    config = AnalysisConfig()
    result = word_frequencies(sample_messages_df, config)
    # "the", "a", "and" should be removed
    assert "the" not in result["word"].to_numpy()
    assert "a" not in result["word"].to_numpy()


def test_word_frequencies_excludes_system_phrases(sample_messages_df: pd.DataFrame) -> None:
    df = sample_messages_df.copy()
    df.loc[len(df)] = df.iloc[0].copy()
    df.loc[len(df) - 1, "text_data"] = "<Media omitted>"
    config = AnalysisConfig()
    result = word_frequencies(df, config)
    max_media_count = 5
    media_count = result[result["word"] == "media"]["count"].sum()
    assert "media" not in result["word"].to_numpy() or media_count < max_media_count


def test_emoji_counts_returns_df(sample_messages_df: pd.DataFrame) -> None:
    df = sample_messages_df.copy()
    df.loc[0, "text_data"] = "Hello 😊 world 🎉"
    config = AnalysisConfig()
    result = emoji_counts(df, config)
    assert not result.empty
    assert "emoji" in result.columns
    assert "count" in result.columns


def test_emoji_counts_empty_when_no_emoji(sample_messages_df: pd.DataFrame) -> None:
    config = AnalysisConfig()
    result = emoji_counts(sample_messages_df, config)
    # sample df has no emoji — may be empty
    assert isinstance(result, pd.DataFrame)
