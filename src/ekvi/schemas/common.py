from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SpanReference(BaseModel):
    """Evidence span that every finding must carry."""

    block_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    revision_id: Optional[UUID] = None
    page: Optional[int] = None
    section: Optional[str] = None
    paragraph_index: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    quote: Optional[str] = None
    confidence: Optional[float] = None


class ObligationDraft(BaseModel):
    """Discrete verification obligation extracted from a requirement.

    Obligations are *not* new requirements; they retain the source span.
    """

    obligation_id: str
    requirement_external_id: str
    behaviour: str
    lens: Optional[str] = None
    applicability: str = "applicable"
    applicability_rationale: Optional[str] = None
    source_span: SpanReference
    confidence: Optional[float] = None


class CoverageResult(BaseModel):
    """Absolute coverage classification — never altered by policy config (C22)."""

    requirement_external_id: str
    obligation_id: str
    status: str
    rationale: str
    mapped_step_spans: list[SpanReference] = Field(default_factory=list)
    confidence: Optional[float] = None


class FindingCreate(BaseModel):
    category: str
    coverage_status: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[float] = None
    explanation: str
    evidence_references: list[SpanReference] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    affected_entity_ids: list[str] = Field(default_factory=list)


class FindingOut(FindingCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_run_id: UUID
    created_at: datetime


class DispositionCreate(BaseModel):
    finding_id: Optional[UUID] = None
    requirement_external_id: Optional[str] = None
    disposition: str
    reason_code: Optional[str] = None
    rationale: Optional[str] = None
    started_at: Optional[datetime] = None
    first_evidence_verified_at: Optional[datetime] = None
    disposition_reached_at: Optional[datetime] = None
    note_written_at: Optional[datetime] = None


class ProjectCreate(BaseModel):
    name: str
    product: Optional[str] = None
    version_context: Optional[str] = None
    configuration: dict[str, Any] = Field(default_factory=dict)


class ProjectOut(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
