"""Lazy, resource-conscious Sentence Transformers embeddings."""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence

import numpy as np


BASELINE_MODEL = "all-MiniLM-L6-v2"


class EmbeddingInitializationError(RuntimeError):
    pass


class SentenceTransformerEmbeddings:
    def __init__(self, model_name: str = BASELINE_MODEL) -> None:
        self.model_name = model_name

    @property
    def model(self):
        return _load_model(self.model_name)

    def validate(self) -> None:
        """Ensure the configured local embedding model can initialize."""

        _ = self.model

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype="float32")
        try:
            vectors = self.model.encode(
                list(texts),
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as exc:  # pragma: no cover - library/hardware dependent
            raise EmbeddingInitializationError(str(exc)) from exc
        return np.asarray(vectors, dtype="float32")


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name, device="cpu")
    except Exception as exc:  # pragma: no cover - network/cache dependent
        raise EmbeddingInitializationError(
            f"Unable to initialize embedding model {model_name}: {exc}"
        ) from exc

