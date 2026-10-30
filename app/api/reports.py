from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.entities import GeneratedReport
from app.schemas.schemas import ReportCreateRequest
from app.services.report_service import generate_pdf_report, export_timeline_csv, export_parsing_gaps_csv

router = APIRouter(prefix="/reports", tags=["Incident Reports"])

@router.post("", status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreateRequest, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Generates an official incident report in PDF format."""
    try:
        report = generate_pdf_report(
            db=db,
            investigation_id=payload.investigation_id,
            title=payload.title,
            actor=actor
        )
        return {
            "report_id": report.report_id,
            "title": report.title,
            "format": report.file_format,
            "sha256_digest": report.sha256_digest,
            "created_at": report.created_at.isoformat(),
            "download_url": f"/api/reports/{report.report_id}/download",
            "message": "Report generated successfully."
        }
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(ex)}")

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    """Lists all previously generated reports."""
    reports = db.query(GeneratedReport).order_by(desc(GeneratedReport.created_at)).all()
    return [
        {
            "report_id": r.report_id,
            "investigation_id": r.investigation_id,
            "title": r.title,
            "format": r.file_format,
            "sha256_digest": r.sha256_digest,
            "created_at": r.created_at.isoformat(),
            "download_url": f"/api/reports/{r.report_id}/download"
        }
        for r in reports
    ]

@router.get("/{report_id}/download")
def download_report(report_id: str, db: Session = Depends(get_db)):
    """Downloads the generated PDF report."""
    report = db.query(GeneratedReport).filter(GeneratedReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Underlying report file missing on disk.")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"{report.report_id}.pdf"
    )

@router.get("/export/csv")
def download_timeline_csv(evidence_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Exports chronological timeline records in CSV format."""
    csv_data = export_timeline_csv(db, evidence_id=evidence_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tracelens_timeline.csv"}
    )

@router.get("/export/gaps-csv")
def download_gaps_csv(db: Session = Depends(get_db)):
    """Exports parsing ledger gap records (non-PARSED lines) in CSV format."""
    csv_data = export_parsing_gaps_csv(db)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tracelens_parsing_gaps.csv"}
    )
