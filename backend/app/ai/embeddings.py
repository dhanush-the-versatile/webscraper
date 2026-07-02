"""Embedding service for semantic / vector search.

Uses OpenAI embeddings when configured. Otherwise falls back to a
deterministic feature-hashing embedding (a classic hashing-vectorizer):
stable across processes, unit-normalized, and good enough to make vector
search functional in development without any API key.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai.embeddings")

_TOKEN_RE = re.compile(r"[a-z0-9+#.]{2,}")


def _hashing_embedding(text: str, dim: int) -> list[float]:
    """Deterministic bag-of-tokens embedding via feature hashing."""
    vector = [0.0] * dim
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingService:
    def __init__(self) -> None:
        self._dim = settings.EMBEDDING_DIM
        self._openai = None
        if settings.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI

                self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as exc:  # pragma: no cover
                logger.warning("embedding_client_init_failed", error=str(exc))

    async def embed(self, text: str) -> list[float]:
        text = (text or "").strip()[:8000]
        if not text:
            return [0.0] * self._dim
        if self._openai is not None:
            try:
                response = await self._openai.embeddings.create(
                    model=settings.EMBEDDING_MODEL, input=text
                )
                return list(response.data[0].embedding)
            except Exception as exc:
                logger.warning("embedding_api_failed", error=str(exc))
        return _hashing_embedding(text, self._dim)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]

    @staticmethod
    def candidate_document(candidate) -> str:
        """Canonical text representation of a candidate for embedding."""
        parts = [
            candidate.full_name or "",
            candidate.headline or "",
            candidate.company or "",
            candidate.industry or "",
            " ".join(candidate.technologies or []),
            candidate.bio or "",
            f"{candidate.city or ''} {candidate.country or ''}",
        ]
        return " \n".join(p for p in parts if p)

    @staticmethod
    def requirement_document(req) -> str:
        """Canonical text representation of a requirement for embedding."""
        return " \n".join(
            [
                " ".join(req.job_titles),
                " ".join(req.all_skills()),
                " ".join(req.industries),
                " ".join(req.countries + req.cities),
                " ".join(req.keywords),
            ]
        )


embedding_service = EmbeddingService()
