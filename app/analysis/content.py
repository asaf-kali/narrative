import logging
import re
from collections import Counter
from pathlib import Path

import emoji as emoji_lib
import pandas as pd
from analysis.base import analysis  # ty: ignore[unresolved-import]
from models.config import AnalysisConfig  # ty: ignore[unresolved-import]

logger = logging.getLogger(__name__)

_STOPWORDS_DIR = Path(__file__).parent.parent / "data" / "stopwords"
_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
_NON_ALPHA = re.compile(r"[^\w\s]", re.UNICODE)


def _load_stopwords() -> frozenset[str]:
    words: set[str] = set()
    for lang_file in _STOPWORDS_DIR.glob("*.txt"):
        try:
            words.update(lang_file.read_text(encoding="utf-8").splitlines())
        except OSError:
            logger.warning(f"Could not read stopwords file: {lang_file}")
    return frozenset(w.lower().strip() for w in words if w.strip())


_STOPWORDS: frozenset[str] = _load_stopwords()

_WHATSAPP_SYSTEM_PHRASES: frozenset[str] = frozenset(
    {
        "<media omitted>",
        "this message was deleted",
        "you deleted this message",
        "missed voice call",
        "missed video call",
    }
)


@analysis(name="word_frequencies", label="Word Frequencies", page="content")
def word_frequencies(df: pd.DataFrame, _config: AnalysisConfig) -> pd.DataFrame:
    texts = df["text_data"].dropna().astype(str)
    if texts.empty:
        return pd.DataFrame(columns=["word", "count"])

    words: Counter[str] = Counter()
    for raw in texts:
        if raw.lower() in _WHATSAPP_SYSTEM_PHRASES:
            continue
        cleaned = _NON_ALPHA.sub(" ", _URL_PATTERN.sub("", raw))
        for word in cleaned.lower().split():
            if len(word) > 1 and word not in _STOPWORDS:
                words[word] += 1

    top = words.most_common(50)
    return pd.DataFrame(top, columns=["word", "count"])


@analysis(name="emoji_counts", label="Emoji Usage", page="content")
def emoji_counts(df: pd.DataFrame, _config: AnalysisConfig) -> pd.DataFrame:
    texts = df["text_data"].dropna().astype(str)
    if texts.empty:
        return pd.DataFrame(columns=["emoji", "count"])

    counter: Counter[str] = Counter()
    for text in texts:
        for e in emoji_lib.analyze(text):
            counter[e.chars] += 1

    top = counter.most_common(30)
    return pd.DataFrame(top, columns=["emoji", "count"])


def build_word_cloud_text(df: pd.DataFrame) -> str:
    texts = df["text_data"].dropna().astype(str)
    words: list[str] = []
    for raw in texts:
        if raw.lower() in _WHATSAPP_SYSTEM_PHRASES:
            continue
        cleaned = _NON_ALPHA.sub(" ", _URL_PATTERN.sub("", raw))
        words.extend(w for w in cleaned.lower().split() if len(w) > 1 and w not in _STOPWORDS)
    return " ".join(words)
