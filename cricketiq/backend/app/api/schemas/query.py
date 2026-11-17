"""Request schemas for CricketIQ Query API."""

from __future__ import annotations
from typing import Optional, Literal, Union
from datetime import date
from pydantic import BaseModel, Field

from cricketiq.backend.app.database.models import (
    CricketFormat,
    GenderCategory,
    DocumentAuthority,
)


class MatchContextInput(BaseModel):
    """User-supplied match or tournament context for rule applicability."""
    cricket_level: Optional[str] = Field(
        default=None,
        description="'international', 'domestic', or 'unspecified'"
    )
    governing_body: Optional[str] = Field(
        default=None,
        description="ICC, MCC, BCCI, ECB, CA, etc."
    )
    competition: Optional[str] = Field(
        default=None,
        description="Competition identifier, e.g. 'T20_WORLD_CUP_2026', 'WTC', 'IPL'"
    )
    format: Optional[CricketFormat] = Field(
        default=None,
        description="Match format: 'Test', 'ODI', 'T20I', or 'General'"
    )
    category: Optional[GenderCategory] = Field(
        default=None,
        description="Gender category: 'Men\\'s', 'Women\\'s', or 'Universal'"
    )
    match_date: Optional[Union[str, date]] = Field(
        default=None,
        description="Date of the match in YYYY-MM-DD format"
    )
    series_start_date: Optional[Union[str, date]] = Field(
        default=None,
        description="Start date of the series/tournament in YYYY-MM-DD format"
    )
    season: Optional[str] = Field(
        default=None,
        description="Season string, e.g. '2025-2027'"
    )
    applicable_rules: Optional[DocumentAuthority] = Field(
        default=None,
        description="Preferred authority: 'ICC' or 'MCC'"
    )


class ResponsePreferences(BaseModel):
    """User-configurable answer generation preferences."""
    detail_level: Literal["concise", "standard", "detailed"] = Field(
        default="standard",
        description="Level of explanation detail"
    )
    include_historical_comparison: bool = Field(
        default=False,
        description="Whether to include historical rule comparison"
    )
    include_cross_references: bool = Field(
        default=True,
        description="Whether to include related cross-referenced clauses"
    )
    max_citations: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of authoritative citations to return (1-10)"
    )


class QueryRequest(BaseModel):
    """Inbound query payload for POST /v1/rules/query."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language question about cricket rules"
    )
    context: Optional[MatchContextInput] = Field(
        default=None,
        description="Explicit match/tournament context if known"
    )
    preferences: Optional[ResponsePreferences] = Field(
        default_factory=ResponsePreferences,
        description="Answer formatting and citation preferences"
    )
