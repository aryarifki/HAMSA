"""
Advanced Reporting & Investigation Export Engine for Hamsa OSINT Framework.
Transforms raw knowledge graph data into executive summaries, chronological timeline analysis,
and structured digital evidence dossiers (Markdown, Standalone HTML, and JSON).
"""

from __future__ import annotations

import datetime
import html
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from hamsa.core.graph import KnowledgeGraph
from hamsa.core.models import EntityNode, RelationEdge, TargetType


class ReportGenerator:
    """Generates board-level and forensic investigative reports from an intelligence graph."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def generate_executive_summary(self, targets: List[Tuple[str, TargetType]]) -> str:
        """Synthesizes high-level executive findings and key risk indicators."""
        total_nodes = len(self.graph.nodes)
        total_edges = len(self.graph.edges)

        breaches = [n for n in self.graph.nodes.values() if n.type == TargetType.BREACH]
        accounts = [n for n in self.graph.nodes.values() if n.type == TargetType.USERNAME or "platform" in n.attributes]
        phones = [n for n in self.graph.nodes.values() if n.type == TargetType.PHONE]
        tags = [n for n in self.graph.nodes.values() if "source" in n.attributes and n.attributes["source"] in ("GetContact", "Truecaller")]

        target_str = ", ".join([f"{t[0]} ({t[1].value})" for t in targets])
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"**Investigative Subject(s):** {target_str}",
            f"**Execution Timestamp:** {timestamp}",
            f"**Correlated Intelligence Footprint:** {total_nodes} unique entities and {total_edges} cross-identity relational links discovered.",
        ]

        # Threat Exposure Assessment
        if breaches:
            lines.append(
                f"\n⚠️ **High Risk Exposure:** Target has been identified across **{len(breaches)} public data breach incident(s)** "
                f"or infostealer malware logs ({', '.join([b.label for b in breaches[:3]])}{'...' if len(breaches) > 3 else ''})."
            )
        else:
            lines.append("\n✓ **Threat Status:** No public breach exposure or infostealer malware logs identified.")

        # Digital Identity Breadth
        if accounts:
            platforms = list(dict.fromkeys([a.attributes.get("platform", a.label) for a in accounts]))
            lines.append(
                f"🌐 **Social & Platform Presence:** Confirmed active presence across **{len(platforms)} online service(s)** "
                f"({', '.join(platforms[:5])}{'...' if len(platforms) > 5 else ''})."
            )

        # Telecommunications & Caller ID
        if phones or tags:
            carriers = list(dict.fromkeys([p.attributes.get("carrier") for p in phones if p.attributes.get("carrier")]))
            tag_names = [t.attributes.get("tag", t.value) for t in tags[:4]]
            carrier_str = f" via {', '.join(carriers)}" if carriers else ""
            tag_str = f" | Crowd-Sourced Contact Tags: {', '.join(tag_names)}" if tag_names else ""
            lines.append(f"📞 **Telecommunication Intelligence:** Verified phone footprint{carrier_str}{tag_str}.")

        return "\n".join(lines)

    def generate_timeline(self) -> List[Dict[str, Any]]:
        """Extracts chronological timestamps across breaches, EXIF metadata, and discovery events."""
        events: List[Dict[str, Any]] = []

        for node in self.graph.nodes.values():
            attrs = node.attributes

            # 1. EXIF Photo Timestamp
            if "datetime_original" in attrs:
                events.append({
                    "timestamp": attrs["datetime_original"],
                    "category": "Physical / Device Footprint",
                    "event": f"Photo capture by {attrs.get('camera_model', 'Device')}",
                    "details": f"Coordinates: {attrs.get('latitude')}, {attrs.get('longitude')} ({attrs.get('osm_address', 'Unknown location')})",
                    "node_id": node.id,
                })

            # 2. Data Breach Incident Year/Date
            if node.type == TargetType.BREACH:
                b_date = attrs.get("breached_date") or attrs.get("date") or "Unknown Date"
                events.append({
                    "timestamp": str(b_date),
                    "category": "Security Incident",
                    "event": f"Data Breach: {node.label}",
                    "details": f"Compromised accounts in breach of {attrs.get('domain', 'domain')}",
                    "node_id": node.id,
                })

            # 3. Infostealer Compromise Date
            if "infected_path" in attrs:
                events.append({
                    "timestamp": attrs.get("date", "Recent Incident"),
                    "category": "Malware Infection",
                    "event": f"Infostealer Infection Log ({attrs.get('malware_family', 'Stealer')})",
                    "details": f"Computer infected: {attrs.get('infected_path')} | IP: {attrs.get('ip', 'N/A')}",
                    "node_id": node.id,
                })

        # Sort timeline chronologically
        events.sort(key=lambda x: str(x["timestamp"]), reverse=True)
        return events

    def generate_markdown(self, targets: List[Tuple[str, TargetType]], title: str = "HAMSA OSINT Intelligence Report") -> str:
        """Generates comprehensive markdown report."""
        summary = self.generate_executive_summary(targets)
        timeline = self.generate_timeline()

        md_lines = [
            f"# 🪬 {title}",
            "",
            "## 1. Executive Summary",
            summary,
            "",
            "## 2. Chronological Activity Timeline",
        ]

        if timeline:
            md_lines.append("| Date / Timestamp | Category | Incident / Activity | Technical Details |")
            md_lines.append("| :--- | :--- | :--- | :--- |")
            for t in timeline:
                md_lines.append(f"| {t['timestamp']} | **{t['category']}** | {t['event']} | {t['details']} |")
        else:
            md_lines.append("*No chronological timestamps were extracted from the current investigation entities.*")

        md_lines.extend([
            "",
            "## 3. Discovered Entity Registry",
            "| Entity ID | Type | Label / Identifier | Confidence | Source Plugin | Key Attributes |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for node in self.graph.nodes.values():
            key_attr = ", ".join([f"{k}: {v}" for k, v in list(node.attributes.items())[:3] if isinstance(v, (str, int, float))])
            md_lines.append(
                f"| `{node.id}` | {node.type.value} | **{node.label}** | {int(node.confidence * 100)}% | {node.source_plugin or 'Core'} | {key_attr} |"
            )

        md_lines.extend([
            "",
            "## 4. Entity Correlation Edges",
            "| Source Entity | Relation Type | Target Entity | Relationship Label |",
            "| :--- | :--- | :--- | :--- |",
        ])

        for edge in self.graph.edges:
            md_lines.append(f"| `{edge.source_id}` | `{edge.relation_type.value}` | `{edge.target_id}` | {edge.label} |")

        md_lines.extend([
            "",
            "---",
            f"*Generated autonomously by HAMSA OSINT Intelligence Framework on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        ])

        return "\n".join(md_lines)

    def generate_html(self, targets: List[Tuple[str, TargetType]], title: str = "HAMSA OSINT Intelligence Dossier") -> str:
        """Generates print-ready standalone HTML report with Material Design 3 aesthetic."""
        summary_md = self.generate_executive_summary(targets)
        summary_html = "<br/>".join([html.escape(line) for line in summary_md.split("\n") if line.strip()])
        summary_html = summary_html.replace("**", "<b>").replace("⚠️", "<span style='color:#f43f5e;'>⚠️</span>")

        timeline = self.generate_timeline()

        timeline_rows = ""
        for t in timeline:
            timeline_rows += f"""
            <tr>
              <td class="font-mono">{html.escape(str(t['timestamp']))}</td>
              <td><b>{html.escape(t['category'])}</b></td>
              <td>{html.escape(t['event'])}</td>
              <td class="text-muted">{html.escape(t['details'])}</td>
            </tr>
            """

        entity_rows = ""
        for n in self.graph.nodes.values():
            attr_summary = ", ".join([f"{k}: {v}" for k, v in list(n.attributes.items())[:2] if isinstance(v, (str, int, float))])
            conf_badge = f"<span class='badge' style='background:rgba(16,185,129,0.15); color:#10b981;'>{int(n.confidence * 100)}%</span>"
            entity_rows += f"""
            <tr>
              <td class="font-mono">{html.escape(n.id)}</td>
              <td><span class="badge">{html.escape(n.type.value)}</span></td>
              <td><b>{html.escape(n.label)}</b></td>
              <td>{conf_badge}</td>
              <td class="text-muted">{html.escape(n.source_plugin or 'Core')}</td>
              <td class="font-mono text-muted">{html.escape(attr_summary)}</td>
            </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #141210;
      --card: #211D1A;
      --border: #52443C;
      --text: #EBE0D9;
      --text-muted: #9F8D83;
      --accent: #FFB879;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 40px 24px;
    }}
    .container {{ max-width: 1000px; margin: 0 auto; }}
    header {{ border-bottom: 2px solid var(--accent); padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; }}
    h1 {{ font-size: 2rem; color: var(--accent); letter-spacing: -0.02em; }}
    h2 {{ font-size: 1.25rem; margin: 30px 0 15px 0; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase; background: rgba(255,184,121,0.15); color: var(--accent); border: 1px solid rgba(255,184,121,0.3); }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.85rem; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
    th {{ background: rgba(255,255,255,0.03); color: var(--accent); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
    tr:hover {{ background: rgba(255,255,255,0.02); }}
    .font-mono {{ font-family: ui-monospace, Menlo, Monaco, Consolas, monospace; font-size: 0.8rem; }}
    .text-muted {{ color: var(--text-muted); }}
    @media print {{
      body {{ background: #ffffff !important; color: #1a1a1a !important; }}
      .card {{ border: 1px solid #ddd !important; background: #fafafa !important; }}
      th, td {{ border-bottom: 1px solid #ddd !important; color: #1a1a1a !important; }}
      h1, h2 {{ color: #8C5000 !important; }}
      .badge {{ border: 1px solid #ccc !important; color: #333 !important; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <div class="badge" style="margin-bottom: 8px;">HAMSA OSINT INTELLIGENCE SUITE</div>
        <h1>{html.escape(title)}</h1>
      </div>
      <div style="text-align: right; font-size: 0.8rem; color: var(--text-muted);">
        Confidential Forensic Report<br/>
        Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
      </div>
    </header>

    <h2>1. Executive Summary & Threat Profile</h2>
    <div class="card">
      <div style="font-size: 0.95rem;">{summary_html}</div>
    </div>

    <h2>2. Chronological Activity Timeline</h2>
    <div class="card">
      {"<table><thead><tr><th>Timestamp</th><th>Category</th><th>Event</th><th>Technical Details</th></tr></thead><tbody>" + timeline_rows + "</tbody></table>" if timeline else "<p class='text-muted'>No chronological timestamps extracted.</p>"}
    </div>

    <h2>3. Correlated Entity Registry ({len(self.graph.nodes)} Total)</h2>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Entity ID</th>
            <th>Type</th>
            <th>Label</th>
            <th>Confidence</th>
            <th>Source</th>
            <th>Key Attributes</th>
          </tr>
        </thead>
        <tbody>
          {entity_rows}
        </tbody>
      </table>
    </div>

    <footer style="margin-top: 40px; text-align: center; font-size: 0.75rem; color: var(--text-muted); border-top: 1px solid var(--border); padding-top: 15px;">
      HAMSA OSINT Intelligence Framework • Autonomous Correlation & Knowledge Graph Engine
    </footer>
  </div>
</body>
</html>
"""

    def export(self, filepath: str, targets: List[Tuple[str, TargetType]], title: Optional[str] = None) -> str:
        """Exports report to markdown or HTML based on file extension."""
        title = title or "HAMSA OSINT Intelligence Report"
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        if filepath.endswith(".html") or filepath.endswith(".htm"):
            content = self.generate_html(targets, title)
        else:
            content = self.generate_markdown(targets, title)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath
