#!/usr/bin/env python3
"""Seed the MedView PACS synthetic benchmark (STRAT §21).

Creates a minimal set of planted cases that exercise C1–C14.
Run: python scripts/seed_medview_pacs.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

from ekvi.config import get_settings
from ekvi.core.db import AsyncSessionLocal, Base, engine
from ekvi.models.artefacts import (
    ArtefactType,
    EngineeringArtefact,
    Project,
    Tenant,
)

# Ensure disposition model is registered on metadata
import ekvi.models.disposition  # noqa: F401


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
    settings = get_settings()
    print(f"DATABASE_URL = {settings.database_url}")

    if settings.is_sqlite:
        raw = settings.database_url.replace("sqlite+aiosqlite:///", "")
        db_file = Path(raw)
        if not db_file.is_absolute():
            db_file = Path.cwd() / db_file
        db_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"SQLite file  = {db_file.resolve()}")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        print("\nERROR connecting to the database.", file=sys.stderr)
        print(f"  {type(exc).__name__}: {exc}", file=sys.stderr)
        if "aiosqlite" in str(exc).lower() or "no module" in str(exc).lower():
            print("\nFix: pip install aiosqlite", file=sys.stderr)
        if "postgresql" in settings.database_url or "asyncpg" in settings.database_url:
            print(
                "\nYour .env still points at Postgres. For no-Docker use, set in .env:\n"
                "  DATABASE_URL=sqlite+aiosqlite:///./data/ekvi.db",
                file=sys.stderr,
            )
        raise SystemExit(1) from exc

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
