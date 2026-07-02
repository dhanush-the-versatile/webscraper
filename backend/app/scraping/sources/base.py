"""Source abstractions.

Two extension points keep the pipeline modular:

* ``SearchProvider`` — turns a generated query into ``SearchHit``s
  (search-engine APIs, or any site with a searchable public API).
* ``ProfileEnricher`` — turns a ``SearchHit`` into a ``CollectedProfile``
  (official APIs preferred; generic page extraction otherwise).

New public sources are added by implementing one of these and registering it —
no pipeline changes required.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import GeneratedQuery, ParsedRequirement
from app.scraping.models import CollectedProfile, SearchHit


class SearchProvider(ABC):
    """Produces candidate URLs for a query."""

    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """Whether this provider is usable in the current configuration."""

    @abstractmethod
    async def search(self, query: GeneratedQuery, *, limit: int = 10) -> list[SearchHit]:
        ...


class ProfileEnricher(ABC):
    """Turns a search hit into a collected profile."""

    name: str = "base"

    @abstractmethod
    def matches(self, hit: SearchHit) -> bool:
        """Whether this enricher should handle the given hit."""

    @abstractmethod
    async def enrich(
        self, hit: SearchHit, requirement: ParsedRequirement
    ) -> CollectedProfile | None:
        ...


class EnricherRegistry:
    """Ordered registry — first matching enricher wins."""

    def __init__(self) -> None:
        self._enrichers: list[ProfileEnricher] = []

    def register(self, enricher: ProfileEnricher) -> None:
        self._enrichers.append(enricher)

    def resolve(self, hit: SearchHit) -> ProfileEnricher | None:
        return next((e for e in self._enrichers if e.matches(hit)), None)

    @property
    def all(self) -> list[ProfileEnricher]:
        return list(self._enrichers)
