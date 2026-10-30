import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.entities import BlindLensReview, Investigation, AuditEvent

def canonical_json_digest(payload: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA-256 digest over canonical JSON representation
    (sorted keys, compact delimiters, UTF-8 encoded).
    """
    canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    h = hashlib.sha256()
    h.update(canonical_str.encode("utf-8"))
    return h.hexdigest().lower()

def create_blindlens_review(
    db: Session,
    investigation_id: str,
    initial_hypothesis: str,
    initial_confidence: int,
    initial_evidence_refs: List[str],
    initial_unresolved: Optional[str] = None,
    context_items: Optional[List[Dict[str, Any]]] = None,
    investigator_id: str = "Analyst"
) -> BlindLensReview:
    """
    Stage 1: Records an initial assessment prior to contextual reveal,
    generating an immutable canonical cryptographic digest.
    """
    inv = db.query(Investigation).filter(Investigation.investigation_id == investigation_id).first()
    if not inv:
        raise ValueError(f"Investigation '{investigation_id}' not found.")

    review_id = f"BLIND-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    recorded_at = datetime.now(timezone.utc)
    recorded_at_str = recorded_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Canonical payload for Stage 1 initial assessment
    initial_payload = {
        "review_id": review_id,
        "investigation_id": investigation_id,
        "investigator_id": investigator_id,
        "initial_hypothesis": initial_hypothesis.strip(),
        "initial_confidence": int(initial_confidence),
        "initial_evidence_refs": sorted(initial_evidence_refs),
        "initial_unresolved": (initial_unresolved or "").strip(),
        "initial_recorded_at": recorded_at_str
    }
    initial_digest = canonical_json_digest(initial_payload)

    review = BlindLensReview(
        review_id=review_id,
        investigation_id=investigation_id,
        investigator_id=investigator_id,
        stage="INITIAL",
        initial_hypothesis=initial_hypothesis.strip(),
        initial_confidence=int(initial_confidence),
        initial_evidence_refs_json=json.dumps(initial_evidence_refs),
        initial_unresolved=initial_unresolved,
        initial_recorded_at=recorded_at,
        initial_digest=initial_digest,
        context_items_json=json.dumps(context_items or []),
        final_review_status="IN_PROGRESS"
    )
    db.add(review)

    audit = AuditEvent(
        audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        timestamp=recorded_at,
        action="BLINDLENS_STAGE1_RECORDED",
        entity_type="BLINDLENS_REVIEW",
        entity_id=review_id,
        actor=investigator_id,
        details_json=json.dumps({
            "initial_confidence": initial_confidence,
            "initial_digest": initial_digest
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(review)
    return review

def reveal_blindlens_context(db: Session, review_id: str, actor: str = "Analyst") -> BlindLensReview:
    """
    Advances review to Stage 2: Context Reveal.
    Records the reveal timestamp while preserving initial assessment completely intact.
    """
    review = db.query(BlindLensReview).filter(BlindLensReview.review_id == review_id).first()
    if not review:
        raise ValueError(f"BlindLens review '{review_id}' not found.")

    if review.stage == "REVEALED":
        return review  # Context already revealed

    review.stage = "REVEALED"
    review.context_revealed_at = datetime.now(timezone.utc)

    audit = AuditEvent(
        audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        timestamp=review.context_revealed_at,
        action="BLINDLENS_CONTEXT_REVEALED",
        entity_type="BLINDLENS_REVIEW",
        entity_id=review_id,
        actor=actor,
        details_json=f'{{"revealed_at": "{review.context_revealed_at.isoformat()}"}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(review)
    return review

def record_blindlens_revision(
    db: Session,
    review_id: str,
    revised_hypothesis: str,
    revised_confidence: int,
    reason_for_change: str,
    final_review_status: str = "CONFIRMED",
    actor: str = "Analyst"
) -> BlindLensReview:
    """
    Stage 2 Re-assessment: Records revised findings and obligatory rationale for change.
    Generates a canonical final review digest.
    """
    review = db.query(BlindLensReview).filter(BlindLensReview.review_id == review_id).first()
    if not review:
        raise ValueError(f"BlindLens review '{review_id}' not found.")

    if review.stage != "REVEALED":
        raise ValueError("Cannot record revision before context has been explicitly revealed.")

    if not reason_for_change.strip():
        raise ValueError("A clear reason for change or confirmation is required when completing review.")

    review.revised_hypothesis = revised_hypothesis.strip()
    review.revised_confidence = int(revised_confidence)
    review.reason_for_change = reason_for_change.strip()
    review.final_review_status = final_review_status

    context_revealed_str = (
        review.context_revealed_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        if review.context_revealed_at else ""
    )
    final_payload = {
        "review_id": review.review_id,
        "initial_digest": review.initial_digest,
        "context_revealed_at": context_revealed_str,
        "revised_hypothesis": review.revised_hypothesis,
        "revised_confidence": review.revised_confidence,
        "reason_for_change": review.reason_for_change,
        "final_review_status": review.final_review_status
    }
    review.final_digest = canonical_json_digest(final_payload)

    audit = AuditEvent(
        audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        action="BLINDLENS_REVISION_RECORDED",
        entity_type="BLINDLENS_REVIEW",
        entity_id=review_id,
        actor=actor,
        details_json=json.dumps({
            "revised_confidence": revised_confidence,
            "status": final_review_status,
            "final_digest": review.final_digest
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(review)
    return review

def verify_blindlens_review(db: Session, review_id: str) -> Dict[str, Any]:
    """
    Verifies that the stored review records have not been altered outside
    the canonical workflow by re-calculating the Stage 1 and Stage 2 digests.
    """
    review = db.query(BlindLensReview).filter(BlindLensReview.review_id == review_id).first()
    if not review:
        raise ValueError(f"BlindLens review '{review_id}' not found.")

    initial_refs = json.loads(review.initial_evidence_refs_json or "[]")
    rec_time_str = (
        review.initial_recorded_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        if review.initial_recorded_at else ""
    )
    recalc_initial_payload = {
        "review_id": review.review_id,
        "investigation_id": review.investigation_id,
        "investigator_id": review.investigator_id,
        "initial_hypothesis": review.initial_hypothesis.strip(),
        "initial_confidence": int(review.initial_confidence),
        "initial_evidence_refs": sorted(initial_refs),
        "initial_unresolved": (review.initial_unresolved or "").strip(),
        "initial_recorded_at": rec_time_str
    }
    calc_initial_digest = canonical_json_digest(recalc_initial_payload)
    initial_match = (calc_initial_digest == review.initial_digest)

    final_match = None
    calc_final_digest = None
    if review.final_digest:
        rev_time_str = (
            review.context_revealed_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            if review.context_revealed_at else ""
        )
        recalc_final_payload = {
            "review_id": review.review_id,
            "initial_digest": review.initial_digest,
            "context_revealed_at": rev_time_str,
            "revised_hypothesis": review.revised_hypothesis or "",
            "revised_confidence": review.revised_confidence or 0,
            "reason_for_change": review.reason_for_change or "",
            "final_review_status": review.final_review_status or ""
        }
        calc_final_digest = canonical_json_digest(recalc_final_payload)
        final_match = (calc_final_digest == review.final_digest)

    is_valid = initial_match and (final_match is not False)
    review.is_tampered = not is_valid
    db.commit()

    return {
        "review_id": review_id,
        "initial_digest_match": initial_match,
        "final_digest_match": final_match,
        "is_valid": is_valid,
        "calculated_initial_digest": calc_initial_digest,
        "stored_initial_digest": review.initial_digest,
        "calculated_final_digest": calc_final_digest,
        "stored_final_digest": review.final_digest,
        "message": "Review integrity verified: baseline digests match canonical payload." if is_valid else "Integrity warning: stored review record payload does not match canonical digest!"
    }
