"""LangGraph orchestration of the talent-search pipeline.

The graph wires the AI stages into an explicit, observable state machine:

    understand → generate_queries → collect → rank → END

Data collection and ranking/persistence are injected as async callables so the
graph stays free of I/O concerns (HTTP, DB) and is trivially testable.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.ai.query_generation import generate_queries
from app.ai.understanding import parse_requirement
from app.core.logging import get_logger
from app.schemas import GeneratedQuery, ParsedRequirement

logger = get_logger("ai.graph")

# collector(queries, requirement, max_results) -> list of raw profile dicts
Collector = Callable[
    [list[GeneratedQuery], ParsedRequirement, int], Awaitable[list[dict[str, Any]]]
]
# ranker(requirement, profiles) -> list of ranked result dicts
Ranker = Callable[
    [ParsedRequirement, list[dict[str, Any]]], Awaitable[list[dict[str, Any]]]
]
# stage callback for progress reporting (e.g. persisting search status)
StageCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class PipelineState(TypedDict, total=False):
    query: str
    max_results: int
    requirement: ParsedRequirement
    queries: list[GeneratedQuery]
    profiles: list[dict[str, Any]]
    results: list[dict[str, Any]]
    error: str | None


async def _noop_stage(_: str, __: dict[str, Any]) -> None:  # pragma: no cover
    return None


def build_search_graph(
    collector: Collector,
    ranker: Ranker,
    on_stage: StageCallback | None = None,
):
    """Compile the search pipeline graph with injected I/O stages."""
    notify = on_stage or _noop_stage

    async def understand_node(state: PipelineState) -> PipelineState:
        await notify("understanding", {})
        requirement = await parse_requirement(state["query"])
        logger.info("stage_complete", stage="understand")
        return {"requirement": requirement}

    async def generate_node(state: PipelineState) -> PipelineState:
        await notify("searching", {"requirement": state["requirement"].model_dump()})
        queries = await generate_queries(state["requirement"])
        logger.info("stage_complete", stage="generate_queries", count=len(queries))
        return {"queries": queries}

    async def collect_node(state: PipelineState) -> PipelineState:
        await notify("collecting", {"queries": [q.query for q in state["queries"]]})
        profiles = await collector(
            state["queries"], state["requirement"], state.get("max_results", 30)
        )
        logger.info("stage_complete", stage="collect", profiles=len(profiles))
        return {"profiles": profiles}

    async def rank_node(state: PipelineState) -> PipelineState:
        await notify("ranking", {"profiles": len(state.get("profiles", []))})
        results = await ranker(state["requirement"], state.get("profiles", []))
        logger.info("stage_complete", stage="rank", results=len(results))
        return {"results": results}

    graph = StateGraph(PipelineState)
    graph.add_node("understand", understand_node)
    graph.add_node("generate_queries", generate_node)
    graph.add_node("collect", collect_node)
    graph.add_node("rank", rank_node)

    graph.set_entry_point("understand")
    graph.add_edge("understand", "generate_queries")
    graph.add_edge("generate_queries", "collect")
    graph.add_edge("collect", "rank")
    graph.add_edge("rank", END)

    return graph.compile()
