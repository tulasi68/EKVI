"""Project management (minimal for prototype)."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ekvi.core.db import get_db
from ekvi.models.artefacts import Project, Tenant
from ekvi.schemas.common import ProjectCreate, ProjectOut

router = APIRouter()


async def _ensure_default_tenant(db: AsyncSession) -> uuid.UUID:
    result = await db.execute(select(Tenant).limit(1))
    tenant = result.scalar_one_or_none()
    if tenant:
        return tenant.id
    tenant = Tenant(name="Default Tenant")
    db.add(tenant)
    await db.flush()
    return tenant.id


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    tenant_id = await _ensure_default_tenant(db)
    project = Project(
        tenant_id=tenant_id,
        name=body.name,
        product=body.product,
        version_context=body.version_context,
        configuration=body.configuration,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("", response_model=List[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[Project]:
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
