# EKVI — Engineering Knowledge & Verification Intelligence

**Prototype baseline** aligned with:
- `EKVI-STRAT-001 v1.2` (engagement-first, detection claims C1–C23)
- `EKVI-ARCH-001 v1.0` (modular, document-first, evidence-backed)

> **Status**: Pre-gate concierge tooling scaffold.  
> Implements only the capabilities permitted in Architecture Annex A.  
> Workbench UI, multi-tenancy, connectors, generation, and script impact are deferred.

## What this prototype provides

| Capability | Status | Notes |
|---|---|---|
| Document ingestion (PDF, DOCX, XLSX, CSV, TXT) | Skeleton | Content blocks with page/section/paragraph spans + confidence |
| Content / evidence store | Implemented | SQLAlchemy models + span references |
| Obligation discovery & step mapping drafts | Skeleton | Baseline rules; LLM adapter later |
| Coverage classification | Skeleton | Absolute assessment only (C22-protected) |
| Disposition log with timing | Implemented | Supports split-half measurement |
| Claims evaluation harness | Skeleton | Stage 0–2 ready structure |
| MedView PACS benchmark placeholder | Present | For calibration of C1–C14 |

## Design invariants (non-negotiable)

1. **One absolute truth, many policy verdicts** — obligation status + evidence spans are never changed by configuration.
2. **Propose → sandbox → re-assess → human approve** — no automatic write to controlled records.
3. **Every finding carries a verified span** — no unsupported assertions.
4. **Semantic similarity never becomes a formal trace link**.

## Quick start (no Docker)

Requires only **Python 3.11+** and Git. Uses SQLite by default.

```bash
git clone https://github.com/tulasi68/EKVI.git
cd EKVI
cp .env.example .env

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
pip install -e .

python scripts/seed_medview_pacs.py
uvicorn ekvi.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** in your browser (Swagger UI).

Optional claims smoke test (no server needed):

```bash
python scripts/run_claims_eval.py
```

### Optional: Postgres via Docker

If you prefer Postgres later:

```bash
docker compose up -d
# In .env set:
# DATABASE_URL=postgresql+asyncpg://ekvi:ekvi@localhost:5432/ekvi
```

## Project layout

```
src/ekvi/
├── main.py                 # FastAPI application
├── config.py
├── models/                 # SQLAlchemy (system of record)
├── schemas/                # Pydantic (typed contracts)
├── services/
│   ├── ingestion/          # parsers, content blocks
│   └── assessment/         # obligations, coverage
├── api/                    # route modules
└── core/                   # db, settings
scripts/
├── seed_medview_pacs.py
└── run_claims_eval.py
benchmark/medview_pacs/
```

## Next steps (post-prototype)

- Harden Stage 0 extraction gate (ID recall ≥ 99%, span accuracy ≥ 95%).
- Lock Stage 1 smoke corpus and measure classification precision.
- Instrument first real engagement (disposition log + split-half).
- Only after gate: policy layer, sandbox remediation, delta analysis, workbench UI.

## License & governance

Customer content is never used for model training without explicit written permission.  
All outputs are review aids; the manufacturer incorporates and approves them.
