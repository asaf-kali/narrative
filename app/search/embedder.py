from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from FlagEmbedding import BGEM3FlagModel

logger = logging.getLogger(__name__)

_MODEL_NAME = "BAAI/bge-m3"


class EmbedderUnavailableError(RuntimeError):
    pass


class Embedder:
    def __init__(self) -> None:
        self._model: BGEM3FlagModel | None = None

    def _load(self) -> BGEM3FlagModel:
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel  # noqa: PLC0415
            except ImportError as e:
                msg = "FlagEmbedding is not installed — run: uv sync --group search"
                raise EmbedderUnavailableError(msg) from e

            logger.info(f"Loading embedding model {_MODEL_NAME}")
            self._model = BGEM3FlagModel(_MODEL_NAME, use_fp16=True)
            logger.info("Embedding model loaded")
        return self._model

    def embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        model = self._load()
        output = model.encode(
            texts,
            batch_size=batch_size,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        return [vec.tolist() for vec in output["dense_vecs"]]
