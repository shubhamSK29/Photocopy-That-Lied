"""Reviewer report generation (JSON, self-contained HTML, and PDF)."""
from __future__ import annotations

import base64
import json
from html import escape
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

from backend import config
from backend.storage import artifacts, database

router = APIRouter(prefix="/api", tags=["reports"])


def _row(label: str, value) -> str:
    return f"<tr><th>{escape(str(label))}</th><td>{escape(str(value))}</td></tr>"


def _image_tag(analysis_id: str, name: str, caption: str) -> str:
    try:
        path = artifacts.resolve_artifact(analysis_id, name)
    except (ValueError, FileNotFoundError):
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        f'<figure><img src="data:image/png;base64,{encoded}" alt="{escape(caption)}"/>'
        f"<figcaption>{escape(caption)}</figcaption></figure>"
    )


def render_html(record: dict) -> str:
    image = record["image"]
    detectors = record["detectors"]
    explanation = record["explanation"]
    coverage = record["coverage"]

    def _score(det: dict) -> str:
        return "n/a" if det.get("score") is None else f"{det['score']:.2f}"

    detector_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{escape(det['status'])}</td>"
        f"<td>{_score(det)}</td>"
        f"<td>{escape(det['explanation'])}</td></tr>"
        for name, det in detectors.items()
    )
    summary_rows = "".join(
        f"<tr><td>{escape(r['detector'])}</td><td>{escape(r['status'])}</td>"
        f"<td>{escape(r['strength'])}</td></tr>"
        for r in explanation["summary_rows"]
    )
    warnings = "".join(f"<li>{escape(w)}</li>" for w in record["warnings"])
    limitations = "".join(f"<li>{escape(l)}</li>" for l in record["limitations"])

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Forensic screening report {escape(record['analysis_id'])}</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 32px; color: #111; }}
 h1 {{ letter-spacing: .04em; }}
 table {{ border-collapse: collapse; margin: 12px 0 24px; width: 100%; }}
 th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; vertical-align: top; font-size: 14px; }}
 th {{ background: #f4f4f5; width: 220px; }}
 .scores {{ display: flex; gap: 24px; margin: 16px 0; }}
 .card {{ border: 1px solid #ccc; border-radius: 8px; padding: 16px 24px; }}
 .card .v {{ font-size: 32px; font-weight: 700; }}
 figure {{ margin: 0 0 16px; }} img {{ max-width: 420px; border: 1px solid #ddd; }}
 .figs {{ display: flex; gap: 16px; flex-wrap: wrap; }}
 .disclaimer {{ border-left: 4px solid #b45309; background: #fffbeb; padding: 12px 16px; }}
 pre {{ white-space: pre-wrap; background: #fafafa; border: 1px solid #eee; padding: 12px; font-size: 13px; }}
</style></head><body>
<h1>PHOTOCOPY THAT LIED</h1>
<p><strong>AI-assisted image forensics for crop-insurance review</strong></p>
<div class="disclaimer">{escape(config.DISCLAIMER)}</div>

<h2>Case information</h2>
<table>
 {_row('Analysis ID', record['analysis_id'])}
 {_row('Analysis timestamp (UTC)', record['created_at'])}
 {_row('Processing time (ms)', record['duration_ms'])}
</table>

<h2>Image information</h2>
<table>
 {_row('Filename', image['filename'])}
 {_row('SHA-256', image['sha256'])}
 {_row('Format', image['format'])}
 {_row('Dimensions', f"{image['width']} x {image['height']}")}
 {_row('File size (bytes)', image['file_size'])}
 {_row('Analysis resolution', f"{image['analysis_width']} x {image['analysis_height']}")}
</table>

<h2>Result</h2>
<div class="scores">
 <div class="card"><div>Manipulation evidence</div><div class="v">{record['manipulation_evidence']} / 100</div></div>
 <div class="card"><div>Data coverage</div><div class="v">{record['data_coverage']} / 100</div></div>
 <div class="card"><div>Review category</div><div class="v" style="font-size:20px">{escape(record['risk_band'])}</div></div>
</div>

<h2>Evidence summary</h2>
<table><tr><th>Signal</th><th>Status</th><th>Strength</th></tr>{summary_rows}</table>

<h2>Detector results</h2>
<table><tr><th>Detector</th><th>Status</th><th>Score</th><th>Explanation</th></tr>{detector_rows}</table>

<h2>Spatial agreement</h2>
<table>
 {_row('Agreement level', record['spatial_agreement']['agreement_level'])}
 {_row('Max IoU', record['spatial_agreement']['max_iou'])}
 {_row('Max Dice', record['spatial_agreement']['max_dice'])}
</table>

<h2>Metadata status</h2>
<table>
 {_row('EXIF status', record['metadata']['status'])}
 {_row('Camera make', record['metadata'].get('camera_make') or 'unavailable')}
 {_row('Camera model', record['metadata'].get('camera_model') or 'unavailable')}
 {_row('Software', record['metadata'].get('software') or 'unavailable')}
</table>

<h2>Timestamp integrity</h2>
<table>
 {_row('EXIF timestamp', record['timestamp_integrity'].get('exif_timestamp') or 'unavailable')}
 {_row('Visible timestamp', record['timestamp_integrity'].get('visible_timestamp_text') or 'not detected')}
 {_row('Verification', record['timestamp_integrity'].get('verification'))}
</table>
<p>{escape(record['timestamp_integrity'].get('summary', ''))}</p>

<h2>Data coverage detail</h2>
<table>{''.join(_row(k, v) for k, v in coverage['components'].items())}</table>

<h2>Heatmap</h2>
<div class="figs">
 {_image_tag(record['analysis_id'], 'analysis.png', 'Normalised analysis image')}
 {_image_tag(record['analysis_id'], 'heatmap.png', 'Combined forensic heatmap')}
 {_image_tag(record['analysis_id'], 'overlay.png', 'Overlay with highlighted regions')}
</div>
<p><em>Approximate forensic signal - not pixel-perfect proof of manipulation.</em></p>

<h2>Explanation</h2>
<pre>{escape(explanation['narrative'])}</pre>

<h2>Warnings</h2><ul>{warnings}</ul>
<h2>System limitations</h2><ul>{limitations}</ul>

<h2>Provenance</h2>
<table>{''.join(_row(k, v) for k, v in record['versions'].items())}
 {_row('Fusion mode', record['fusion']['mode'])}
</table>
</body></html>"""


def _load(analysis_id: str) -> dict:
    record = database.get_analysis(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Unknown analysis id"})
    return record


def render_pdf(record: dict) -> bytes:
    """Convert HTML report to PDF using weasyprint."""
    try:
        from weasyprint import HTML
        html_content = render_html(record)
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except ImportError:
        # Fallback: if weasyprint is not available, return error
        raise ValueError("PDF export requires weasyprint package")
    except Exception as e:
        raise ValueError(f"PDF generation failed: {str(e)}")


@router.get("/report/{analysis_id}")
async def get_report(analysis_id: str, format: str = "json"):
    record = _load(analysis_id)
    if format == "html":
        html = render_html(record)
        path = Path(config.REPORT_DIR) / f"{analysis_id}.html"
        path.write_text(html, encoding="utf-8")
        return HTMLResponse(html)
    elif format == "pdf":
        try:
            pdf_bytes = render_pdf(record)
            path = Path(config.REPORT_DIR) / f"{analysis_id}.pdf"
            path.write_bytes(pdf_bytes)
            return FileResponse(
                path,
                media_type="application/pdf",
                filename=f"forensic_report_{analysis_id}.pdf"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=501,
                detail={"code": "pdf_not_available", "message": str(e)}
            )
    path = Path(config.REPORT_DIR) / f"{analysis_id}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return JSONResponse(record)
