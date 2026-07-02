"""AI module: LLM-backed capabilities with deterministic fallbacks."""

from app.ai.embeddings import EmbeddingService, cosine_similarity, embedding_service
from app.ai.extraction import extract_profile
from app.ai.graph import build_search_graph
from app.ai.narrative import generate_narratives
from app.ai.provider import get_llm_provider, reset_provider_cache
from app.ai.query_generation import generate_queries, generate_queries_deterministic
from app.ai.understanding import parse_requirement

__all__ = [
    "parse_requirement",
    "generate_queries",
    "generate_queries_deterministic",
    "extract_profile",
    "generate_narratives",
    "build_search_graph",
    "EmbeddingService",
    "embedding_service",
    "cosine_similarity",
    "get_llm_provider",
    "reset_provider_cache",
]
