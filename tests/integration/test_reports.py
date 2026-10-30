import os
from pathlib import Path
from app.services.report_service import generate_pdf_report, export_timeline_csv, export_parsing_gaps_csv
from app.services.evidence_service import collect_evidence_file
from app.services.ingestion_service import run_ingestion
from app.services.investigation_service import create_investigation, create_finding

def test_generate_pdf_report_and_csv(db_session):
    # Setup sample evidence and events
    content = b"Oct 27 10:30:01 host01 sshd[1234]: Failed password for admin from 192.0.2.10 port 52100 ssh2\n"
    ev = collect_evidence_file(db_session, "report_test.log", content)
    run_ingestion(db_session, ev.evidence_id, parser_name="linux_auth")

    inv = create_investigation(db_session, "Report Test Investigation")
    create_finding(db_session, inv.investigation_id, title="Test Finding")

    # Generate PDF Report
    report = generate_pdf_report(db_session, investigation_id=inv.investigation_id, title="Test Incident Report")
    assert report.report_id.startswith("REP-")
    assert report.file_format == "PDF"
    assert len(report.sha256_digest) == 64

    # Verify physical PDF file exists on disk and is non-empty
    pdf_path = Path(report.file_path)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 500

    # Test Timeline CSV export
    csv_content = export_timeline_csv(db_session)
    assert "Event ID,Evidence ID,Source Line" in csv_content
    assert "192.0.2.10" in csv_content

    # Test Gaps CSV export
    gaps_content = export_parsing_gaps_csv(db_session)
    assert "Source Record ID,Evidence ID" in gaps_content
