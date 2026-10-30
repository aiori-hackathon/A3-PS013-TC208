from pathlib import Path
from app.services.evidence_service import collect_evidence_file
from app.services.ingestion_service import run_ingestion
from app.services.investigation_service import create_investigation, create_finding
from app.services.integrity_service import verify_evidence_file
from app.services.mutation_service import get_mutation_impact
from app.models.entities import TimelineEvent

def test_mutation_radar_flags_dependent_findings(db_session):
    content = b"Oct 27 11:00:00 host01 sshd[100]: Failed password for root from 192.0.2.99 port 44000 ssh2\n"
    ev = collect_evidence_file(db_session, "controlled.log", content)
    ing_run = run_ingestion(db_session, ev.evidence_id, parser_name="linux_auth")

    # Get created timeline event
    evt = db_session.query(TimelineEvent).filter(TimelineEvent.evidence_id == ev.evidence_id).first()
    assert evt is not None

    # Create investigation with finding that cites this event
    inv = create_investigation(db_session, "Mutation Test Inv")
    fnd = create_finding(
        db_session,
        inv.investigation_id,
        title="Unauthorized root attempt",
        supporting_events=[evt.event_id]
    )
    assert fnd.requires_review is False

    # Simulate post-collection file modification on disk
    file_path = Path(ev.stored_path)
    with open(file_path, "ab") as f:
        f.write(b"Oct 27 11:00:05 host01 sshd[101]: Tampered injected line\n")

    # Re-run verification -> should detect MISMATCH and trigger Mutation Radar
    ver = verify_evidence_file(db_session, ev.evidence_id)
    assert ver.result == "MISMATCH"

    # Verify that the dependent finding was automatically marked as requiring review
    db_session.refresh(fnd)
    assert fnd.requires_review is True
    assert "Mutation Radar alert" in fnd.review_reason

    # Verify impact map
    impact = get_mutation_impact(db_session, ev.evidence_id)
    assert impact["has_mismatch"] is True
    assert impact["affected_findings"][0].finding_id == fnd.finding_id
