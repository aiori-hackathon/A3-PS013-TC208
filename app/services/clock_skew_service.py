import uuid
import statistics
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.entities import TimelineEvent, ClockSkewEstimate, AuditEvent

def estimate_clock_skew(
    db: Session,
    evidence_a_id: str,
    evidence_b_id: str,
    matching_criteria: str = "source_ip_and_username",
    actor: str = "Analyst"
) -> ClockSkewEstimate:
    """
    Computes an explainable clock-skew estimate between two evidence sources
    based on explicit matching criteria (e.g. same client IP and username or request target).
    Never correlates purely based on timestamp proximity.
    """
    events_a = db.query(TimelineEvent).filter(
        TimelineEvent.evidence_id == evidence_a_id,
        TimelineEvent.normalized_utc.isnot(None)
    ).all()

    events_b = db.query(TimelineEvent).filter(
        TimelineEvent.evidence_id == evidence_b_id,
        TimelineEvent.normalized_utc.isnot(None)
    ).all()

    matched_differences: List[float] = []
    match_pairs: List[Dict[str, Any]] = []

    # Correlate based on explicit matching criteria
    if matching_criteria == "source_ip_and_username":
        # Group by (source_ip, username)
        a_map: Dict[tuple, List[TimelineEvent]] = {}
        for ea in events_a:
            if ea.source_ip and ea.username:
                key = (ea.source_ip, ea.username)
                a_map.setdefault(key, []).append(ea)

        for eb in events_b:
            if eb.source_ip and eb.username:
                key = (eb.source_ip, eb.username)
                if key in a_map:
                    # Match candidate
                    ea = a_map[key][0]  # First candidate match
                    diff_seconds = (eb.normalized_utc - ea.normalized_utc).total_seconds()
                    # Filter out implausible differences (> 24 hours) to avoid accidental collisions
                    if abs(diff_seconds) < 86400:
                        matched_differences.append(diff_seconds)
                        match_pairs.append({
                            "event_a_id": ea.event_id,
                            "event_b_id": eb.event_id,
                            "ip": eb.source_ip,
                            "user": eb.username,
                            "diff_sec": diff_seconds
                        })

    elif matching_criteria == "source_ip":
        a_ip_map: Dict[str, List[TimelineEvent]] = {}
        for ea in events_a:
            if ea.source_ip:
                a_ip_map.setdefault(ea.source_ip, []).append(ea)

        for eb in events_b:
            if eb.source_ip and eb.source_ip in a_ip_map:
                ea = a_ip_map[eb.source_ip][0]
                diff_seconds = (eb.normalized_utc - ea.normalized_utc).total_seconds()
                if abs(diff_seconds) < 86400:
                    matched_differences.append(diff_seconds)
                    match_pairs.append({
                        "event_a_id": ea.event_id,
                        "event_b_id": eb.event_id,
                        "ip": eb.source_ip,
                        "diff_sec": diff_seconds
                    })

    # Minimum matching threshold: requires at least 2 distinct correlated pairs to establish a non-coincidental offset
    MIN_PAIRS = 2
    if len(matched_differences) < MIN_PAIRS:
        confidence = "INSUFFICIENT_MATCHES"
        est_offset = None
        uncertainty = None
        assumptions = (
            f"Fewer than {MIN_PAIRS} correlating events found between {evidence_a_id} and {evidence_b_id} "
            f"under criteria '{matching_criteria}'. Cannot reliably establish clock drift or offset."
        )
    else:
        est_offset = float(statistics.median(matched_differences))
        uncertainty = float(statistics.pstdev(matched_differences)) if len(matched_differences) > 1 else 0.5
        # Add baseline margin
        uncertainty = round(max(uncertainty, 0.5), 2)
        confidence = "HIGH" if len(matched_differences) >= 4 and uncertainty <= 2.0 else "MEDIUM"
        assumptions = (
            f"Estimated from {len(matched_differences)} candidate pairs matched on {matching_criteria}. "
            f"Assumes correlated events represent concurrent or near-concurrent activity."
        )

    estimate = ClockSkewEstimate(
        estimate_id=f"SKEW-{uuid.uuid4().hex[:8].upper()}",
        source_evidence_a_id=evidence_a_id,
        source_evidence_b_id=evidence_b_id,
        matching_criteria=matching_criteria,
        matched_pairs_count=len(matched_differences),
        estimated_offset_seconds=est_offset,
        uncertainty_seconds=uncertainty,
        confidence=confidence,
        assumptions=assumptions,
        calculated_at=datetime.now(timezone.utc)
    )
    db.add(estimate)

    audit = AuditEvent(
        audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        action="CLOCK_SKEW_ESTIMATION",
        entity_type="EVIDENCE_PAIR",
        entity_id=f"{evidence_a_id}:{evidence_b_id}",
        actor=actor,
        details_json=f'{{"confidence": "{confidence}", "offset_seconds": {est_offset}, "matches": {len(matched_differences)}}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(estimate)
    return estimate
