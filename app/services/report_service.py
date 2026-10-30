import io
import csv
import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

from app.config import settings
from app.models.entities import (
    Investigation, InvestigationFinding, EvidenceFile, IntegrityVerification,
    IngestionRun, ParsingLedger, TimelineEvent, ClockSkewEstimate,
    BlindLensReview, GeneratedReport, EvaluationRun
)

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Top Header (omitted on cover/page 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "TRACELENS | INCIDENT TIMELINE & EVIDENCE REPORT")
            self.drawRightString(558, 750, "OFFICIAL USE ONLY / EVIDENCE RECORD")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Bottom Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawString(54, 36, "Synthetic Demonstration — Not Certified Digital Evidence")
        self.drawRightString(558, 36, page_str)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 558, 46)

        self.restoreState()

def generate_pdf_report(
    db: Session,
    investigation_id: Optional[str] = None,
    title: str = "Incident Evidence and Timeline Report",
    actor: str = "Lead Analyst"
) -> GeneratedReport:
    """
    Generates a formal, 19-section digital incident investigation report in PDF format
    using ReportLab, calculating live database records.
    """
    report_id = f"REP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    filename = f"{report_id}.pdf"
    file_path = settings.REPORTS_DIR / filename

    # Retrieve data
    investigation = None
    findings = []
    reviews = []
    if investigation_id:
        investigation = db.query(Investigation).filter(Investigation.investigation_id == investigation_id).first()
        if investigation:
            findings = db.query(InvestigationFinding).filter(InvestigationFinding.investigation_id == investigation_id).all()
            reviews = db.query(BlindLensReview).filter(BlindLensReview.investigation_id == investigation_id).all()

    evidence_files = db.query(EvidenceFile).all()
    events = db.query(TimelineEvent).order_by(TimelineEvent.normalized_utc.asc().nullsfirst()).limit(150).all()
    ledgers = db.query(ParsingLedger).all()
    estimates = db.query(ClockSkewEstimate).all()
    latest_eval = db.query(EvaluationRun).order_by(desc(EvaluationRun.run_at)).first()

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12
    )
    h1_style = ParagraphStyle(
        "Heading1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4
    )
    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0f172a")
    )
    tag_style = ParagraphStyle(
        "TagText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white
    )

    story = []

    # Title & Metadata Header
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(
        f"<b>Report ID:</b> {report_id} &nbsp;|&nbsp; "
        f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} &nbsp;|&nbsp; "
        f"<b>Investigator:</b> {actor} &nbsp;|&nbsp; "
        f"<b>Problem Statement:</b> {settings.PROBLEM_STATEMENT}",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=10))

    # Executive Summary / Investigation Overview
    story.append(Paragraph("1. Investigation Context & Scope", h1_style))
    if investigation:
        inv_desc = f"<b>Investigation:</b> {investigation.title} ({investigation.investigation_id})<br/>" \
                   f"<b>Status:</b> {investigation.status} | <b>Lead:</b> {investigation.lead_investigator}<br/>" \
                   f"<b>Summary:</b> {investigation.description or 'No general description recorded.'}"
    else:
        inv_desc = "Global incident timeline export encompassing all ingested evidence files and analytical ledger accounts."
    story.append(Paragraph(inv_desc, body_style))

    # Evidence Inventory & SHA-256 Baselines
    story.append(Paragraph("2. Evidence Inventory & Cryptographic Baseline Hashes", h1_style))
    ev_data = [["Evidence ID", "Original Filename", "Size (bytes)", "SHA-256 Baseline Digest", "Latest Status"]]
    for ev in evidence_files:
        latest_v = db.query(IntegrityVerification).filter(IntegrityVerification.evidence_id == ev.evidence_id).order_by(desc(IntegrityVerification.verified_at)).first()
        status_txt = latest_v.result if latest_v else "UNVERIFIED"
        ev_data.append([
            ev.evidence_id,
            ev.original_filename[:20],
            str(ev.file_size_bytes),
            Paragraph(ev.sha256_baseline[:24] + "...", code_style),
            status_txt
        ])
    if len(ev_data) > 1:
        ev_table = Table(ev_data, colWidths=[80, 110, 65, 165, 84])
        ev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(ev_table)
    else:
        story.append(Paragraph("No evidence files currently collected in repository.", body_style))

    # Parsing Ledger Reconciliation
    story.append(Spacer(1, 8))
    story.append(Paragraph("3. Parsing Ledger Accounting (Invariant: TOTAL = PARSED + PARTIAL + AMBIGUOUS + UNPARSED)", h1_style))
    ledger_data = [["Ingestion ID", "Evidence ID", "Total", "Parsed", "Partial", "Ambiguous", "Unparsed", "Reconciled"]]
    for lg in ledgers:
        ledger_data.append([
            lg.ingestion_id[:16],
            lg.evidence_id,
            str(lg.total_records),
            str(lg.parsed_count),
            str(lg.partial_count),
            str(lg.ambiguous_count),
            str(lg.unparsed_count),
            "YES" if lg.reconciled else "NO"
        ])
    if len(ledger_data) > 1:
        lg_table = Table(ledger_data, colWidths=[90, 80, 50, 50, 50, 60, 55, 69])
        lg_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(lg_table)

    # Mutation Radar Alerts
    story.append(Spacer(1, 8))
    story.append(Paragraph("4. Mutation Radar & Evidence Integrity Impact Analysis", h1_style))
    mismatches = db.query(IntegrityVerification).filter(IntegrityVerification.result == "MISMATCH").all()
    if mismatches:
        mut_text = f"<b>ALERT:</b> {len(mismatches)} hash verification mismatch(es) detected across collected evidence.<br/>"
        for m in mismatches:
            mut_text += f"- Evidence <b>{m.evidence_id}</b> failed baseline verification at {m.verified_at.strftime('%Y-%m-%d %H:%M:%S UTC')}.<br/>"
        story.append(Paragraph(mut_text, body_style))
    else:
        story.append(Paragraph("All verified evidence baselines match on-disk copies. No post-collection file mutations detected.", body_style))

    # Clock-Skew Estimates
    story.append(Spacer(1, 8))
    story.append(Paragraph("5. Clock-Skew Estimates & Correlation Assumptions", h1_style))
    if estimates:
        skew_data = [["Estimate ID", "Source A", "Source B", "Offset (s)", "Confidence", "Assumptions"]]
        for es in estimates:
            off_str = f"{es.estimated_offset_seconds:+.2f}s" if es.estimated_offset_seconds is not None else "N/A"
            skew_data.append([
                es.estimate_id,
                es.source_evidence_a_id[:12],
                es.source_evidence_b_id[:12],
                off_str,
                es.confidence,
                Paragraph(es.assumptions or "-", body_style)
            ])
        sk_table = Table(skew_data, colWidths=[70, 75, 75, 55, 75, 154])
        sk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(sk_table)
    else:
        story.append(Paragraph("No clock-skew estimation sessions recorded.", body_style))

    # BlindLens Review Trail
    story.append(Spacer(1, 8))
    story.append(Paragraph("6. BlindLens Staged Investigator Review Trail", h1_style))
    if reviews:
        for r in reviews:
            rev_p = f"<b>Review ID:</b> {r.review_id} | <b>Investigator:</b> {r.investigator_id} | <b>Stage:</b> {r.stage}<br/>" \
                    f"<b>Initial Hypothesis:</b> {r.initial_hypothesis} (Confidence: {r.initial_confidence}%)<br/>" \
                    f"<b>Stage 1 Digest:</b> <font face='Courier' size=7>{r.initial_digest}</font><br/>"
            if r.stage == "REVEALED":
                rev_p += f"<b>Context Revealed At:</b> {r.context_revealed_at.strftime('%Y-%m-%d %H:%M:%S UTC') if r.context_revealed_at else '-'}<br/>" \
                         f"<b>Revised Hypothesis:</b> {r.revised_hypothesis} (Confidence: {r.revised_confidence}%)<br/>" \
                         f"<b>Rationale for Change:</b> {r.reason_for_change}<br/>" \
                         f"<b>Final Status:</b> {r.final_review_status} | <b>Final Digest:</b> <font face='Courier' size=7>{r.final_digest}</font><br/>"
            story.append(Paragraph(rev_p, body_style))
    else:
        story.append(Paragraph("No BlindLens staged reviews conducted for this scope.", body_style))

    # Findings
    story.append(Spacer(1, 8))
    story.append(Paragraph("7. Investigative Findings & Hypotheses", h1_style))
    if findings:
        for f in findings:
            rev_flag = " <font color='#e11d48'>[REQUIRES REVIEW: Evidence Mismatch]</font>" if f.requires_review else ""
            f_text = f"<b>Finding {f.finding_id}:</b> {f.title} — <b>Status: {f.status}</b>{rev_flag}<br/>" \
                     f"<b>Rationale:</b> {f.rationale or 'None recorded.'}<br/>" \
                     f"<b>Unresolved Questions:</b> {f.unresolved_questions or 'None.'}"
            story.append(Paragraph(f_text, body_style))
    else:
        story.append(Paragraph("No findings linked to this investigation scope.", body_style))

    # Timeline Extract
    story.append(Spacer(1, 8))
    story.append(Paragraph("8. Chronological Incident Timeline (Extract)", h1_style))
    tl_data = [["Normalized UTC", "Uncertainty Interval [t-Δ, t+Δ]", "Source IP / User", "Summary", "Order"]]
    for ev in events[:40]:  # Limit top 40 for PDF summary table
        utc_str = ev.normalized_utc.strftime("%Y-%m-%d %H:%M:%S") if ev.normalized_utc else "UNRESOLVED"
        earliest_str = ev.earliest_utc.strftime("%H:%M:%S") if ev.earliest_utc else "-"
        latest_str = ev.latest_utc.strftime("%H:%M:%S") if ev.latest_utc else "-"
        interval_str = f"[{earliest_str} to {latest_str}]"
        src_str = f"{ev.source_ip or '-'}\n{ev.username or ''}"
        order_str = "UNCERTAIN" if ev.order_uncertain else "Certain"
        tl_data.append([
            utc_str,
            interval_str,
            src_str,
            Paragraph(ev.summary[:90], body_style),
            order_str
        ])
    if len(tl_data) > 1:
        tl_table = Table(tl_data, colWidths=[90, 105, 85, 175, 49])
        tl_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(tl_table)

    # Benchmark & Pilot Triage
    if latest_eval:
        story.append(Spacer(1, 8))
        story.append(Paragraph("9. Empirical Evaluation & Triage Benchmarks", h1_style))
        eval_txt = f"<b>Traceability Rate:</b> {latest_eval.traceability_rate}% &nbsp;|&nbsp; " \
                   f"<b>Parsing Accuracy:</b> {latest_eval.parsing_accuracy}% &nbsp;|&nbsp; " \
                   f"<b>Mutation Detection:</b> {latest_eval.mutation_detection_rate}%<br/>" \
                   f"<b>Manual Triage Median:</b> {latest_eval.manual_triage_median_sec or 'N/A'}s &nbsp;|&nbsp; " \
                   f"<b>TraceLens-Assisted Triage Median:</b> {latest_eval.assisted_triage_median_sec or 'N/A'}s"
        story.append(Paragraph(eval_txt, body_style))

    # Limitations & Legal / Standards Notice
    story.append(Spacer(1, 10))
    story.append(Paragraph("10. Standards Adherence & Limitations Notice", h1_style))
    standards_text = (
        "<b>Notice of Forensic Scope & Scientific Limitations:</b><br/>"
        "1. <i>Evidence Integrity:</i> SHA-256 digests provide cryptographic verification against recorded application baselines "
        "in compliance with NIST FIPS 180-4 and RFC 3227. However, application-level verification on a local workstation does not "
        "guarantee physical custody integrity or legal chain-of-custody certification.<br/>"
        "2. <i>Log Management:</i> Parsing operates in accordance with NIST SP 800-92. Inferred timestamps (such as syslog records "
        "lacking timezone/year) represent documented analytical assumptions and must not be interpreted as absolute observed facts.<br/>"
        "3. <i>Uncertainty Modeling:</i> Temporal intervals reflect configured clock tolerance bounds. Overlapping intervals indicate "
        "order uncertainty under the selected model; they do not establish causal succession.<br/>"
        "4. <i>Investigator Assessment:</i> BlindLens structured reviews record the chronology of investigator interpretations and "
        "context reveals. The application does not claim to diagnose, detect, or eliminate cognitive bias."
    )
    story.append(Paragraph(standards_text, body_style))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)

    # Compute digest of generated PDF file
    sha256_report = ""
    with open(file_path, "rb") as f:
        sha256_report = hashlib.sha256(f.read()).hexdigest().lower()

    report_record = GeneratedReport(
        report_id=report_id,
        investigation_id=investigation_id,
        title=title,
        file_path=str(file_path),
        file_format="PDF",
        sha256_digest=sha256_report,
        created_at=datetime.now(timezone.utc),
        record_count=len(events),
        metadata_json=json.dumps({
            "investigation_id": investigation_id,
            "events_count": len(events),
            "evidence_count": len(evidence_files)
        })
    )
    db.add(report_record)
    db.commit()
    db.refresh(report_record)
    return report_record

