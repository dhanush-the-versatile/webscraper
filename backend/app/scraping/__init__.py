"""Public data collection: compliant search + extraction pipeline."""

from app.scraping.models import CollectedProfile, SearchHit
from app.scraping.pipeline import (
    CollectionPipeline,
    build_default_registry,
    collection_pipeline,
)

__all__ = [
    "SearchHit",
    "CollectedProfile",
    "CollectionPipeline",
    "collection_pipeline",
    "build_default_registry",
]
