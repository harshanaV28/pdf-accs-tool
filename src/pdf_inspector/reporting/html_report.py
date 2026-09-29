"""
HTML Report Generator
Generates self-contained, publication-grade interactive HTML reports for audit results.
"""

import html
from ..core.models import AuditReport, CheckStatus


class HTMLReportGenerator:
    """Generates modern, standalone HTML reports for PDF accessibility audits."""

    @staticmethod
    def generate(report: AuditReport, output_filepath: str):
        doc = report.document_info
        score = report.compliance_score

        score_color = "#10b981" if score >= 90 else ("#f59e0b" if score >= 70 else "#ef4444")

        # Prepare finding rows
        rows_html = []
        for r in report.results:
            status_cls = {
                CheckStatus.PASS: "badge-pass",
                CheckStatus.FAIL: "badge-fail",
                CheckStatus.WARNING: "badge-warn",
                CheckStatus.MANUAL_REVIEW: "badge-manual",
                CheckStatus.ERROR: "badge-error",
            }.get(r.status, "badge-info")

            rows_html.append(f"""
            <tr class="finding-row" data-status="{r.status.value}" data-standard="{r.standard}">
                <td><span class="badge {status_cls}">{html.escape(r.status.value)}</span></td>
                <td><code>{html.escape(r.check_id)}</code></td>
                <td><strong>{html.escape(r.name)}</strong><br><small class="text-muted">{html.escape(r.category)}</small></td>
                <td>{html.escape(r.standard)}</td>
                <td>{r.page if r.page else '<span class="text-muted">Doc</span>'}</td>
                <td>
                    <div class="msg-box">{html.escape(r.message)}</div>
                    {f'<div class="evidence-box"><strong>Evidence:</strong> <code>{html.escape(r.evidence)}</code></div>' if r.evidence else ''}
                    {f'<div class="remediation-box"><strong>Remediation:</strong> {html.escape(r.remediation)}</div>' if r.remediation else ''}
                </td>
            </tr>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Accessibility Audit Report - {html.escape(doc.get('filename', 'PDF'))}</title>
    <style>
        :root {{
            --bg: #f8fafc;
            --surface: #ffffff;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --primary: #2563eb;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #0284c7;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 2rem;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: var(--surface);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            border: 1px solid var(--border);
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
            margin-bottom: 1rem;
        }}
        h1 {{ margin: 0; font-size: 1.75rem; color: #1e293b; }}
        .score-circle {{
            width: 90px;
            height: 90px;
            border-radius: 50%;
            border: 6px solid {score_color};
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1.4rem;
            color: {score_color};
        }}
        .score-label {{ font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        .meta-item {{ font-size: 0.9rem; }}
        .meta-item strong {{ color: var(--text-muted); display: block; font-size: 0.8rem; text-transform: uppercase; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--surface);
            padding: 1.25rem;
            border-radius: 10px;
            border: 1px solid var(--border);
            text-align: center;
        }}
        .stat-num {{ font-size: 2rem; font-weight: 700; margin: 0.25rem 0; }}
        .stat-pass {{ color: var(--success); }}
        .stat-warn {{ color: var(--warning); }}
        .stat-fail {{ color: var(--danger); }}
        .stat-manual {{ color: var(--info); }}
        .table-card {{
            background: var(--surface);
            border-radius: 12px;
            border: 1px solid var(--border);
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }}
        th {{
            background: #f1f5f9;
            padding: 0.85rem 1rem;
            font-weight: 600;
            color: #475569;
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
        }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-pass {{ background: #dcfce7; color: #166534; }}
        .badge-fail {{ background: #fee2e2; color: #991b1b; }}
        .badge-warn {{ background: #fef3c7; color: #92400e; }}
        .badge-manual {{ background: #e0f2fe; color: #075985; }}
        .badge-error {{ background: #f3e8ff; color: #6b21a8; }}
        .msg-box {{ font-weight: 500; margin-bottom: 0.35rem; }}
        .evidence-box {{
            background: #f8fafc;
            padding: 0.4rem 0.6rem;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-bottom: 0.35rem;
            border-left: 3px solid #cbd5e1;
        }}
        .remediation-box {{
            background: #f0fdf4;
            padding: 0.4rem 0.6rem;
            border-radius: 4px;
            font-size: 0.8rem;
            color: #166534;
            border-left: 3px solid #86efac;
        }}
        .filter-bar {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            align-items: center;
        }}
        .filter-btn {{
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: var(--surface);
            cursor: pointer;
            font-size: 0.85rem;
        }}
        .filter-btn.active {{
            background: var(--primary);
            color: #ffffff;
            border-color: var(--primary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-top">
                <div>
                    <h1>PDF Accessibility Audit Report</h1>
                    <div style="color: var(--text-muted); font-size: 0.95rem; margin-top: 0.25rem;">
                        Generated by <strong>PDF Accessibility Inspector</strong> on {report.timestamp}
                    </div>
                </div>
                <div class="score-circle">
                    {score}%
                    <span class="score-label">Score</span>
                </div>
            </div>
            <div class="meta-grid">
                <div class="meta-item"><strong>Document File</strong>{html.escape(doc.get('filename', ''))}</div>
                <div class="meta-item"><strong>Document Title</strong>{html.escape(doc.get('title', 'Untitled'))}</div>
                <div class="meta-item"><strong>Pages / Size</strong>{doc.get('page_count', 0)} pages ({round(doc.get('filesize', 0)/1024, 1)} KB)</div>
                <div class="meta-item"><strong>PDF Version</strong>{doc.get('pdf_version', '1.7')}</div>
                <div class="meta-item"><strong>Language</strong>{html.escape(doc.get('language', 'Not specified'))}</div>
                <div class="meta-item"><strong>Tagged PDF</strong>{'Yes' if doc.get('is_tagged') else '<span style="color:var(--danger)">No</span>'}</div>
                <div class="meta-item"><strong>PDF/UA Declared</strong>{'Yes' if doc.get('pdfua_declared') else 'No'}</div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-num stat-pass">{report.total_passed}</div>
                <div class="stat-label">Passed Checks</div>
            </div>
            <div class="stat-card">
                <div class="stat-num stat-warn">{report.total_warned}</div>
                <div class="stat-label">Warnings</div>
            </div>
            <div class="stat-card">
                <div class="stat-num stat-fail">{report.total_failed}</div>
                <div class="stat-label">Failed Issues</div>
            </div>
            <div class="stat-card">
                <div class="stat-num stat-manual">{report.total_manual}</div>
                <div class="stat-label">Manual Review</div>
            </div>
        </div>

        <div class="table-card">
            <div style="padding: 1rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0;">Audit Findings Details</h3>
                <div class="filter-bar">
                    <button class="filter-btn active" onclick="filterFindings('ALL')">All ({len(report.results)})</button>
                    <button class="filter-btn" onclick="filterFindings('FAIL')">Failures ({report.total_failed})</button>
                    <button class="filter-btn" onclick="filterFindings('WARNING')">Warnings ({report.total_warned})</button>
                    <button class="filter-btn" onclick="filterFindings('PASS')">Passed ({report.total_passed})</button>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 100px;">Status</th>
                        <th style="width: 130px;">Check ID</th>
                        <th>Checkpoint / Category</th>
                        <th style="width: 90px;">Standard</th>
                        <th style="width: 70px;">Page</th>
                        <th>Evidence & Remediation</th>
                    </tr>
                </thead>
                <tbody id="findingsBody">
                    {''.join(rows_html)}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function filterFindings(status) {{
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            const rows = document.querySelectorAll('.finding-row');
            rows.forEach(row => {{
                if (status === 'ALL' || row.getAttribute('data-status') === status) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
