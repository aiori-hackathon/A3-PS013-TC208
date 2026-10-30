import pytest
from app.services.blindlens_service import (
    create_blindlens_review, reveal_blindlens_context,
    record_blindlens_revision, verify_blindlens_review,
    canonical_json_digest
)
from app.models.entities import Investigation

def test_canonical_json_digest_stability():
    p1 = {"b": 2, "a": 1, "c": [3, 2, 1]}
    p2 = {"a": 1, "c": [3, 2, 1], "b": 2}
    # Deterministic output regardless of dict key insertion order
    assert canonical_json_digest(p1) == canonical_json_digest(p2)

def test_blindlens_staged_workflow_and_verification(db_session):
    inv = Investigation(
        investigation_id="INV-TEST",
        title="Test Investigation",
        status="OPEN"
    )
    db_session.add(inv)
    db_session.commit()

    # Stage 1: Initial assessment
    review = create_blindlens_review(
        db=db_session,
        investigation_id="INV-TEST",
        initial_hypothesis="Possible brute force attack from 192.0.2.10",
        initial_confidence=75,
        initial_evidence_refs=["EVT-01"],
        context_items=[{"content": "Authorized penetration testing note"}]
    )

    assert review.stage == "INITIAL"
    assert len(review.initial_digest) == 64
    assert review.revised_hypothesis is None

    # Initial verification should be valid
    v1 = verify_blindlens_review(db_session, review.review_id)
    assert v1["is_valid"] is True
    assert v1["initial_digest_match"] is True

    # Stage 2: Reveal context
    revealed = reveal_blindlens_context(db_session, review.review_id)
    assert revealed.stage == "REVEALED"
    assert revealed.context_revealed_at is not None

    # Stage 2: Record revision
    revised = record_blindlens_revision(
        db=db_session,
        review_id=review.review_id,
        revised_hypothesis="Activity is confirmed authorized penetration testing.",
        revised_confidence=95,
        reason_for_change="Operational context confirmed pre-scheduled testing window.",
        final_review_status="CONFIRMED"
    )

    assert revised.final_digest is not None
    assert len(revised.final_digest) == 64

    # Full verification
    v2 = verify_blindlens_review(db_session, review.review_id)
    assert v2["is_valid"] is True
    assert v2["initial_digest_match"] is True
    assert v2["final_digest_match"] is True

def test_blindlens_detects_payload_tampering(db_session):
    inv = Investigation(investigation_id="INV-TAMPER", title="Tamper Test", status="OPEN")
    db_session.add(inv)
    db_session.commit()

    review = create_blindlens_review(
        db=db_session,
        investigation_id="INV-TAMPER",
        initial_hypothesis="Original hypothesis",
        initial_confidence=50,
        initial_evidence_refs=[]
    )

    # Directly tamper with initial_hypothesis in the database
    review.initial_hypothesis = "Secretly altered hypothesis"
    db_session.commit()

    # Verification must catch the mismatch against stored canonical digest
    res = verify_blindlens_review(db_session, review.review_id)
    assert res["initial_digest_match"] is False
    assert res["is_valid"] is False
