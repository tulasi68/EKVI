"""Assessment endpoints — obligation discovery and coverage drafts."""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ekvi.schemas.common import CoverageResult, ObligationDraft
from ekvi.services.assessment.obligations import (
    aggregate_coverage,
    discover_obligations,
    map_steps_to_obligation,
)

router = APIRouter()


class ObligationRequest(BaseModel):
    requirement_external_id: str
    normative_text: str
    source_span: Optional[dict[str, Any]] = None


class StepInput(BaseModel):
    sequence: int
    action: str
    expected_result: Optional[str] = None


class CoverageRequest(BaseModel):
    obligation: ObligationDraft
    steps: List[StepInput] = Field(default_factory=list)


class AggregateRequest(BaseModel):
    results: List[CoverageResult]


@router.post("/obligations", response_model=List[ObligationDraft])
async def extract_obligations(body: ObligationRequest) -> list[ObligationDraft]:
    """Discover discrete verification obligations from requirement text (C3)."""
    return discover_obligations(
        requirement_external_id=body.requirement_external_id,
        normative_text=body.normative_text,
        source_span=body.source_span,
    )


@router.post("/coverage", response_model=CoverageResult)
async def assess_coverage(body: CoverageRequest) -> CoverageResult:
    """Map steps to an obligation and classify absolute coverage (C6, C7, C11)."""
    steps = [s.model_dump() for s in body.steps]
    return map_steps_to_obligation(body.obligation, steps)


@router.post("/coverage/aggregate")
async def aggregate(body: AggregateRequest) -> dict[str, str]:
    """Aggregate coverage across linked test cases (C8)."""
    status = aggregate_coverage(body.results)
    return {"aggregate_status": status}
