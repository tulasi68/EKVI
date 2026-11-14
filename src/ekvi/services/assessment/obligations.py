"""Obligation discovery and step-to-obligation mapping drafts.

Implements the spirit of claims C3, C6, C7, C8, C10, C11.
All outputs are *drafts* with proposed status; human verification required.
Absolute classification is produced; policy is applied later (C22).
"""

from __future__ import annotations

import re
from typing import Any, Optional

from ekvi.schemas.common import CoverageResult, ObligationDraft, SpanReference


LENS_KEYWORDS = {
    "negative": ["reject", "invalid", "malformed", "error", "fail", "deny", "unauthorized"],
    "boundary": ["limit", "maximum", "minimum", "exceed", "threshold", "boundary", "range"],
    "state": ["persist", "transition", "state", "session", "resume"],
    "positive": ["shall", "must", "support", "provide", "display", "accept"],
}


def _simple_span(text: str, quote: str) -> SpanReference:
    return SpanReference(quote=quote[:500] if quote else None, confidence=0.7)


def discover_obligations(
    requirement_external_id: str,
    normative_text: str,
    source_span: Optional[dict[str, Any]] = None,
) -> list[ObligationDraft]:
    """Split compound requirements and emit discrete obligations.

    Baseline implementation. Production path uses the LLM adapter
    with structured output schema and evidence validation (ARCH §9).
    """
    text = normative_text.strip()
    obligations: list[ObligationDraft] = []

    parts = re.split(r"\s+and\s+|;\s*", text, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        parts = [text]

    for idx, part in enumerate(parts, start=1):
        lens = "positive"
        for candidate, kws in LENS_KEYWORDS.items():
            if any(kw in part.lower() for kw in kws):
                lens = candidate
                break

        applicability = "applicable"
        applicability_rationale = None
        if lens == "boundary" and not re.search(r"\d+", part):
            applicability = "not_applicable"
            applicability_rationale = (
                "Authoritative numeric limit not stated in the requirement; "
                "do not invent a limit (C10)."
            )

        obligations.append(
            ObligationDraft(
                obligation_id=f"{requirement_external_id}-OBL-{idx:02d}",
                requirement_external_id=requirement_external_id,
                behaviour=part,
                lens=lens,
                applicability=applicability,
                applicability_rationale=applicability_rationale,
                source_span=_simple_span(text, part),
                confidence=0.65,
            )
        )
    return obligations


def map_steps_to_obligation(
    obligation: ObligationDraft,
    steps: list[dict[str, Any]],
) -> CoverageResult:
    """Map test steps to an obligation and classify coverage.

    Distinguishes intentional coverage from semantic false friends (C11).
    Aggregate coverage is performed by the caller across all linked cases (C8).
    """
    if obligation.applicability == "not_applicable":
        return CoverageResult(
            requirement_external_id=obligation.requirement_external_id,
            obligation_id=obligation.obligation_id,
            status="not_assessable",
            rationale=obligation.applicability_rationale or "Lens not applicable",
            confidence=0.9,
        )

    matched: list[SpanReference] = []
    behaviour_lower = obligation.behaviour.lower()
    key_terms = [t for t in re.findall(r"[a-zA-Z0-9_]{4,}", behaviour_lower) if t not in {"shall", "must", "system"}]

    for step in steps:
        action = (step.get("action") or "").lower()
        expected = (step.get("expected_result") or "").lower()
        combined = f"{action} {expected}"

        overlap = sum(1 for t in key_terms if t in combined)
        if overlap >= max(1, len(key_terms) // 2):
            matched.append(
                SpanReference(
                    quote=f"Step {step.get('sequence')}: {step.get('action')}",
                    confidence=0.55,
                )
            )

    if not matched:
        return CoverageResult(
            requirement_external_id=obligation.requirement_external_id,
            obligation_id=obligation.obligation_id,
            status="not_covered",
            rationale="No test step provides intentional evidence for this behaviour.",
            confidence=0.7,
        )

    vague = any(
        "correctly" in (s.get("expected_result") or "").lower()
        or "as expected" in (s.get("expected_result") or "").lower()
        for s in steps
    )
    if vague:
        return CoverageResult(
            requirement_external_id=obligation.requirement_external_id,
            obligation_id=obligation.obligation_id,
            status="partially_covered",
            rationale="Steps exist but expected result is not objectively pass/fail assessable.",
            mapped_step_spans=matched,
            confidence=0.6,
        )

    return CoverageResult(
        requirement_external_id=obligation.requirement_external_id,
        obligation_id=obligation.obligation_id,
        status="covered",
        rationale="One or more steps provide intentional evidence for the obligation.",
        mapped_step_spans=matched,
        confidence=0.6,
    )


def aggregate_coverage(results: list[CoverageResult]) -> str:
    """Aggregate across all linked cases (C8)."""
    if not results:
        return "not_covered"
    statuses = {r.status for r in results}
    if "covered" in statuses:
        return "covered"
    if "partially_covered" in statuses:
        return "partially_covered"
    if "not_assessable" in statuses and len(statuses) == 1:
        return "not_assessable"
    if "ambiguous" in statuses or "disputed" in statuses:
        return "ambiguous"
    return "not_covered"
