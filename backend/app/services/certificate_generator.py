"""Generate tamper-evident ISO 9001:2015 Clause 8.7 Quality Certificates.

Produces self-contained, printable HTML/PDF quality compliance certificates
containing cryptographic audit hashes, regulatory standard citations, defect
evidence, telemetry logs, and a structured 4-part CAPA remediation plan.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.schemas.inspection import InspectionReport


def render_iso_certificate_html(report: "InspectionReport") -> str:
    """Render a self-contained, printable ISO 9001 Quality Certificate."""
    # Escape user values for HTML safety
    obj_name = html.escape(report.object_name)
    insp_id = html.escape(report.inspection_id)
    time_str = html.escape(report.inspection_time.strftime("%Y-%m-%d %H:%M:%S UTC"))
    std_name = html.escape(report.compliance_standard)
    defect_type = html.escape(report.defect_type.upper())
    defect_desc = html.escape(report.defect_description or report.risk_explanation or "None")
    defect_loc = html.escape(report.defect_location or "General surface")
    conf_pct = f"{report.confidence * 100:.1f}%"
    severity = report.severity_level.value.upper()
    action = report.recommended_action.value.replace("_", " ").upper()
    risk_exp = html.escape(report.risk_explanation)
    audit_hash = html.escape(report.audit_hash or "UNVERIFIED")

    # Determine disposition badge styling (Hold if human review required)
    if report.requires_human_review and report.severity_level.rank < 2:
        disposition_title = "NON-CONFORMING — CONDITIONAL HOLD / PENDING REVIEW"
        disposition_class = "disposition-hold"
        disposition_desc = "Mandatory secondary supervisor evaluation required prior to disposition."
    elif report.severity_level.rank >= 2:
        disposition_title = "NON-CONFORMING — QUARANTINE / REJECT"
        disposition_class = "disposition-reject"
        disposition_desc = "Immediate halt or quarantine required. Defect exceeds safety tolerance."
    elif report.severity_level.rank == 1:
        disposition_title = "NON-CONFORMING — CONDITIONAL HOLD / REINSPECT"
        disposition_class = "disposition-hold"
        disposition_desc = "Secondary inspection or engineering evaluation required prior to release."
    else:
        disposition_title = "CONFORMING — APPROVED FOR RELEASE"
        disposition_class = "disposition-pass"
        disposition_desc = "Inspection criteria satisfied within allowable standard tolerances."

    # Render human review reasons if flagged
    review_reasons_html = ""
    if report.requires_human_review and report.human_review_reasons:
        reasons_list = "".join(f"<li>{html.escape(r)}</li>" for r in report.human_review_reasons)
        review_reasons_html = f"""
        <div style="margin-top: 8px; padding: 8px 12px; background: #FFFBEB; border-left: 3px solid #B45309; border-radius: 4px; font-size: 8.5pt;">
            <strong style="color: #B45309;">Supervisor Escalation Triggers:</strong>
            <ul style="margin: 4px 0 0 16px; padding: 0;">{reasons_list}</ul>
        </div>
        """

    # Render clauses
    clause_rows = []
    if report.standard_evidence:
        for ev in report.standard_evidence:
            c_id = html.escape(ev.clause_id or "REF")
            c_title = html.escape(ev.title or "Standard Clause")
            c_text = html.escape(ev.text)
            clause_rows.append(
                f"""
                <div class="clause-item">
                    <div class="clause-head">
                        <span class="clause-tag">CLAUSE {c_id}</span>
                        <span class="clause-title">{c_title}</span>
                        <span class="clause-score">Score: {ev.score:.3f}</span>
                    </div>
                    <div class="clause-text">{c_text}</div>
                </div>
                """
            )
    else:
        clause_rows.append("<div class='clause-item'><em>No matching regulatory clauses recorded.</em></div>")
    clauses_html = "".join(clause_rows)

    # Render sensors
    sensor_rows = []
    if report.sensor_readings:
        for s in report.sensor_readings:
            s_name = html.escape(s.name)
            s_val = f"{s.value:.2f}"
            s_unit = html.escape(s.unit or "")
            sensor_rows.append(
                f"""
                <tr>
                    <td><strong>{s_name}</strong></td>
                    <td>{s_val} {s_unit}</td>
                    <td><span class="sensor-tag">LOGGED</span></td>
                </tr>
                """
            )
    else:
        sensor_rows.append("<tr><td colspan='3'><em>No sensor telemetry provided for this inspection.</em></td></tr>")
    sensors_html = "".join(sensor_rows)

    # Render CAPA plan
    capa = report.capa_plan
    if capa:
        capa_html = f"""
        <div class="capa-grid">
            <div class="capa-card">
                <span class="capa-label">1. Immediate Containment</span>
                <p>{html.escape(capa.immediate_containment)}</p>
            </div>
            <div class="capa-card">
                <span class="capa-label">2. Root Cause Analysis</span>
                <p>{html.escape(capa.root_cause_analysis)}</p>
            </div>
            <div class="capa-card">
                <span class="capa-label">3. Corrective Action</span>
                <p>{html.escape(capa.corrective_action)}</p>
            </div>
            <div class="capa-card">
                <span class="capa-label">4. Preventive Action</span>
                <p>{html.escape(capa.preventive_action)}</p>
            </div>
        </div>
        """
    else:
        capa_html = "<p><em>Standard operating procedure applies. No non-conformance CAPA required.</em></p>"

    # Bounding box coordinates display
    bbox_str = "None specified"
    if report.defect_bbox:
        bbox_str = (
            f"x: {report.defect_bbox.x:.3f}, y: {report.defect_bbox.y:.3f}, "
            f"w: {report.defect_bbox.width:.3f}, h: {report.defect_bbox.height:.3f}"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ISO 9001 Quality Certificate - {insp_id}</title>
<style>
    @page {{
        size: A4;
        margin: 12mm 15mm;
    }}
    :root {{
        --primary: #0F172A;
        --accent: #2563EB;
        --border: #CBD5E1;
        --bg-subtle: #F8FAFC;
        --text-dark: #0F172A;
        --text-muted: #475569;
        --pass-color: #15803D;
        --hold-color: #B45309;
        --reject-color: #B91C1C;
    }}
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: var(--text-dark);
        background: #FFFFFF;
        line-height: 1.45;
        font-size: 11pt;
        padding: 24px;
    }}
    .cert-container {{
        max-width: 900px;
        margin: 0 auto;
        border: 2px solid var(--border);
        border-radius: 6px;
        padding: 32px 36px;
        background: #FFFFFF;
    }}
    .cert-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 2px solid var(--primary);
        padding-bottom: 16px;
        margin-bottom: 20px;
    }}
    .cert-brand {{
        display: flex;
        flex-direction: column;
    }}
    .cert-brand h1 {{
        font-size: 16pt;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: var(--primary);
        text-transform: uppercase;
    }}
    .cert-brand .cert-sub {{
        font-size: 9pt;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 2px;
    }}
    .cert-meta-box {{
        text-align: right;
        font-size: 9pt;
    }}
    .cert-meta-box strong {{
        color: var(--primary);
    }}
    .audit-seal {{
        display: inline-block;
        padding: 4px 8px;
        background: var(--bg-subtle);
        border: 1px solid var(--border);
        border-radius: 4px;
        font-family: "Courier New", Courier, monospace;
        font-size: 8pt;
        margin-top: 4px;
        word-break: break-all;
    }}
    .disposition-banner {{
        border: 2px solid;
        border-radius: 6px;
        padding: 14px 18px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .disposition-pass {{
        border-color: var(--pass-color);
        background: #F0FDF4;
        color: var(--pass-color);
    }}
    .disposition-hold {{
        border-color: var(--hold-color);
        background: #FFFBEB;
        color: var(--hold-color);
    }}
    .disposition-reject {{
        border-color: var(--reject-color);
        background: #FEF2F2;
        color: var(--reject-color);
    }}
    .disposition-title {{
        font-size: 13pt;
        font-weight: 800;
        letter-spacing: 0.5px;
    }}
    .disposition-desc {{
        font-size: 9pt;
        font-weight: 500;
        margin-top: 2px;
        color: var(--text-dark);
    }}
    .section-title {{
        font-size: 11pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: var(--primary);
        border-bottom: 1px solid var(--border);
        padding-bottom: 4px;
        margin: 20px 0 10px 0;
    }}
    .info-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px 16px;
        font-size: 9.5pt;
        margin-bottom: 16px;
    }}
    .info-row {{
        display: flex;
    }}
    .info-label {{
        width: 140px;
        font-weight: 600;
        color: var(--text-muted);
    }}
    .info-value {{
        flex: 1;
        color: var(--text-dark);
        font-weight: 500;
    }}
    .clauses-container {{
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 16px;
    }}
    .clause-item {{
        background: var(--bg-subtle);
        border: 1px solid var(--border);
        border-left: 3px solid var(--accent);
        border-radius: 4px;
        padding: 8px 12px;
        font-size: 9pt;
    }}
    .clause-head {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 700;
        margin-bottom: 4px;
    }}
    .clause-tag {{
        background: var(--primary);
        color: #FFFFFF;
        font-size: 7.5pt;
        padding: 2px 6px;
        border-radius: 3px;
    }}
    .clause-score {{
        margin-left: auto;
        color: var(--text-muted);
        font-size: 8pt;
    }}
    .clause-text {{
        color: var(--text-dark);
        font-size: 8.5pt;
    }}
    .sensor-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 9pt;
        margin-bottom: 16px;
    }}
    .sensor-table th, .sensor-table td {{
        border: 1px solid var(--border);
        padding: 6px 10px;
        text-align: left;
    }}
    .sensor-table th {{
        background: var(--bg-subtle);
        font-weight: 700;
        color: var(--text-muted);
    }}
    .sensor-tag {{
        display: inline-block;
        padding: 1px 6px;
        background: #E2E8F0;
        border-radius: 3px;
        font-size: 7.5pt;
        font-weight: 600;
    }}
    .capa-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        margin-bottom: 24px;
    }}
    .capa-card {{
        background: var(--bg-subtle);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 10px 12px;
        font-size: 8.5pt;
    }}
    .capa-label {{
        display: block;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 4px;
        text-transform: uppercase;
        font-size: 8pt;
        letter-spacing: 0.4px;
    }}
    .signoff-section {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        border-top: 1px dashed var(--border);
        padding-top: 20px;
        margin-top: 30px;
    }}
    .signoff-box {{
        font-size: 8.5pt;
        text-align: center;
    }}
    .signoff-line {{
        border-bottom: 1px solid var(--text-dark);
        height: 36px;
        margin-bottom: 6px;
    }}
    .signoff-name {{
        font-weight: 700;
        color: var(--primary);
    }}
    .signoff-role {{
        color: var(--text-muted);
        font-size: 7.5pt;
    }}
    .no-print-bar {{
        max-width: 900px;
        margin: 0 auto 16px auto;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 16px;
        background: #0F172A;
        color: #FFFFFF;
        border-radius: 6px;
    }}
    .btn-print {{
        background: #2563EB;
        color: #FFFFFF;
        border: none;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 9pt;
        border-radius: 4px;
        cursor: pointer;
    }}
    .btn-print:hover {{
        background: #1D4ED8;
    }}
    @media print {{
        body {{
            padding: 0;
            background: #FFFFFF;
        }}
        .no-print-bar {{
            display: none !important;
        }}
        .cert-container {{
            border: none;
            padding: 0;
            max-width: 100%;
        }}
    }}
</style>
</head>
<body>

<div class="no-print-bar">
    <span><strong>Official Quality Document</strong> — Ready for archiving and audit trail inspection.</span>
    <button class="btn-print" onclick="window.print()">Print / Save PDF</button>
</div>

<div class="cert-container">
    <header class="cert-header">
        <div class="cert-brand">
            <h1>Certificate of Quality Audit</h1>
            <div class="cert-sub">{std_name} Non-Conformance Record</div>
        </div>
        <div class="cert-meta-box">
            <div>Certificate ID: <strong>CERT-{insp_id}</strong></div>
            <div>Date Issued: <strong>{time_str}</strong></div>
            <div class="audit-seal" title="Cryptographic SHA-256 Digest">SHA-256: {audit_hash[:24]}...</div>
        </div>
    </header>

    <div class="disposition-banner {disposition_class}">
        <div>
            <div class="disposition-title">{disposition_title}</div>
            <div class="disposition-desc">{disposition_desc}</div>
        </div>
        <div style="text-align: right; font-weight: 700; font-size: 11pt;">
            Severity: {severity}<br>Action: {action}
        </div>
    </div>

    <div class="section-title">1. Inspection Target & Asset Details</div>
    <div class="info-grid">
        <div class="info-row"><span class="info-label">Object / Component:</span><span class="info-value"><strong>{obj_name}</strong></span></div>
        <div class="info-row"><span class="info-label">Inspection ID:</span><span class="info-value">{insp_id}</span></div>
        <div class="info-row"><span class="info-label">Inspection Engine:</span><span class="info-value">{html.escape(report.detector or "DefectDetector")} ({html.escape(report.detector_model or "Standard")})</span></div>
        <div class="info-row"><span class="info-label">Human Review:</span><span class="info-value"><strong>{'REQUIRED' if report.requires_human_review else 'NOT REQUIRED'}</strong></span></div>
    </div>

    <div class="section-title">2. Visual Defect Analysis & Bounding Box</div>
    <div class="info-grid">
        <div class="info-row"><span class="info-label">Defect Classification:</span><span class="info-value"><strong>{defect_type}</strong></span></div>
        <div class="info-row"><span class="info-label">Detection Confidence:</span><span class="info-value"><strong>{conf_pct}</strong></span></div>
        <div class="info-row"><span class="info-label">Surface Location:</span><span class="info-value">{defect_loc}</span></div>
        <div class="info-row"><span class="info-label">Coordinates (Normalized):</span><span class="info-value">{bbox_str}</span></div>
        <div class="info-row" style="grid-column: span 2;"><span class="info-label">Visual Description:</span><span class="info-value">{defect_desc}</span></div>
    </div>

    <div class="section-title">3. Decision Rationale & Risk Assessment</div>
    <div style="background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 4px; padding: 10px 14px; font-size: 9pt; margin-bottom: 16px;">
        <p><strong>Risk Evaluation:</strong> {risk_exp}</p>
        {review_reasons_html}
    </div>

    <div class="section-title">4. Standard Regulatory Citations (Evidence Grounding)</div>
    <div class="clauses-container">
        {clauses_html}
    </div>

    <div class="section-title">5. Physical Telemetry Log</div>
    <table class="sensor-table">
        <thead>
            <tr>
                <th style="width: 40%;">Parameter</th>
                <th style="width: 40%;">Observed Value</th>
                <th style="width: 20%;">Telemetry Status</th>
            </tr>
        </thead>
        <tbody>
            {sensors_html}
        </tbody>
    </table>

    <div class="section-title">6. Corrective & Preventive Action Plan (CAPA)</div>
    {capa_html}

    <div class="section-title">7. Audit Integrity & Cryptographic Chain of Custody</div>
    <p style="font-size: 8.5pt; color: var(--text-muted); margin-bottom: 8px;">
        This document represents an automated regulatory inspection record pursuant to ISO 9001:2015 Clause 8.7.
        All raw inputs (source image, inspection standard, sensor time-series) and decision variables have been
        cryptographically bound into the SHA-256 seal below.
    </p>
    <div style="background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 4px; padding: 6px 10px; font-family: monospace; font-size: 8pt; word-break: break-all;">
        <strong>Audit Digest:</strong> {audit_hash}
    </div>

    <footer class="signoff-section">
        <div class="signoff-box">
            <div class="signoff-line"></div>
            <div class="signoff-name">Automated Inspection Agent</div>
            <div class="signoff-role">System Verification Signature</div>
        </div>
        <div class="signoff-box">
            <div class="signoff-line"></div>
            <div class="signoff-name">Lead Quality Auditor</div>
            <div class="signoff-role">Quality Assurance Inspector</div>
        </div>
        <div class="signoff-box">
            <div class="signoff-line"></div>
            <div class="signoff-name">Plant Operations Director</div>
            <div class="signoff-role">Authorization & Release Stamp</div>
        </div>
    </footer>
</div>

</body>
</html>
"""


def save_iso_certificate(report: "InspectionReport", output_dir: str = "outputs") -> Path:
    """Render and save the ISO certificate HTML to disk."""
    out_path = Path(output_dir) / f"{report.inspection_id}_certificate.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_content = render_iso_certificate_html(report)
    out_path.write_text(html_content, encoding="utf-8")
    return out_path
