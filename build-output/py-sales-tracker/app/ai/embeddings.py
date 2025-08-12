from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore

import numpy as np

from app.ai.config import EMBEDDING_MODEL_DIR, EMBEDDING_DIM


class Embeddings:
    def __init__(self) -> None:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers not installed. Install to enable embeddings.")
        self.model = SentenceTransformer(str(EMBEDDING_MODEL_DIR))

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        return np.asarray(self.model.encode(list(texts), normalize_embeddings=True)) 