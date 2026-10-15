"""
In-memory Knowledge Graph Engine and Interactive HTML/JSON Exporter for Hamsa.
Maintains nodes and relations with automatic deduplication, cross-linking, and standalone visualization.
"""

import json
import os
from typing import Any, Dict, List, Optional
from hamsa.core.models import EntityNode, RelationEdge, RelationType, TargetType


class KnowledgeGraph:
    """In-memory intelligence graph that links entities across multiple OSINT modules."""

    def __init__(self) -> None:
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: List[RelationEdge] = []
        self._edge_keys: set = set()

    def add_node(self, node: EntityNode) -> None:
        if node.id in self.nodes:
            existing = self.nodes[node.id]
            # Merge attributes
            existing.attributes.update(node.attributes)
            existing.confidence = max(existing.confidence, node.confidence)
        else:
            self.nodes[node.id] = node

    def add_edge(self, edge: RelationEdge) -> None:
        key = (edge.source_id, edge.target_id, edge.relation_type)
        if key not in self._edge_keys:
            self._edge_keys.add(key)
            self.edges.append(edge)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_entities": len(self.nodes),
                "total_relations": len(self.edges),
            },
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def export_json(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def export_csv(self, output_path: str) -> None:
        """Exports entities and relationship edges to a structured CSV file."""
        import csv

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Section 1: Entities
            writer.writerow(["# SECTION: ENTITIES"])
            writer.writerow(["Entity ID", "Type", "Label", "Value", "Source Plugin", "Confidence", "Attributes"])
            for node in self.nodes.values():
                n_type = node.type.value if isinstance(node.type, TargetType) else str(node.type)
                writer.writerow([
                    node.id,
                    n_type,
                    node.label,
                    node.value,
                    node.source_plugin,
                    f"{node.confidence * 100:.1f}%",
                    json.dumps(node.attributes, ensure_ascii=False),
                ])

            writer.writerow([])
            # Section 2: Relationships
            writer.writerow(["# SECTION: RELATIONSHIPS"])
            writer.writerow(["Source Entity", "Target Entity", "Relation Type", "Label", "Weight"])
            for edge in self.edges:
                r_type = edge.relation_type.value if isinstance(edge.relation_type, RelationType) else str(edge.relation_type)
                writer.writerow([edge.source_id, edge.target_id, r_type, edge.label, edge.weight])

    def export_html(self, output_path: str, title: str = "Hamsa OSINT Investigation Graph") -> None:
        """Exports an interactive, standalone HTML graph visualization using Vis.js CDN."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Color palette by entity type
        type_colors = {
            TargetType.EMAIL.value: "#3b82f6",     # Blue
            TargetType.USERNAME.value: "#10b981",  # Green
            TargetType.PHONE.value: "#f59e0b",     # Amber
            TargetType.BREACH.value: "#ef4444",    # Red
            TargetType.LOCATION.value: "#8b5cf6",  # Purple
            TargetType.DEVICE.value: "#ec4899",    # Pink
            TargetType.GENERIC.value: "#64748b",   # Slate
            TargetType.IMAGE.value: "#06b6d4",     # Cyan
        }

        vis_nodes = []
        for node in self.nodes.values():
            node_type = node.type.value if isinstance(node.type, TargetType) else str(node.type)
            color = type_colors.get(node_type, "#94a3b8")
            vis_nodes.append({
                "id": node.id,
                "label": node.label,
                "title": f"Type: {node_type}<br>Value: {node.value}<br>Plugin: {node.source_plugin}",
                "color": {"background": color, "border": "#ffffff", "highlight": {"background": "#ffffff", "border": color}},
                "font": {"color": "#ffffff", "face": "system-ui, sans-serif"},
                "shape": "dot",
                "size": 25 if "initial_target" in node.attributes else 18,
                "custom_data": node.to_dict(),
            })

        vis_edges = []
        for edge in self.edges:
            vis_edges.append({
                "from": edge.source_id,
                "to": edge.target_id,
                "label": edge.label,
                "arrows": "to",
                "color": {"color": "#475569", "highlight": "#38bdf8"},
                "font": {"color": "#94a3b8", "size": 11, "align": "middle"},
            })

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }}
    header {{
      background: #1e293b;
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #334155;
    }}
    header h1 {{ font-size: 1.15rem; font-weight: 600; color: #38bdf8; display: flex; align-items: center; gap: 8px; }}
    .stats-badge {{ font-size: 0.8rem; background: #334155; padding: 4px 10px; border-radius: 999px; }}
    #workspace {{ display: flex; flex: 1; position: relative; }}
    #network {{ flex: 1; height: 100%; }}
    #inspector {{
      width: 320px;
      background: #1e293b;
      border-left: 1px solid #334155;
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .legend {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: rgba(30, 41, 59, 0.85);
      backdrop-filter: blur(8px);
      padding: 12px 16px;
      border-radius: 8px;
      border: 1px solid #334155;
      font-size: 0.8rem;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
    pre {{ background: #0f172a; padding: 10px; border-radius: 6px; font-size: 0.75rem; overflow-x: auto; color: #a5f3fc; }}
  </style>
</head>
<body>
  <header>
    <h1>🕸️ {title}</h1>
    <div class="stats-badge">Entities: <b>{len(self.nodes)}</b> | Relations: <b>{len(self.edges)}</b></div>
  </header>
  <div id="workspace">
    <div id="network"></div>
    <div class="legend">
      <div style="font-weight:600; margin-bottom:4px; color:#94a3b8;">ENTITY TYPES</div>
      <div class="legend-item"><div class="legend-dot" style="background:#3b82f6;"></div> Email</div>
      <div class="legend-item"><div class="legend-dot" style="background:#10b981;"></div> Username / Account</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f59e0b;"></div> Phone / Carrier</div>
      <div class="legend-item"><div class="legend-dot" style="background:#ef4444;"></div> Data Breach</div>
      <div class="legend-item"><div class="legend-dot" style="background:#8b5cf6;"></div> Location / GPS</div>
      <div class="legend-item"><div class="legend-dot" style="background:#ec4899;"></div> Device / Camera</div>
    </div>
    <div id="inspector">
      <h3 style="color:#38bdf8;">Node Inspector</h3>
      <p style="font-size:0.85rem; color:#94a3b8;">Click on any node in the graph to view intelligence details.</p>
      <div id="node-details"></div>
    </div>
  </div>

  <script>
    const nodes = new vis.DataSet({json.dumps(vis_nodes)});
    const edges = new vis.DataSet({json.dumps(vis_edges)});
    const container = document.getElementById('network');
    const data = {{ nodes: nodes, edges: edges }};
    const options = {{
      nodes: {{ borderWidth: 2 }},
      edges: {{ smooth: {{ type: 'cubicBezier', forceDirection: 'horizontal' }} }},
      physics: {{
        barnesHut: {{ gravitationalConstant: -3500, centralGravity: 0.3, springLength: 120 }},
        stabilization: {{ iterations: 120 }}
      }},
      interaction: {{ hover: true, tooltipDelay: 200 }}
    }};
    const network = new vis.Network(container, data, options);

    network.on("click", function (params) {{
      if (params.nodes.length > 0) {{
        const nodeId = params.nodes[0];
        const nodeItem = nodes.get(nodeId);
        const detailsContainer = document.getElementById("node-details");
        detailsContainer.innerHTML = `
          <div style="margin-top:10px; display:flex; flex-direction:column; gap:8px;">
            <div><b style="color:#cbd5e1;">Label:</b> <span style="color:#f8fafc;">${{nodeItem.label}}</span></div>
            <div><b style="color:#cbd5e1;">Type:</b> <span style="color:#38bdf8;">${{nodeItem.custom_data.type}}</span></div>
            <div><b style="color:#cbd5e1;">Value:</b> <span style="word-break:break-all;">${{nodeItem.custom_data.value}}</span></div>
            <div><b style="color:#cbd5e1;">Plugin:</b> ${{nodeItem.custom_data.source_plugin}}</div>
            <div><b style="color:#cbd5e1;">Confidence:</b> ${{nodeItem.custom_data.confidence * 100}}%</div>
            <div style="margin-top:8px;"><b style="color:#cbd5e1;">Attributes:</b></div>
            <pre>${{JSON.stringify(nodeItem.custom_data.attributes, null, 2)}}</pre>
          </div>
        `;
      }}
    }});
  </script>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
