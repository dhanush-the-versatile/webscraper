"""Value objects passed through the collection pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models import SourceType


@dataclass(slots=True)
class SearchHit:
    """A single result returned by a search provider."""

    url: str
    title: str = ""
    snippet: str = ""
    source: SourceType = SourceType.SEARCH_ENGINE
    provider: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CollectedProfile:
    """A normalized public profile produced by the pipeline.

    ``data`` holds the extracted profile fields (the extraction contract from
    ``app.ai.extraction``); ``source_*`` carry provenance for CandidateSource.
    """

    data: dict[str, Any]
    source_url: str
    source_type: SourceType
    source_title: str = ""
    source_snippet: str = ""
    content_excerpt: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str | None:
        return self.data.get("full_name")

    @property
    def confidence(self) -> float:
        return float(self.data.get("extraction_confidence") or 0.0)