def export_timeline_csv(db: Session, evidence_id: Optional[str] = None) -> str:
    """Exports timeline events as a standardized CSV string."""
    query = db.query(TimelineEvent)
    if evidence_id:
        query = query.filter(TimelineEvent.evidence_id == evidence_id)
    events = query.order_by(TimelineEvent.normalized_utc.asc().nullsfirst()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Event ID", "Evidence ID", "Source Line", "Raw Timestamp", "Normalized UTC",
        "Earliest UTC", "Latest UTC", "Uncertainty Seconds", "Order Uncertain",
        "Event Type", "Source IP", "Port", "Username", "HTTP Method", "Target",
        "HTTP Status", "Summary", "Parsing Status", "Warnings"
    ])
    for e in events:
        writer.writerow([
            e.event_id,
            e.evidence_id,
            e.source_line,
            e.raw_timestamp or "",
            e.normalized_utc.isoformat() if e.normalized_utc else "",
            e.earliest_utc.isoformat() if e.earliest_utc else "",
            e.latest_utc.isoformat() if e.latest_utc else "",
            e.uncertainty_margin_seconds,
            "TRUE" if e.order_uncertain else "FALSE",
            e.event_type or "",
            e.source_ip or "",
            e.source_port or "",
            e.username or "",
            e.http_method or "",
            e.http_target or "",
            e.http_status or "",
            e.summary or "",
            e.parsing_status,
            e.warnings or ""
        ])
    return output.getvalue()

def export_parsing_gaps_csv(db: Session) -> str:
    """Exports all non-PARSED source records (PARTIAL, AMBIGUOUS, UNPARSED) as CSV."""
    from app.models.entities import SourceRecord
    gaps = db.query(SourceRecord).filter(SourceRecord.parsing_status != "PARSED").all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Source Record ID", "Evidence ID", "Ingestion ID", "Line Number", "Parsing Status", "Warnings", "Raw Text"])
    for g in gaps:
        writer.writerow([
            g.id,
            g.evidence_id,
            g.ingestion_id,
            g.line_number,
            g.parsing_status,
            g.parser_warnings or "",
            g.raw_text.strip()
        ])
    return output.getvalue()
