#!/usr/bin/env python3
"""Lightweight claims evaluation harness (Stage 1 smoke).

Exercises the baseline obligation + coverage logic against the planted cases
defined in STRAT §21.2. This is a starting point; full Stage 2 requires the
locked corpus with ground-truth annotations.
"""

from __future__ import annotations

from ekvi.services.assessment.obligations import (
    aggregate_coverage,
    discover_obligations,
    map_steps_to_obligation,
)
from ekvi.schemas.common import CoverageResult


def case_a() -> None:
    """Correct trace link, inadequate steps → Partially Covered."""
    print("\n=== Case A (REQ-042) — partial coverage ===")
    req = (
        "The system shall reject uploads exceeding 50 MB with an error message "
        "identifying the size limit."
    )
    obls = discover_obligations("REQ-042", req)
    print(f"Obligations discovered: {len(obls)}")
    for o in obls:
        print(f"  {o.obligation_id} [{o.lens}] {o.behaviour[:60]}...")

    steps = [
        {"sequence": 1, "action": "Upload a 60 MB file", "expected_result": "Upload fails"},
    ]
    results: list[CoverageResult] = []
    for o in obls:
        r = map_steps_to_obligation(o, steps)
        results.append(r)
        print(f"  {o.obligation_id} → {r.status}: {r.rationale[:80]}")

    agg = aggregate_coverage(results)
    print(f"Aggregate: {agg}  (expected: partially_covered)")


def case_b() -> None:
    """Boundary lens, no numeric limit → Not Assessable (C10)."""
    print("\n=== Case B (REQ-055) — not assessable (no invented limit) ===")
    req = "The system shall respond within an acceptable time for large studies."
    obls = discover_obligations("REQ-055", req)
    for o in obls:
        print(f"  {o.obligation_id} applicability={o.applicability}")
        print(f"    rationale: {o.applicability_rationale}")
        r = map_steps_to_obligation(o, [])
        print(f"  coverage → {r.status}")


def case_g() -> None:
    """Compound requirement half covered."""
    print("\n=== Case G (REQ-080) — compound split ===")
    req = "The system shall support DICOM and HL7."
    obls = discover_obligations("REQ-080", req)
    print(f"Obligations: {len(obls)} (expected ≥ 2)")
    for o in obls:
        print(f"  {o.obligation_id}: {o.behaviour}")


def main() -> None:
    print("EKVI Claims Eval — Stage 1 smoke (baseline rules)")
    case_a()
    case_b()
    case_g()
    print("\nDone. Replace baseline with LLM adapter + locked corpus for Stage 2.")


if __name__ == "__main__":
    main()
