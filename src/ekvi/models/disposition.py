"""Disposition log for measurement (STRAT §9) and feedback loop (§11).

Records timestamps that separate time-to-trust from time-to-decide.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ekvi.core.db import Base


class DispositionLog(Base):
    __tablename__ = "disposition_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    requirement_external_id: Mapped[Optional[str]] = mapped_column(String(128))
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    disposition: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(String(64))
    rationale: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    first_evidence_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    disposition_reached_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    note_written_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    time_to_trust_seconds: Mapped[Optional[float]] = mapped_column(Float)
    time_to_decide_seconds: Mapped[Optional[float]] = mapped_column(Float)
    total_seconds: Mapped[Optional[float]] = mapped_column(Float)

    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
