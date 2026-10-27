import pytest
from app.services.evidence_service import collect_evidence_file
from app.services.ingestion_service import run_ingestion
from app.models.entities import ParsingLedger, TimelineEvent

def test_ingestion_ledger_accounting_invariant(db_session):
    # Log stream containing 3 valid syslog lines and 1 blank line
    log_content = (
        b"Oct 27 10:30:01 host01 sshd[1234]: Failed password for invalid user admin from 192.0.2.10 port 52100 ssh2\n"
        b"\n"
        b"Oct 27 10:30:08 host01 sshd[1234]: Accepted publickey for analyst from 192.0.2.20 port 52110 ssh2\n"
        b"This is an unparseable malformed line without syslog header\n"
    )

    ev = collect_evidence_file(db_session, "test_accounting.log", log_content)
    ing_run = run_ingestion(db_session, ev.evidence_id, parser_name="linux_auth", timezone_assumption="UTC")

    assert ing_run.status == "COMPLETED"
    assert ing_run.total_records == 4
    assert ing_run.parsed_count == 2
    assert ing_run.unparsed_count == 2  # Blank line + malformed line

    # Enforce Ledger Invariant: TOTAL = PARSED + PARTIAL + AMBIGUOUS + UNPARSED
    ledger = db_session.query(ParsingLedger).filter(ParsingLedger.ingestion_id == ing_run.ingestion_id).first()
    assert ledger is not None
    assert ledger.reconciled is True
    assert ledger.total_records == (ledger.parsed_count + ledger.partial_count + ledger.ambiguous_count + ledger.unparsed_count)

    # Verify timeline events were created for parsed records
    events = db_session.query(TimelineEvent).filter(TimelineEvent.ingestion_id == ing_run.ingestion_id).all()
    assert len(events) == 2
    for e in events:
        assert e.evidence_id == ev.evidence_id
        assert e.source_line in (1, 3)
