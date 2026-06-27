from __future__ import annotations

import contextlib
import io
import logging
from typing import TYPE_CHECKING

from semantic_search.vector_store import SearchHit

if TYPE_CHECKING:
    from FlagEmbedding import FlagReranker

logger = logging.getLogger(__name__)

_MODEL_NAME = "BAAI/bge-reranker-v2-m3"


class RerankerUnavailableError(RuntimeError):
    pass


class Reranker:
    """Cross-encoder second stage that reorders a candidate pool.

    Reads (query, passage) jointly — far more precise than bi-encoder cosine.
    Multilingual (Hebrew-capable).
    """

    def __init__(self) -> None:
        self._model: FlagReranker | None = None

    def rerank(self, query: str, candidates: list[SearchHit], top_n: int) -> list[SearchHit]:
        if not candidates:
            return []
        model = self._load()
        pairs = [[query, c.text] for c in candidates]
        with contextlib.redirect_stderr(io.StringIO()):
            raw = model.compute_score(pairs, normalize=True)
        scores = self._as_scores(raw=raw, expected=len(candidates))
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        return [hit.model_copy(update={"score": score}) for hit, score in ranked[:top_n]]

    def _load(self) -> FlagReranker:
        if self._model is None:
            try:
                from FlagEmbedding import FlagReranker  # noqa: PLC0415
            except ImportError as e:
                msg = "FlagEmbedding is not installed — run: uv sync --group semantic"
                raise RerankerUnavailableError(msg) from e

            logger.info(f"Loading reranker model {_MODEL_NAME}")
            self._model = FlagReranker(_MODEL_NAME, use_fp16=True)
            logger.info("Reranker model loaded")
        return self._model

    @staticmethod
    def _as_scores(raw: object, expected: int) -> list[float]:
        if isinstance(raw, (int, float)):
            return [float(raw)]
        if isinstance(raw, list):
            return [float(s) for s in raw]
        msg = f"Unexpected reranker score type {type(raw)!r} (expected {expected} scores)"
        raise RerankerUnavailableError(msg)
