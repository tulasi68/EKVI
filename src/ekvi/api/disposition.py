"""Disposition logging for measurement and feedback (STRAT §9, §11)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ekvi.core.db import get_db
from ekvi.models.disposition import DispositionLog
from ekvi.schemas.common import DispositionCreate

router = APIRouter()


def _compute_timings(log: DispositionLog) -> None:
    if log.started_at and log.first_evidence_verified_at:
        log.time_to_trust_seconds = (
            log.first_evidence_verified_at - log.started_at
        ).total_seconds()
    if log.first_evidence_verified_at and log.disposition_reached_at:
        log.time_to_decide_seconds = (
            log.disposition_reached_at - log.first_evidence_verified_at
        ).total_seconds()
    if log.started_at and log.note_written_at:
        log.total_seconds = (log.note_written_at - log.started_at).total_seconds()
    elif log.started_at and log.disposition_reached_at:
        log.total_seconds = (log.disposition_reached_at - log.started_at).total_seconds()


@router.post("")
async def record_disposition(
    body: DispositionCreate,
    project_id: uuid.UUID,
    reviewer: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    log = DispositionLog(
        project_id=project_id,
        finding_id=body.finding_id,
        requirement_external_id=body.requirement_external_id,
        reviewer=reviewer,
        disposition=body.disposition,
        reason_code=body.reason_code,
        rationale=body.rationale,
        started_at=body.started_at,
        first_evidence_verified_at=body.first_evidence_verified_at,
        disposition_reached_at=body.disposition_reached_at or datetime.now(timezone.utc),
        note_written_at=body.note_written_at,
    )
    _compute_timings(log)
    db.add(log)
    await db.flush()
    return {
        "id": str(log.id),
        "disposition": log.disposition,
        "time_to_trust_seconds": log.time_to_trust_seconds,
        "time_to_decide_seconds": log.time_to_decide_seconds,
        "total_seconds": log.total_seconds,
    }
