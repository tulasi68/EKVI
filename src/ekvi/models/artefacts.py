"""Core domain models aligned with EKVI-ARCH-001 §6 Conceptual Model.

Key invariants:
- All structured records are tenant- and project-scoped.
- Source documents and content blocks preserve spans and extraction confidence.
- Relationships carry provenance and approval state (proposed by default).
- Findings always reference evidence spans; absolute assessment is non-configurable.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ekvi.core.db import Base


class ArtefactType(str, enum.Enum):
    REQUIREMENT = "requirement"
    TEST_CASE = "test_case"
    DEFECT = "defect"
    COMPONENT = "component"
    DESIGN_DECISION = "design_decision"
    CODE_CHANGE = "code_change"
    RELEASE = "release"


class RelationshipType(str, enum.Enum):
    DERIVES_FROM = "DERIVES_FROM"
    DECOMPOSES_INTO = "DECOMPOSES_INTO"
    VERIFIED_BY = "VERIFIED_BY"
    PROPOSED_VERIFICATION_LINK = "PROPOSED_VERIFICATION_LINK"
    AFFECTED_BY = "AFFECTED_BY"
    FIXED_BY = "FIXED_BY"
    IMPLEMENTED_BY = "IMPLEMENTED_BY"
    INTRODUCED_IN = "INTRODUCED_IN"
    DUPLICATES = "DUPLICATES"
    RELATED_TO = "RELATED_TO"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    SUPERSEDES = "SUPERSEDES"
    SUPPORTED_BY = "SUPPORTED_BY"


class RelationshipStatus(str, enum.Enum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ProvenanceType(str, enum.Enum):
    EXPLICIT_IMPORT = "explicit_import"
    USER_CREATED = "user_created"
    AI_SUGGESTED = "ai_suggested"


class CoverageStatus(str, enum.Enum):
    COVERED = "covered"
    PARTIALLY_COVERED = "partially_covered"
    NOT_COVERED = "not_covered"
    NOT_ASSESSABLE = "not_assessable"
    AMBIGUOUS = "ambiguous"
    DISPUTED = "disputed"


class FindingCategory(str, enum.Enum):
    REQUIREMENT_QUALITY = "requirement_quality"
    OBLIGATION_GAP = "obligation_gap"
    PROCEDURE_QUALITY = "procedure_quality"
    COVERAGE = "coverage"
    REGRESSION_CANDIDATE = "regression_candidate"
    EVIDENCE = "evidence"
    OTHER = "other"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    product: Mapped[Optional[str]] = mapped_column(String(255))
    version_context: Mapped[Optional[str]] = mapped_column(String(128))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents: Mapped[list["SourceDocument"]] = relationship(back_populates="project")
    artefacts: Mapped[list["EngineeringArtefact"]] = relationship(back_populates="project")


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    source_revision: Mapped[Optional[str]] = mapped_column(String(128))
    upload_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="documents")
    revisions: Mapped[list["DocumentRevision"]] = relationship(back_populates="document")


class DocumentRevision(Base):
    __tablename__ = "document_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_documents.id"), nullable=False, index=True)
    revision_label: Mapped[str] = mapped_column(String(128), nullable=False)
    effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    supersedes_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    processing_status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.QUEUED, nullable=False
    )
    extraction_quality: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["SourceDocument"] = relationship(back_populates="revisions")
    blocks: Mapped[list["ContentBlock"]] = relationship(back_populates="revision")


class ContentBlock(Base):
    """Preserved extraction unit with location evidence (ARCH §6)."""

    __tablename__ = "content_blocks"
    __table_args__ = (
        Index("ix_content_blocks_revision_type", "revision_id", "block_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_revisions.id"), nullable=False)
    block_type: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[Optional[int]] = mapped_column(Integer)
    section: Mapped[Optional[str]] = mapped_column(String(512))
    paragraph_index: Mapped[Optional[int]] = mapped_column(Integer)
    table_ref: Mapped[Optional[str]] = mapped_column(String(128))
    char_start: Mapped[Optional[int]] = mapped_column(Integer)
    char_end: Mapped[Optional[int]] = mapped_column(Integer)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float)
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    revision: Mapped["DocumentRevision"] = relationship(back_populates="blocks")


class EngineeringArtefact(Base):
    __tablename__ = "engineering_artefacts"
    __table_args__ = (
        UniqueConstraint("project_id", "artefact_type", "external_id", name="uq_artefact_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    artefact_type: Mapped[ArtefactType] = mapped_column(Enum(ArtefactType), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(1024))
    status: Mapped[Optional[str]] = mapped_column(String(64))
    current_revision_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="artefacts")
    revisions: Mapped[list["ArtefactRevision"]] = relationship(back_populates="artefact")


class ArtefactRevision(Base):
    __tablename__ = "artefact_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artefact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("engineering_artefacts.id"), nullable=False, index=True)
    source_revision_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    normalised_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artefact: Mapped["EngineeringArtefact"] = relationship(back_populates="revisions")


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artefact_revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artefact_revisions.id"), nullable=False, unique=True
    )
    level: Mapped[Optional[str]] = mapped_column(String(64))
    parent_external_id: Mapped[Optional[str]] = mapped_column(String(128))
    normative_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[Optional[str]] = mapped_column(String(64))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    source_span: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artefact_revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artefact_revisions.id"), nullable=False, unique=True
    )
    objective: Mapped[Optional[str]] = mapped_column(Text)
    preconditions: Mapped[Optional[str]] = mapped_column(Text)
    test_data: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(String(64))
    source_span: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    steps: Mapped[list["TestStep"]] = relationship(back_populates="test_case")


class TestStep(Base):
    __tablename__ = "test_steps"
    __table_args__ = (
        Index("ix_test_steps_case_seq", "test_case_id", "sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    expected_result: Mapped[Optional[str]] = mapped_column(Text)
    source_span: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    test_case: Mapped["TestCase"] = relationship(back_populates="steps")


class Defect(Base):
    __tablename__ = "defects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artefact_revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artefact_revisions.id"), nullable=False, unique=True
    )
    symptoms: Mapped[Optional[str]] = mapped_column(Text)
    environment: Mapped[Optional[str]] = mapped_column(Text)
    component: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[Optional[str]] = mapped_column(String(64))
    root_cause: Mapped[Optional[str]] = mapped_column(Text)
    fix_summary: Mapped[Optional[str]] = mapped_column(Text)
    release_ref: Mapped[Optional[str]] = mapped_column(String(128))
    source_span: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Relationship(Base):
    """Typed, governed relationship with provenance and approval state."""

    __tablename__ = "relationships"
    __table_args__ = (
        Index("ix_relationships_source_target", "source_artefact_id", "target_artefact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_artefact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_revision_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    target_artefact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_revision_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    relationship_type: Mapped[RelationshipType] = mapped_column(Enum(RelationshipType), nullable=False)
    status: Mapped[RelationshipStatus] = mapped_column(
        Enum(RelationshipStatus), default=RelationshipStatus.PROPOSED, nullable=False
    )
    provenance_type: Mapped[ProvenanceType] = mapped_column(Enum(ProvenanceType), nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    source_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by: Mapped[Optional[str]] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_by: Mapped[Optional[str]] = mapped_column(String(128))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AssessmentRun(Base):
    __tablename__ = "assessment_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    analysis_type: Mapped[str] = mapped_column(String(64), nullable=False)
    input_revision_ids: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    model_provider: Mapped[Optional[str]] = mapped_column(String(64))
    model_version: Mapped[Optional[str]] = mapped_column(String(128))
    prompt_template_version: Mapped[Optional[str]] = mapped_column(String(64))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    findings: Mapped[list["Finding"]] = relationship(back_populates="assessment_run")


class Finding(Base):
    """Absolute assessment finding. Status is non-configurable (C22)."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_runs.id"), nullable=False, index=True
    )
    affected_entity_ids: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    category: Mapped[FindingCategory] = mapped_column(Enum(FindingCategory), nullable=False)
    coverage_status: Mapped[Optional[CoverageStatus]] = mapped_column(Enum(CoverageStatus))
    severity: Mapped[Optional[str]] = mapped_column(String(32))
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_references: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assessment_run: Mapped["AssessmentRun"] = relationship(back_populates="findings")
    review_decisions: Mapped[list["ReviewDecision"]] = relationship(back_populates="finding")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("findings.id"), nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    disposition: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    reason_code: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    finding: Mapped["Finding"] = relationship(back_populates="review_decisions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor: Mapped[Optional[str]] = mapped_column(String(128))
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(64))
    target_id: Mapped[Optional[str]] = mapped_column(String(128))
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
