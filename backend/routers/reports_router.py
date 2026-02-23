"""WASTE IQ – Reports Router"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from auth import require_admin, require_municipal, UserInfo
from firestore_client import query_collection
from models import APIResponse
from datetime import datetime, timezone
import io, csv

router = APIRouter()

@router.get("/city-summary", response_model=APIResponse)
async def city_summary(user: UserInfo = Depends(require_municipal)):
    """Return city-wide waste statistics for admin view."""
    waste_logs   = query_collection("waste_logs", limit=1000)
    bins         = query_collection("bins")
    complaints   = query_collection("complaints")
    users_all    = query_collection("users")

    from collections import Counter
    categories   = Counter(l.get("waste_category", "Unknown") for l in waste_logs)
    bin_statuses = Counter(b.get("status", "active") for b in bins)
    complaint_st = Counter(c.get("status", "open") for c in complaints)
    roles        = Counter(u.get("role", "household") for u in users_all)

    # Ward performance
    ward_complaints = {}
    for c in complaints:
        ward = c.get("ward_id", "unknown")
        if ward not in ward_complaints:
            ward_complaints[ward] = {"total": 0, "resolved": 0}
        ward_complaints[ward]["total"] += 1
        if c.get("status") == "resolved":
            ward_complaints[ward]["resolved"] += 1

    ward_ranking = sorted([
        {"ward_id": w, **stats,
         "resolution_rate": round(stats["resolved"] / max(stats["total"], 1) * 100, 1)}
        for w, stats in ward_complaints.items()
    ], key=lambda x: -x["resolution_rate"])

    return APIResponse(success=True, message="City summary", data={
        "total_users":          len(users_all),
        "total_bins":           len(bins),
        "total_classifications": len(waste_logs),
        "total_complaints":     len(complaints),
        "waste_by_category":    dict(categories),
        "bins_by_status":       dict(bin_statuses),
        "complaints_by_status": dict(complaint_st),
        "users_by_role":        dict(roles),
        "ward_ranking":         ward_ranking,
    })

@router.get("/export-csv")
async def export_csv(report_type: str = "waste_logs", user: UserInfo = Depends(require_municipal)):
    """Export data as CSV file."""
    valid_types = {"waste_logs", "bins", "complaints", "gamification"}
    if report_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid report type. Use one of: {valid_types}")

    docs = query_collection(report_type, limit=5000)
    if not docs:
        raise HTTPException(status_code=404, detail="No data found")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=docs[0].keys(), extrasaction="ignore")
    writer.writeheader()
    for doc in docs:
        writer.writerow({k: str(v) if isinstance(v, (dict, list)) else v for k, v in doc.items()})

    output.seek(0)
    filename = f"wasteiq_{report_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.read().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.get("/export-pdf")
async def export_pdf(user: UserInfo = Depends(require_municipal)):
    """Generate a city waste report PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed")

    # Fetch data
    waste_logs = query_collection("waste_logs", limit=1000)
    bins       = query_collection("bins")
    complaints = query_collection("complaints")

    from collections import Counter
    categories  = Counter(l.get("waste_category", "Unknown") for l in waste_logs)
    bin_stats   = Counter(b.get("status", "active") for b in bins)
    comp_stats  = Counter(c.get("status", "open") for c in complaints)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles  = getSampleStyleSheet()
    elements= []

    # Title
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=24, textColor=colors.HexColor("#1a7a4a"), spaceAfter=6)
    elements.append(Paragraph("WASTE IQ – City Waste Report", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M UTC')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # Summary table
    summary_data = [
        ["Metric", "Value"],
        ["Total Classifications", str(len(waste_logs))],
        ["Total Bins Monitored", str(len(bins))],
        ["Total Complaints",     str(len(complaints))],
        ["Overflow Bins",        str(bin_stats.get("overflow", 0))],
        ["Open Complaints",      str(comp_stats.get("open", 0))],
        ["Resolved Complaints",  str(comp_stats.get("resolved", 0))],
    ]
    t = Table(summary_data, colWidths=[3*inch, 2*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a7a4a")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f8f4"), colors.white]),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE",   (0, 0), (-1, -1), 11),
        ("PADDING",    (0, 0), (-1, -1), 8),
    ]))
    elements.append(Paragraph("Executive Summary", styles["Heading2"]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Waste categories breakdown
    elements.append(Paragraph("Waste by Category", styles["Heading2"]))
    cat_data = [["Category", "Count", "Percentage"]] + [
        [cat, str(count), f"{round(count/max(len(waste_logs),1)*100,1)}%"]
        for cat, count in sorted(categories.items(), key=lambda x: -x[1])
    ]
    ct = Table(cat_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6a4f")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f8f4"), colors.white]),
        ("PADDING",    (0, 0), (-1, -1), 8),
    ]))
    elements.append(ct)

    doc.build(elements)
    buf.seek(0)
    filename = f"wasteiq_report_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})
