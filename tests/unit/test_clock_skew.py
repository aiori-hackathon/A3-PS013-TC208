from datetime import datetime, timezone, timedelta
from app.services.clock_skew_service import estimate_clock_skew
from app.models.entities import TimelineEvent

def test_clock_skew_insufficient_matches(db_session):
    # When fewer than 2 matched events exist, should return INSUFFICIENT_MATCHES
    est = estimate_clock_skew(db_session, "EV-A", "EV-B", matching_criteria="source_ip_and_username")
    assert est.confidence == "INSUFFICIENT_MATCHES"
    assert est.estimated_offset_seconds is None
    assert "Fewer than 2" in est.assumptions

def test_clock_skew_known_offset(db_session):
    base = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    skew = timedelta(seconds=180.0)

    # Insert candidate events for EV-A and EV-B
    for i in range(3):
        ea = TimelineEvent(
            event_id=f"EA_{i}",
            evidence_id="EV-1",
            ingestion_id="ING-1",
            source_record_id=1,
            source_line=i+1,
            normalized_utc=base + timedelta(seconds=i*10),
            source_ip="192.0.2.60",
            username=f"user_{i}",
            summary="test a",
            parsing_status="PARSED",
            uncertainty_margin_seconds=1.0
        )
        eb = TimelineEvent(
            event_id=f"EB_{i}",
            evidence_id="EV-2",
            ingestion_id="ING-2",
            source_record_id=2,
            source_line=i+1,
            normalized_utc=base + timedelta(seconds=i*10) + skew,
            source_ip="192.0.2.60",
            username=f"user_{i}",
            summary="test b",
            parsing_status="PARSED",
            uncertainty_margin_seconds=1.0
        )
        db_session.add(ea)
        db_session.add(eb)
    db_session.commit()

    est = estimate_clock_skew(db_session, "EV-1", "EV-2", matching_criteria="source_ip_and_username")
    assert est.confidence in ("HIGH", "MEDIUM")
    assert est.matched_pairs_count == 3
    assert est.estimated_offset_seconds == 180.0
