"""Candidate repository: dedup-aware upserts, filtering, and vector search."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Candidate,
    CandidateSkill,
    CandidateSource,
    Experience,
    Skill,
)
from app.repositories.base import BaseRepository


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower().strip()).strip("-")


def compute_dedup_hash(
    *,
    full_name: str,
    linkedin_url: str | None = None,
    github_url: str | None = None,
    public_email: str | None = None,
    company: str | None = None,
) -> str:
    """Stable identity hash for de-duplication.

    Prefers globally-unique public handles (LinkedIn/GitHub URL, public email);
    falls back to a name+company composite.
    """
    for anchor in (linkedin_url, github_url, public_email):
        if anchor:
            basis = anchor.lower().strip().rstrip("/")
            break
    else:
        basis = f"{full_name.lower().strip()}|{(company or '').lower().strip()}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


class CandidateRepository(BaseRepository[Candidate]):
    model = Candidate

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._skill_cache: dict[str, Skill] = {}

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    async def get_detail(self, id_: str) -> Candidate | None:
        stmt = (
            select(Candidate)
            .where(Candidate.id == id_)
            .options(
                selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
                selectinload(Candidate.experiences),
                selectinload(Candidate.sources),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_dedup_hash(self, dedup_hash: str) -> Candidate | None:
        return await self.get_by(dedup_hash=dedup_hash)

    def _apply_filters(self, stmt, filters: dict[str, Any]):
        """Translate a filter dict into SQL predicates."""
        if countries := filters.get("countries"):
            stmt = stmt.where(
                func.lower(Candidate.country).in_([c.lower() for c in countries])
            )
        if cities := filters.get("cities"):
            stmt = stmt.where(func.lower(Candidate.city).in_([c.lower() for c in cities]))
        if companies := filters.get("companies"):
            clauses = [Candidate.company.ilike(f"%{c}%") for c in companies]
            stmt = stmt.where(or_(*clauses))
        if industries := filters.get("industries"):
            clauses = [Candidate.industry.ilike(f"%{i}%") for i in industries]
            stmt = stmt.where(or_(*clauses))
        if min_years := filters.get("min_years_experience"):
            stmt = stmt.where(Candidate.years_experience >= int(min_years))
        if technologies := filters.get("technologies"):
            # technologies stored as a JSON array — portable containment check
            clauses = [
                cast(Candidate.technologies, String).ilike(f'%"{t.lower()}"%')
                for t in technologies
            ]
            stmt = stmt.where(or_(*clauses))
        if skills := filters.get("skills"):
            skill_subq = (
                select(CandidateSkill.candidate_id)
                .join(Skill, Skill.id == CandidateSkill.skill_id)
                .where(Skill.slug.in_([slugify(s) for s in skills]))
            )
            stmt = stmt.where(Candidate.id.in_(skill_subq))
        return stmt

    async def search(
        self,
        *,
        keyword: str | None = None,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Candidate], int]:
        """Keyword + structured filter search with total count."""
        stmt = select(Candidate)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    Candidate.full_name.ilike(like),
                    Candidate.headline.ilike(like),
                    Candidate.company.ilike(like),
                    Candidate.bio.ilike(like),
                    cast(Candidate.technologies, String).ilike(like),
                )
            )
        if filters:
            stmt = self._apply_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(count_stmt)).scalar_one())

        stmt = stmt.order_by(Candidate.updated_at.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        return items, total

    async def vector_search(
        self,
        embedding: list[float],
        *,
        limit: int = 50,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[Candidate, float]]:
        """Nearest-neighbour search returning ``(candidate, similarity ∈ [0,1])``.

        Uses pgvector cosine distance on PostgreSQL; on other dialects (the
        SQLite test suite) it falls back to computing cosine similarity in
        Python over the (bounded) candidate set, so semantic search behaves
        identically everywhere.
        """
        if self.db.bind.dialect.name == "postgresql":
            distance = Candidate.embedding.cosine_distance(embedding)  # type: ignore[attr-defined]
            stmt = select(Candidate, distance.label("distance")).where(
                Candidate.embedding.is_not(None)
            )
            if filters:
                stmt = self._apply_filters(stmt, filters)
            stmt = stmt.order_by(distance).limit(limit)
            rows = (await self.db.execute(stmt)).all()
            return [(row[0], max(0.0, 1.0 - float(row[1]))) for row in rows]

        # Portable fallback: score in Python.
        from app.ai.embeddings import cosine_similarity

        stmt = select(Candidate).where(Candidate.embedding.is_not(None))
        if filters:
            stmt = self._apply_filters(stmt, filters)
        candidates = list((await self.db.execute(stmt.limit(1000))).scalars().all())
        scored = [
            (candidate, max(0.0, cosine_similarity(embedding, candidate.embedding or [])))
            for candidate in candidates
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:limit]

    async def hybrid_search(
        self,
        *,
        keyword: str,
        embedding: list[float],
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 20,
        keyword_weight: float = 0.5,
    ) -> tuple[list[tuple[Candidate, float]], int]:
        """Blend keyword matching and semantic similarity into one ranking.

        Keyword hits get a rank-decayed score; semantic scores come from
        ``vector_search``. Final score = weighted sum, candidates appearing in
        either list are included.
        """
        keyword_hits, _ = await self.search(
            keyword=keyword, filters=filters, offset=0, limit=200
        )
        semantic_hits = await self.vector_search(embedding, limit=200, filters=filters)

        scores: dict[str, float] = {}
        by_id: dict[str, Candidate] = {}
        for rank, candidate in enumerate(keyword_hits):
            by_id[candidate.id] = candidate
            scores[candidate.id] = keyword_weight * (1.0 / (1.0 + rank * 0.15))
        for candidate, similarity in semantic_hits:
            by_id.setdefault(candidate.id, candidate)
            scores[candidate.id] = scores.get(candidate.id, 0.0) + (
                (1.0 - keyword_weight) * similarity
            )

        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        total = len(ordered)
        page = ordered[offset : offset + limit]
        return [(by_id[cid], round(score, 4)) for cid, score in page], total

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #
    async def upsert_by_hash(self, dedup_hash: str, **fields: Any) -> tuple[Candidate, bool]:
        """Create the candidate or merge new non-empty fields into the existing row.

        Returns ``(candidate, created)``.
        """
        existing = await self.get_by_dedup_hash(dedup_hash)
        if existing is None:
            candidate = await self.create(dedup_hash=dedup_hash, **fields)
            return candidate, True

        # Merge: only fill fields that are currently empty (first source wins),
        # except confidence which takes the max observed.
        for key, value in fields.items():
            if value in (None, "", [], {}):
                continue
            current = getattr(existing, key, None)
            if key == "extraction_confidence":
                setattr(existing, key, max(float(current or 0.0), float(value)))
            elif current in (None, "", [], {}):
                setattr(existing, key, value)
        await self.db.flush()
        return existing, False

    async def get_or_create_skill(self, name: str, category: str | None = None) -> Skill:
        slug = slugify(name)
        if not slug:
            raise ValueError(f"Cannot derive slug from skill name {name!r}")
        if slug in self._skill_cache:
            return self._skill_cache[slug]
        skill = (
            await self.db.execute(select(Skill).where(Skill.slug == slug))
        ).scalar_one_or_none()
        if skill is None:
            skill = Skill(name=name.strip(), slug=slug, category=category)
            self.db.add(skill)
            await self.db.flush()
        self._skill_cache[slug] = skill
        return skill

    async def set_skills(
        self, candidate: Candidate, skills: list[str], *, inferred_from: str | None = None
    ) -> None:
        """Attach skills (idempotent) to a candidate."""
        existing_stmt = select(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id)
        existing = {
            link.skill_id: link
            for link in (await self.db.execute(existing_stmt)).scalars().all()
        }
        for raw in skills:
            name = raw.strip()
            if not name or not slugify(name):
                continue
            skill = await self.get_or_create_skill(name)
            if skill.id not in existing:
                link = CandidateSkill(
                    candidate_id=candidate.id, skill_id=skill.id, inferred_from=inferred_from
                )
                self.db.add(link)
                existing[skill.id] = link
        await self.db.flush()

    async def add_source(
        self, candidate: Candidate, *, url: str, source_type, **fields: Any
    ) -> CandidateSource | None:
        """Attach a provenance record, ignoring duplicates by (candidate, url)."""
        dup = await self.db.execute(
            select(CandidateSource).where(
                CandidateSource.candidate_id == candidate.id, CandidateSource.url == url
            )
        )
        if dup.scalar_one_or_none() is not None:
            return None
        source = CandidateSource(
            candidate_id=candidate.id, url=url, source_type=source_type, **fields
        )
        self.db.add(source)
        await self.db.flush()
        return source

    async def replace_experiences(
        self, candidate: Candidate, experiences: list[dict[str, Any]]
    ) -> None:
        """Replace experience rows when a richer extraction arrives."""
        for old in list(candidate.experiences):
            await self.db.delete(old)
        for exp in experiences:
            self.db.add(Experience(candidate_id=candidate.id, **exp))
        await self.db.flush()
