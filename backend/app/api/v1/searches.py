"""Search endpoints: create/run searches, poll status, fetch ranked results."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.api.deps import DB, CurrentUser, Pagination
from app.schemas import Page, SearchCreate, SearchDetail, SearchRead
from app.services import SearchService
from app.tasks.dispatch import dispatch_search

router = APIRouter()


@router.post("", response_model=SearchRead, status_code=status.HTTP_202_ACCEPTED,
             summary="Create a search and start the AI pipeline")
async def create_search(
    payload: SearchCreate,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: DB,
) -> SearchRead:
    service = SearchService(db)
    search = await service.create_search(user.id, payload)
    await db.commit()  # persist before handing off to the worker
    dispatch_search(background_tasks, search.id, payload.max_results)
    return SearchRead.model_validate(search)


@router.get("", response_model=Page[SearchRead], summary="List my searches")
async def list_searches(user: CurrentUser, db: DB, params: Pagination) -> Page[SearchRead]:
    return await SearchService(db).list_searches(user.id, params)


@router.get("/{search_id}", response_model=SearchRead, summary="Search status (poll)")
async def get_search(search_id: str, user: CurrentUser, db: DB) -> SearchRead:
    search = await SearchService(db).get_search(user.id, search_id)
    return SearchRead.model_validate(search)


@router.get("/{search_id}/results", response_model=SearchDetail,
            summary="Ranked results for a search")
async def get_results(
    search_id: str,
    user: CurrentUser,
    db: DB,
    params: Pagination,
    min_score: float | None = Query(default=None, ge=0, le=100),
) -> SearchDetail:
    detail, _total = await SearchService(db).get_detail(
        user.id, search_id, params=params, min_score=min_score
    )
    return detail
