"""Document upload and parsing endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ekvi.config import get_settings
from ekvi.core.db import get_db
from ekvi.models.artefacts import ContentBlock, DocumentRevision, Project, SourceDocument, JobStatus
from ekvi.services.ingestion.parsers import checksum_bytes, parse_file

router = APIRouter()
settings = get_settings()


@router.post("/upload")
async def upload_document(
    project_id: uuid.UUID = Form(...),
    revision_label: str = Form("v1"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    data = await file.read()
    if len(data) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    mime = file.content_type or "application/octet-stream"
    if mime not in settings.allowed_mime_list and not any(
        file.filename and file.filename.lower().endswith(ext)
        for ext in (".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md")
    ):
        raise HTTPException(status_code=415, detail=f"Unsupported MIME type: {mime}")

    checksum = checksum_bytes(data)
    object_key = f"{project_id}/{checksum}_{file.filename}"

    store_path = Path(settings.storage_local_path) / object_key
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_bytes(data)

    doc = SourceDocument(
        project_id=project_id,
        object_key=object_key,
        filename=file.filename or "unknown",
        mime_type=mime,
        checksum=checksum,
        upload_metadata={"size": len(data)},
    )
    db.add(doc)
    await db.flush()

    revision = DocumentRevision(
        document_id=doc.id,
        revision_label=revision_label,
        processing_status=JobStatus.PROCESSING,
    )
    db.add(revision)
    await db.flush()

    try:
        parse_result = parse_file(file.filename or "", data, mime)
    except ValueError as exc:
        revision.processing_status = JobStatus.FAILED
        revision.extraction_quality = {"error": str(exc)}
        await db.flush()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for block in parse_result.blocks:
        db.add(
            ContentBlock(
                revision_id=revision.id,
                block_type=block.block_type,
                text=block.text,
                page=block.page,
                section=block.section,
                paragraph_index=block.paragraph_index,
                table_ref=block.table_ref,
                char_start=block.char_start,
                char_end=block.char_end,
                extraction_confidence=block.extraction_confidence,
                extra=block.extra,
            )
        )

    revision.processing_status = JobStatus.SUCCEEDED
    revision.extraction_quality = {
        **parse_result.quality,
        "warnings": parse_result.warnings,
        "block_count": len(parse_result.blocks),
    }
    await db.flush()

    return {
        "document_id": str(doc.id),
        "revision_id": str(revision.id),
        "checksum": checksum,
        "blocks": len(parse_result.blocks),
        "warnings": parse_result.warnings,
        "quality": revision.extraction_quality,
    }


@router.get("/{revision_id}/blocks")
async def list_blocks(
    revision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(ContentBlock).where(ContentBlock.revision_id == revision_id).order_by(ContentBlock.paragraph_index)
    )
    blocks = result.scalars().all()
    return {
        "revision_id": str(revision_id),
        "count": len(blocks),
        "blocks": [
            {
                "id": str(b.id),
                "type": b.block_type,
                "text": b.text[:500],
                "page": b.page,
                "section": b.section,
                "paragraph_index": b.paragraph_index,
                "confidence": b.extraction_confidence,
            }
            for b in blocks
        ],
    }
