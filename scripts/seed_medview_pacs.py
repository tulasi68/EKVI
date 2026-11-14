#!/usr/bin/env python3
"""Seed the MedView PACS synthetic benchmark (STRAT §21).

Creates a minimal set of planted cases that exercise C1–C14.
Run after migrations: python scripts/seed_medview_pacs.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from ekvi.core.db import AsyncSessionLocal, Base, engine
from ekvi.models.artefacts import (
    ArtefactType,
    EngineeringArtefact,
    Project,
    Tenant,
)


CASES = [
    {
        "id": "REQ-042",
        "title": "Upload size limit rejection",
        "text": (
            "The system shall reject uploads exceeding 50 MB with an error message "
            "identifying the size limit."
        ),
        "notes": "Case A — correct link, inadequate steps (partial)",
    },
    {
        "id": "REQ-055",
        "title": "Response time for large studies",
        "text": "The system shall respond within an acceptable time for large studies.",
        "notes": "Case B — boundary lens, limit not stated (not assessable)",
    },
    {
        "id": "REQ-060",
        "title": "DICOM tag validation",
        "text": (
            "The system shall validate DICOM tags, reject malformed tags, "
            "and log the rejection."
        ),
        "notes": "Case C — coverage spread across cases",
    },
    {
        "id": "REQ-070",
        "title": "Positive flow only",
        "text": "The system shall accept valid patient registration data.",
        "notes": "Case E — negative path absent",
    },
    {
        "id": "REQ-080",
        "title": "Compound protocol support",
        "text": "The system shall support DICOM and HL7.",
        "notes": "Case G — compound half covered",
    },
]


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name="MedView Benchmark Tenant")
            db.add(tenant)
            await db.flush()

        result = await db.execute(select(Project).where(Project.name == "MedView PACS"))
        project = result.scalar_one_or_none()
        if not project:
            project = Project(
                tenant_id=tenant.id,
                name="MedView PACS",
                product="MedView PACS",
                version_context="synthetic-v1",
                configuration={"benchmark": True},
            )
            db.add(project)
            await db.flush()

        for case in CASES:
            result = await db.execute(
                select(EngineeringArtefact).where(
                    EngineeringArtefact.project_id == project.id,
                    EngineeringArtefact.external_id == case["id"],
                )
            )
            if result.scalar_one_or_none():
                continue
            art = EngineeringArtefact(
                project_id=project.id,
                artefact_type=ArtefactType.REQUIREMENT,
                external_id=case["id"],
                title=case["title"],
                status="approved",
            )
            db.add(art)

        await db.commit()
        print(f"Seeded MedView PACS project {project.id}")
        print(f"  Requirements: {len(CASES)}")
        for c in CASES:
            print(f"    {c['id']}: {c['notes']}")


if __name__ == "__main__":
    asyncio.run(main())
