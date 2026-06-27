from __future__ import annotations

import logging
from types import ModuleType
from typing import TYPE_CHECKING

from semantic_search.vector_store import SearchHit

if TYPE_CHECKING:
    from transformers import PreTrainedModel, PreTrainedTokenizerBase

logger = logging.getLogger(__name__)

_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
_MAX_LENGTH = 1024
_BATCH_SIZE = 16


class RerankerUnavailableError(RuntimeError):
    pass


class Reranker:
    """Cross-encoder second stage that reorders a candidate pool.

    Reads (query, passage) jointly — far more precise than bi-encoder cosine.
    bge-reranker-v2-m3 is a multilingual (Hebrew-capable) XLM-RoBERTa sequence
    classifier; the relevance score is sigmoid(logit). Run via transformers
    directly rather than FlagEmbedding's wrapper, which breaks on transformers 5.x.
    """

    def __init__(self) -> None:
        self._model: PreTrainedModel | None = None
        self._tokenizer: PreTrainedTokenizerBase | None = None
        self._torch: ModuleType | None = None
        self._device: str = "cpu"

    def rerank(self, query: str, candidates: list[SearchHit], top_n: int) -> list[SearchHit]:
        if not candidates:
            return []
        self._load()
        passages = [c.text for c in candidates]
        scores = self._score(query=query, passages=passages)
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        return [hit.model_copy(update={"score": score}) for hit, score in ranked[:top_n]]

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch  # noqa: PLC0415
            from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: PLC0415
        except ImportError as e:
            msg = "transformers/torch not installed — run: uv sync --group semantic"
            raise RerankerUnavailableError(msg) from e

        logger.info(f"Loading reranker model {_MODEL_NAME}")
        self._torch = torch
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, use_fast=True)
        model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
        if self._device == "cuda":
            model = model.half()
        self._model = model.to(self._device).eval()
        logger.info(f"Reranker model loaded on {self._device}")

    def _score(self, query: str, passages: list[str]) -> list[float]:
        torch = self._torch
        tokenizer = self._tokenizer
        model = self._model
        if torch is None or tokenizer is None or model is None:
            raise RerankerUnavailableError("Reranker model failed to load")

        scores: list[float] = []
        for start in range(0, len(passages), _BATCH_SIZE):
            batch = passages[start : start + _BATCH_SIZE]
            pairs = [[query, p] for p in batch]
            inputs = tokenizer(pairs, padding=True, truncation=True, max_length=_MAX_LENGTH, return_tensors="pt").to(
                self._device
            )
            with torch.no_grad():
                logits = model(**inputs).logits.view(-1).float()
                batch_scores = torch.sigmoid(logits).tolist()
            scores.extend(float(s) for s in batch_scores)
        return scores
