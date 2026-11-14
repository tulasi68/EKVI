"""Unit tests for baseline obligation discovery and coverage (C3, C7, C8, C10)."""

from ekvi.services.assessment.obligations import (
    aggregate_coverage,
    discover_obligations,
    map_steps_to_obligation,
)


def test_compound_split():
    obls = discover_obligations("REQ-080", "The system shall support DICOM and HL7.")
    assert len(obls) >= 2
    behaviours = " ".join(o.behaviour.lower() for o in obls)
    assert "dicom" in behaviours
    assert "hl7" in behaviours


def test_no_invented_limit():
    obls = discover_obligations(
        "REQ-055",
        "The system shall respond within an acceptable time for large studies.",
    )
    assert any(o.applicability == "not_applicable" for o in obls)
    for o in obls:
        if o.applicability == "not_applicable":
            r = map_steps_to_obligation(o, [])
            assert r.status == "not_assessable"


def test_aggregate_covered_wins():
    from ekvi.schemas.common import CoverageResult

    results = [
        CoverageResult(
            requirement_external_id="R",
            obligation_id="O1",
            status="partially_covered",
            rationale="partial",
        ),
        CoverageResult(
            requirement_external_id="R",
            obligation_id="O1",
            status="covered",
            rationale="full",
        ),
    ]
    assert aggregate_coverage(results) == "covered"
