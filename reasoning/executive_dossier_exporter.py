"""
Executive Dossier & Multi-Format Forensic Exporter for AETHER.

Compiles complete investigation dossiers into publication-grade, self-contained HTML
reports with embedded STIX 2.1 bundles, MITRE matrix heatmaps, and print-ready PDF styling.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class ExecutiveDossierExporter:
    """Renders standalone HTML intelligence dossiers and STIX 2.1 bundles."""

    @staticmethod
    def generate_html_report(project: Dict[str, Any], stix_bundle: Optional[Dict[str, Any]] = None) -> str:
        name = project.get("name", "Target Investigation")
        seed = project.get("target_seed", "N/A")
        target_type = project.get("target_type", "UNKNOWN")
        briefing = project.get("context_briefing", "") or "Autonomous cognitive reconnaissance."
        created_at = project.get("created_at", datetime.now(timezone.utc).isoformat())
        entities_count = project.get("entities_count", 0)
        dossier_text = project.get("dossier", "") or "No formal narrative dossier synthesized yet."

        state = project.get("state") or {}
        entities = state.get("entities", {})
        relationships = state.get("relationships", [])

        stix_json = json.dumps(stix_bundle or {}, indent=2)

        # Build Entity Rows
        entity_rows_html = ""
        for eid, ent in list(entities.items())[:50]:
            ename = ent.get("name", eid)
            etype = ent.get("type", "UNKNOWN")
            conf = ent.get("confidence", 1.0)
            signals = ", ".join(ent.get("signals", [])[:3])
            entity_rows_html += f"""
            <tr>
                <td style="font-weight:600; color:#38bdf8;">{ename}</td>
                <td><span class="badge badge-type">{etype}</span></td>
                <td><span class="badge badge-conf">{int(conf * 100)}%</span></td>
                <td style="color:#94a3b8; font-size:12px;">{signals or 'Direct Evidence'}</td>
            </tr>
            """

        if not entity_rows_html:
            entity_rows_html = "<tr><td colspan='4' style='text-align:center; color:#64748b;'>No corroborating entities recorded.</td></tr>"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AETHER Intelligence Dossier: {name}</title>
<style>
  :root {{
    --bg-main: #0b0f19;
    --bg-card: #111827;
    --border: #1f2937;
    --accent: #38bdf8;
    --accent-glow: rgba(56, 189, 248, 0.15);
    --text: #f8fafc;
    --text-muted: #94a3b8;
    --danger: #ef4444;
    --success: #10b981;
  }}
  @media print {{
    body {{ background: #ffffff !important; color: #000000 !important; }}
    .no-print {{ display: none !important; }}
    .card {{ border: 1px solid #cccccc !important; background: #ffffff !important; }}
    table th, table td {{ border-color: #dddddd !important; color: #000000 !important; }}
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: var(--bg-main);
    color: var(--text);
    padding: 32px 20px;
    line-height: 1.6;
  }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid var(--border);
    padding-bottom: 24px;
    margin-bottom: 32px;
  }}
  .brand {{ display: flex; align-items: center; gap: 12px; }}
  .brand-logo {{
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, #38bdf8, #818cf8);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    color: #0b0f19;
    font-size: 20px;
  }}
  .brand h1 {{ font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }}
  .brand p {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }}
  .meta-pills {{ display: flex; gap: 8px; }}
  .badge {{
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .badge-type {{ background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
  .badge-conf {{ background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }}
  .card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
  }}
  .card-title {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 16px;
    color: var(--accent);
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
  }}
  .grid-meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
  .meta-item label {{ display: block; font-size: 11px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px; }}
  .meta-item span {{ font-size: 14px; font-weight: 600; word-break: break-all; }}
  .dossier-body {{
    background: #080c14;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 18px;
    font-family: "Courier New", Courier, monospace;
    font-size: 13px;
    white-space: pre-wrap;
    color: #cbd5e1;
  }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }}
  th {{ color: var(--text-muted); font-size: 11px; text-transform: uppercase; }}
  .btn-print {{
    background: var(--accent);
    color: #0b0f19;
    padding: 8px 18px;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    cursor: pointer;
    font-size: 13px;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="brand">
      <div class="brand-logo">Æ</div>
      <div>
        <h1>AETHER Intelligence Dossier</h1>
        <p>Autonomous Cognitive Cyber Reconnaissance & Threat Intel</p>
      </div>
    </div>
    <div class="no-print">
      <button class="btn-print" onclick="window.print()">Print / Export PDF</button>
    </div>
  </div>

  <div class="card">
    <div class="card-title">🎯 Investigation Target Parameters</div>
    <div class="grid-meta">
      <div class="meta-item">
        <label>Investigation Name</label>
        <span>{name}</span>
      </div>
      <div class="meta-item">
        <label>Target Seed</label>
        <span>{seed}</span>
      </div>
      <div class="meta-item">
        <label>Target Classification</label>
        <span><span class="badge badge-type">{target_type}</span></span>
      </div>
      <div class="meta-item">
        <label>Analysis Timestamp</label>
        <span>{created_at}</span>
      </div>
      <div class="meta-item">
        <label>Corroborated Entities</label>
        <span>{entities_count} nodes</span>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">📝 Executive Narrative & Strategic Briefing</div>
    <div class="dossier-body">{dossier_text}</div>
  </div>

  <div class="card">
    <div class="card-title">🌐 Corroborated Entity Knowledge Matrix</div>
    <table>
      <thead>
        <tr>
          <th>Entity / Indicator</th>
          <th>Type</th>
          <th>Confidence</th>
          <th>Evidence Signals</th>
        </tr>
      </thead>
      <tbody>
        {entity_rows_html}
      </tbody>
    </table>
  </div>

  <div class="card">
    <div class="card-title">🛡️ Standard STIX 2.1 Cyber Threat Bundle (JSON-LD)</div>
    <pre style="background:#080c14; padding:12px; border-radius:6px; font-size:11px; overflow-x:auto; color:#38bdf8;">{stix_json}</pre>
  </div>
</div>
<script type="application/ld+json">
{stix_json}
</script>
</body>
</html>
"""
        return html
