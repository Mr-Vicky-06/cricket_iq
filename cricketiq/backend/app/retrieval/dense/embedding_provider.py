"""Embedding Provider Implementations and Text Construction for CricketIQ.

Supports:
- LocalDeterministicEmbeddingProvider: High-performance, offline, zero-network vectorizer.
- SentenceTransformerEmbeddingProvider: Neural dense embedding provider (e.g. all-MiniLM-L6-v2).
- Versioned embedding text construction template.
"""

from __future__ import annotations
import hashlib
import math
import re
from typing import List, Optional
import numpy as np

from cricketiq.backend.app.database.models import RuleClause, SourceDocument
from cricketiq.backend.app.retrieval.dense.base import EmbeddingProvider

EMBEDDING_TEMPLATE_VERSION = "v1"


def build_clause_embedding_text(clause: RuleClause, doc: Optional[SourceDocument] = None) -> str:
    """Build deterministic versioned text representation for clause embedding.

    Preserves original_text intact and incorporates regulatory authority/edition context.
    """
    context_prefix = ""
    if doc:
        pub = doc.publisher.value if hasattr(doc.publisher, "value") else str(doc.publisher)
        fmt = f" {doc.format.value if hasattr(doc.format, 'value') else str(doc.format)}" if doc.format else ""
        ed = f" {doc.edition}" if doc.edition else ""
        context_prefix = f"[{pub}{fmt}{ed}] "

    heading_part = f" - {clause.heading}" if clause.heading else ""
    return f"{context_prefix}Clause {clause.clause_number}{heading_part}: {clause.original_text.strip()}"


def compute_text_hash(text: str) -> str:
    """Compute SHA-256 hash of embedding input text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class LocalDeterministicEmbeddingProvider:
    """Zero-network, deterministic semantic vectorizer for offline and test environments.

    Projects subword character 3-grams and token hashes into a unit hypersphere (L2-normalized).
    Guarantees deterministic, reproducible cosine similarities without downloading multi-GB models.
    """

    def __init__(self, dimension: int = 384, model_name: str = "local-deterministic-v1"):
        self._dim = dimension
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_semantic(self) -> bool:
        """Local deterministic hash model is non-semantic (diagnostic/test only)."""
        return False

    def _text_to_vector(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self._dim

        words = re.findall(r"\b\w+\b", text.lower())
        vec = np.zeros(self._dim, dtype=np.float32)

        for w in words:
            # Word-level hash
            h_word = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % self._dim
            vec[h_word] += 1.0

            # Character 3-grams for morphological and phrasing similarity
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    tri = w[i:i + 3]
                    h_tri = int(hashlib.md5(tri.encode("utf-8")).hexdigest(), 16) % self._dim
                    vec[h_tri] += 0.35

        norm = float(np.linalg.norm(vec))
        if norm > 0.0 and math.isfinite(norm):
            vec = vec / norm
        else:
            vec = np.zeros(self._dim, dtype=np.float32)

        return vec.tolist()

    def embed_text(self, text: str) -> List[float]:
        return self._text_to_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._text_to_vector(t) for t in texts]


class SentenceTransformerEmbeddingProvider:
    """Neural sentence transformer provider with revision pinning."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", revision: Optional[str] = None):
        from sentence_transformers import SentenceTransformer
        self._model_name = model_name
        self._revision = revision
        kwargs = {}
        if revision:
            kwargs["revision"] = revision
        self._model = SentenceTransformer(model_name, **kwargs)
        self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_semantic(self) -> bool:
        """Sentence transformer model is a genuine semantic neural embedding model."""
        return True

    def embed_text(self, text: str) -> List[float]:
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]
