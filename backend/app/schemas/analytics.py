"""Analytics dashboard schemas."""

from __future__ import annotations

from pydantic import BaseModel


class CountPoint(BaseModel):
    label: str
    value: int


class TimeSeriesPoint(BaseModel):
    date: str
    value: int


class AnalyticsOverview(BaseModel):
    total_searches: int
    total_candidates: int
    total_saved: int
    completed_searches: int
    avg_results_per_search: float
    searches_over_time: list[TimeSeriesPoint]
    top_skills: list[CountPoint]
    top_countries: list[CountPoint]
    top_technologies: list[CountPoint]
    candidates_by_source: list[CountPoint]
    score_distribution: list[CountPoint]
