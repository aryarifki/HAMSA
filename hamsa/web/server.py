"""
Embedded Web Dashboard & REST API Server for Hamsa OSINT Framework.
Provides a modern web UI and API bridge without requiring heavy external dependencies.
"""

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from hamsa.core.models import TargetType
from hamsa.core.orchestrator import Orchestrator
from hamsa.core.sources import SourceManager
from hamsa.utils.formatters import log_error, log_info, log_success

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hamsa OSINT Dashboard</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #131b2e;
      --card-border: #1e293b;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.2);
      --text: #f8fafc;
      --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }
    header {
      background: #0f172a;
      border-bottom: 1px solid var(--card-border);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 10;
    }
    .brand { display: flex; align-items: center; gap: 10px; font-size: 1.25rem; font-weight: 700; color: var(--accent); }
    .nav-actions { display: flex; gap: 12px; align-items: center; }
    button.btn-action {
      background: #1e293b;
      border: 1px solid #334155;
      color: var(--text);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 0.85rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    button.btn-action:hover { background: #334155; }
    button.btn-primary {
      background: #0284c7;
      border: 1px solid #38bdf8;
      color: #ffffff;
      padding: 8px 18px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 0 15px var(--accent-glow);
    }
    button.btn-primary:hover { background: #0369a1; }
    #main-layout { display: flex; flex: 1; position: relative; overflow: hidden; }
    #sidebar {
      width: 360px;
      background: var(--card-bg);
      border-right: 1px solid var(--card-border);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      overflow-y: auto;
      z-index: 5;
    }
    .form-group { display: flex; flex-direction: column; gap: 6px; }
    .form-group label { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
    .form-group input, .form-group select {
      background: #0b1120;
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 6px;
      font-size: 0.9rem;
      outline: none;
    }
    .form-group input:focus { border-color: var(--accent); box-shadow: 0 0 8px var(--accent-glow); }
    #canvas-area { flex: 1; position: relative; height: 100%; }
    #network { width: 100%; height: 100%; }
    #right-panel {
      width: 340px;
      background: var(--card-bg);
      border-left: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      z-index: 5;
    }
    .panel-tab-header {
      display: flex;
      border-bottom: 1px solid var(--card-border);
      background: #0f172a;
    }
    .panel-tab {
      flex: 1;
      padding: 12px;
      text-align: center;
      font-size: 0.85rem;
      color: var(--text-muted);
      cursor: pointer;
      font-weight: 600;
    }
    .panel-tab.active { color: var(--accent); border-bottom: 2px solid var(--accent); background: var(--card-bg); }
    .tab-content { padding: 16px; flex: 1; overflow-y: auto; display: none; }
    .tab-content.active { display: block; }
    #log-stream { font-family: monospace; font-size: 0.78rem; display: flex; flex-direction: column; gap: 6px; }
    .log-line { color: #a5f3fc; line-height: 1.4; word-break: break-all; }
    .legend {
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: rgba(19, 27, 46, 0.85);
      backdrop-filter: blur(8px);
      padding: 12px 16px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
      font-size: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .legend-item { display: flex; align-items: center; gap: 8px; }
    .legend-dot { width: 10px; height: 10px; border-radius: 50%; }
    pre { background: #0b1120; padding: 10px; border-radius: 6px; font-size: 0.75rem; overflow-x: auto; color: #a5f3fc; }
  </style>
</head>
<body>
  <header>
    <div class="brand">🪬 HAMSA <span style="font-size:0.75rem; font-weight:400; color:var(--text-muted);">OSINT & Correlation Web Suite</span></div>
    <div class="nav-actions">
      <button class="btn-action" onclick="updateSources()">🔄 Update 690+ Sources</button>
      <button class="btn-action" onclick="exportJSON()">📥 Export JSON</button>
      <button class="btn-action" onclick="resetGraph()">🗑️ Reset Graph</button>
    </div>
  </header>
  <div id="main-layout">
    <div id="sidebar">
      <h3 style="font-size: 1rem; color: var(--accent); margin-bottom: 4px;">🎯 Investigation Setup</h3>
      <div class="form-group">
        <label>Username Target</label>
        <input type="text" id="target-username" placeholder="e.g. torvalds" />
      </div>
      <div class="form-group">
        <label>Email Address</label>
        <input type="email" id="target-email" placeholder="e.g. target@example.com" />
      </div>
      <div class="form-group">
        <label>Phone Number</label>
        <input type="text" id="target-phone" placeholder="e.g. +628123456789" />
      </div>
      <div class="form-group">
        <label>Recursion Depth (Multi-Round)</label>
        <select id="target-depth">
          <option value="1">Depth 1 (Direct Scan Only)</option>
          <option value="2" selected>Depth 2 (Auto-Scan Discovered Identities)</option>
          <option value="3">Depth 3 (Deep Knowledge Crawl)</option>
        </select>
      </div>
      <button class="btn-primary" id="btn-start" onclick="startScan()" style="margin-top: 10px;">⚡ Launch Investigation</button>
      
      <div style="margin-top: 10px; font-size: 0.8rem; color: var(--text-muted); line-height: 1.5;">
        <b>💡 Tip:</b> The engine runs multi-threaded async tasks across breach databases, social networks, and recursive name-dork resolvers.
      </div>
    </div>

    <div id="canvas-area">
      <div id="network"></div>
      <div class="legend">
        <div style="font-weight:600; margin-bottom:4px; color:#94a3b8;">ENTITY TYPES</div>
        <div class="legend-item"><div class="legend-dot" style="background:#3b82f6;"></div> Email</div>
        <div class="legend-item"><div class="legend-dot" style="background:#10b981;"></div> Username / Account</div>
        <div class="legend-item"><div class="legend-dot" style="background:#f59e0b;"></div> Phone / Carrier</div>
        <div class="legend-item"><div class="legend-dot" style="background:#ef4444;"></div> Data Breach</div>
        <div class="legend-item"><div class="legend-dot" style="background:#8b5cf6;"></div> Location / GPS</div>
        <div class="legend-item"><div class="legend-dot" style="background:#ec4899;"></div> Device / Camera</div>
        <div class="legend-item"><div class="legend-dot" style="background:#06b6d4;"></div> Knowledge / Wikipedia</div>
      </div>
    </div>

    <div id="right-panel">
      <div class="panel-tab-header">
        <div class="panel-tab active" onclick="switchTab('inspector')">Inspector</div>
        <div class="panel-tab" onclick="switchTab('logs')">Live Logs</div>
      </div>
      <div id="tab-inspector" class="tab-content active">
        <h4 style="color:var(--accent); margin-bottom:8px;">Entity Details</h4>
        <div id="node-inspector-content" style="color:var(--text-muted); font-size:0.85rem;">
          Click on any node in the graph to inspect discovered intelligence attributes.
        </div>
      </div>
      <div id="tab-logs" class="tab-content">
        <div id="log-stream">
          <div class="log-line">[SYSTEM] Ready. Enter target parameters and launch investigation.</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    let network = null;
    let currentGraphData = { nodes: [], edges: [] };
    const visNodes = new vis.DataSet([]);
    const visEdges = new vis.DataSet([]);

    function initNetwork() {
      const container = document.getElementById('network');
      const data = { nodes: visNodes, edges: visEdges };
      const options = {
        nodes: { borderWidth: 2 },
        edges: { smooth: { type: 'cubicBezier', forceDirection: 'horizontal' } },
        physics: {
          barnesHut: { gravitationalConstant: -3500, centralGravity: 0.3, springLength: 120 },
          stabilization: { iterations: 100 }
        },
        interaction: { hover: true, tooltipDelay: 200 }
      };
      network = new vis.Network(container, data, options);

      network.on("click", function (params) {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          const nodeItem = visNodes.get(nodeId);
          renderInspector(nodeItem.custom_data);
        }
      });
      loadExistingGraph();
    }

    function switchTab(tab) {
      document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      if (tab === 'inspector') {
        document.querySelectorAll('.panel-tab')[0].classList.add('active');
        document.getElementById('tab-inspector').classList.add('active');
      } else {
        document.querySelectorAll('.panel-tab')[1].classList.add('active');
        document.getElementById('tab-logs').classList.add('active');
      }
    }

    function renderInspector(data) {
      switchTab('inspector');
      const c = document.getElementById('node-inspector-content');
      c.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:8px;">
          <div><b style="color:#cbd5e1;">Label:</b> <span style="color:#f8fafc;">${data.label}</span></div>
          <div><b style="color:#cbd5e1;">Type:</b> <span style="color:var(--accent);">${data.type}</span></div>
          <div><b style="color:#cbd5e1;">Value:</b> <span style="word-break:break-all;">${data.value}</span></div>
          <div><b style="color:#cbd5e1;">Source:</b> ${data.source_plugin}</div>
          <div><b style="color:#cbd5e1;">Confidence:</b> ${data.confidence * 100}%</div>
          <div style="margin-top:6px;"><b style="color:#cbd5e1;">Attributes:</b></div>
          <pre>${JSON.stringify(data.attributes, null, 2)}</pre>
        </div>
      `;
    }

    function addLog(msg) {
      const stream = document.getElementById('log-stream');
      const line = document.createElement('div');
      line.className = 'log-line';
      line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
      stream.appendChild(line);
      stream.scrollTop = stream.scrollHeight;
    }

    async function startScan() {
      const u = document.getElementById('target-username').value.trim();
      const e = document.getElementById('target-email').value.trim();
      const p = document.getElementById('target-phone').value.trim();
      const d = parseInt(document.getElementById('target-depth').value, 10);

      if (!u && !e && !p) {
        alert("Please enter at least one target (Username, Email, or Phone).");
        return;
      }

      const btn = document.getElementById('btn-start');
      btn.disabled = true;
      btn.textContent = "⏳ Investigating...";
      addLog(`Initiating multi-target scan (Depth: ${d})...`);
      switchTab('logs');

      try {
        const resp = await fetch('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: u, email: e, phone: p, depth: d })
        });
        const res = await resp.json();
        btn.disabled = false;
        btn.textContent = "⚡ Launch Investigation";

        if (res.error) {
          addLog(`Error: ${res.error}`);
          return;
        }

        addLog(`Scan complete! Discovered ${res.nodes.length} entities and ${res.edges.length} relations.`);
        renderGraphData(res);
      } catch (err) {
        btn.disabled = false;
        btn.textContent = "⚡ Launch Investigation";
        addLog(`Investigation request failed: ${err}`);
      }
    }

    function renderGraphData(res) {
      if (!res || !res.nodes) return;
      currentGraphData = res;
      visNodes.clear();
      visEdges.clear();

      const typeColors = {
        email: "#3b82f6", username: "#10b981", phone: "#f59e0b",
        breach: "#ef4444", location: "#8b5cf6", device: "#ec4899",
        generic: "#06b6d4", image: "#06b6d4"
      };

      res.nodes.forEach(n => {
        const color = typeColors[n.type] || "#94a3b8";
        visNodes.add({
          id: n.id,
          label: n.label,
          color: { background: color, border: "#ffffff" },
          font: { color: "#ffffff" },
          shape: "dot",
          size: n.attributes && n.attributes.initial_target ? 24 : 16,
          custom_data: n
        });
      });

      res.edges.forEach(e => {
        visEdges.add({
          from: e.source,
          to: e.target,
          label: e.label,
          arrows: "to",
          color: { color: "#475569" },
          font: { color: "#94a3b8", size: 10 }
        });
      });

      network.fit();
    }

    async function loadExistingGraph() {
      try {
        const resp = await fetch('/api/graph');
        if (resp.ok) {
          const res = await resp.json();
          if (res && res.nodes && res.nodes.length > 0) {
            renderGraphData(res);
            addLog(`Restored active session graph (${res.nodes.length} entities, ${res.edges.length} relations).`);
          }
        }
      } catch (e) {}
    }

    async function resetGraph() {
      if (!confirm("Are you sure you want to reset the current investigation graph?")) return;
      try {
        const resp = await fetch('/api/reset', { method: 'POST' });
        if (resp.ok) {
          visNodes.clear();
          visEdges.clear();
          currentGraphData = { nodes: [], edges: [] };
          addLog("Investigation graph reset successfully.");
        }
      } catch (err) {
        alert("Failed to reset graph: " + err);
      }
    }

    async function updateSources() {
      addLog("Fetching 690+ WhatsMyName upstream sources...");
      const res = await fetch('/api/update-sources', { method: 'POST' });
      const data = await res.json();
      addLog(`Updated: ${data.total_sites} site definitions cached!`);
      alert(`Successfully synchronized ${data.total_sites} website definitions!`);
    }

    function exportJSON() {
      if (!currentGraphData || !currentGraphData.nodes || currentGraphData.nodes.length === 0) {
        alert("No intelligence data to export. Run a scan first!");
        return;
      }
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentGraphData, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", "hamsa_intelligence_export.json");
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    }

    window.onload = initNetwork;
  </script>
</body>
</html>
"""


def _run_coroutine_sync(coro: Any) -> Any:
    """Executes an asyncio coroutine synchronously in a dedicated thread/loop."""
    result = None
    exception = None

    def worker() -> None:
        nonlocal result, exception
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
        except Exception as e:
            exception = e
        finally:
            loop.close()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    if exception:
        raise exception
    return result


GLOBAL_ORCHESTRATOR = Orchestrator()


class HamsaApiHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler for the embedded Hamsa Web App & REST API."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default verbose HTTP logs to terminal."""
        pass

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html: str, status: int = 200) -> None:
        payload = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_text(self, text: str, content_type: str = "text/plain; charset=utf-8", status: int = 200) -> None:
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        if path in ("/", "/dashboard", "/index.html"):
            self._send_html(DASHBOARD_HTML)
        elif path == "/api/cases":
            from hamsa.core.cases import CaseManager
            cm = CaseManager()
            self._send_json({"cases": cm.list_cases()})
        elif path.startswith("/api/cases/"):
            from hamsa.core.cases import CaseManager
            cid = path.replace("/api/cases/", "").strip()
            cm = CaseManager()
            case = cm.get_case(cid)
            if case:
                self._send_json(case.to_dict())
            else:
                self._send_json({"error": "Case not found"}, status=404)
        elif path == "/api/timeline":
            from hamsa.core.reporting import ReportGenerator
            from hamsa.core.cases import CaseManager
            cid = query.get("case_id", [""])[0]
            if cid:
                cm = CaseManager()
                case = cm.get_case(cid)
                if case and case.graph_data:
                    from hamsa.core.graph import KnowledgeGraph
                    from hamsa.core.models import EntityNode
                    temp_graph = KnowledgeGraph()
                    for nd in case.graph_data.get("nodes", []):
                        temp_graph.add_node(EntityNode(
                            id=nd["id"],
                            type=TargetType(nd["type"]) if nd["type"] in TargetType._value2member_map_ else TargetType.GENERIC,
                            value=nd["value"],
                            label=nd["label"],
                            attributes=nd.get("attributes", {}),
                            confidence=nd.get("confidence", 1.0),
                        ))
                    reporter = ReportGenerator(temp_graph)
                    self._send_json({"timeline": reporter.generate_timeline(), "case_id": cid})
                    return
            reporter = ReportGenerator(GLOBAL_ORCHESTRATOR.graph)
            self._send_json({"timeline": reporter.generate_timeline(), "case_id": "active"})
        elif path == "/api/scan/stream":
            self.handle_sse_scan(query)
        elif path == "/api/graph":
            cid = query.get("case_id", [""])[0]
            if cid:
                from hamsa.core.cases import CaseManager
                cm = CaseManager()
                case = cm.get_case(cid)
                if case:
                    self._send_json(case.graph_data)
                    return
            self._send_json(GLOBAL_ORCHESTRATOR.graph.to_dict())
        elif path == "/api/plugins":
            self._send_json({"plugins": GLOBAL_ORCHESTRATOR.list_plugins()})
        elif path == "/api/cache/stats":
            from hamsa.core.cache import GLOBAL_CACHE
            self._send_json(GLOBAL_CACHE.stats())
        elif path == "/api/watchlist":
            from hamsa.core.monitor import WatchlistManager
            wm = WatchlistManager()
            self._send_json({"watchlist": [t.to_dict() for t in wm.list_all()]})
        elif path == "/api/report":
            from hamsa.core.reporting import ReportGenerator
            reporter = ReportGenerator(GLOBAL_ORCHESTRATOR.graph)
            fmt = query.get("format", ["html"])[0].lower()
            title = query.get("title", ["HAMSA OSINT Intelligence Dossier"])[0]
            # Identify roots from graph nodes
            targets = [(n.value, n.type) for n in GLOBAL_ORCHESTRATOR.graph.nodes.values() if n.confidence >= 0.95][:3]
            if not targets:
                targets = [("Target Subject", TargetType.USERNAME)]

            if fmt in ("md", "markdown"):
                content = reporter.generate_markdown(targets, title)
                self._send_text(content, content_type="text/markdown; charset=utf-8")
            else:
                content = reporter.generate_html(targets, title)
                self._send_html(content)
        else:
            self.send_error(404, "Endpoint Not Found")

    def handle_sse_scan(self, query: Dict[str, List[str]]) -> None:
        """Streams real-time OSINT scan events using Server-Sent Events (SSE)."""
        username = query.get("username", [""])[0]
        email = query.get("email", [""])[0]
        phone = query.get("phone", [""])[0]
        depth = int(query.get("depth", ["2"])[0])
        case_id = query.get("case_id", ["case_default"])[0]
        all_sites = query.get("all_sites", ["false"])[0].lower() == "true"

        targets = []
        if username:
            targets.append((username, TargetType.USERNAME))
        if email:
            targets.append((email, TargetType.EMAIL))
        if phone:
            targets.append((phone, TargetType.PHONE))

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        def send_sse(event_name: str, payload_data: Any) -> None:
            try:
                chunk = f"event: {event_name}\ndata: {json.dumps(payload_data, ensure_ascii=False)}\n\n".encode("utf-8")
                self.wfile.write(chunk)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        send_sse("connected", {"status": "streaming_ready", "case_id": case_id, "targets": [t[0] for t in targets]})

        if not targets:
            send_sse("error", {"message": "No valid targets supplied"})
            return

        context = {"all_sites": all_sites}

        def on_event_emitter(event_name: str, event_data: Any) -> None:
            send_sse(event_name, event_data)

        try:
            graph = _run_coroutine_sync(
                GLOBAL_ORCHESTRATOR.scan(
                    targets,
                    context=context,
                    max_depth=depth,
                    recursive=True,
                    on_event=on_event_emitter,
                )
            )
            # Persist graph into case workspace
            from hamsa.core.cases import CaseManager
            cm = CaseManager()
            case = cm.get_case(case_id)
            if not case:
                case = cm.create_case(title=f"Investigation: {', '.join([t[0] for t in targets])}", case_id=case_id)
            case.graph_data = graph.to_dict()
            for t, typ in targets:
                if not any(et.get("value") == t for et in case.targets):
                    case.targets.append({"value": t, "type": typ.value})
            cm.save_case(case)

            send_sse("saved_to_case", {"case_id": case_id, "entities": len(graph.nodes), "relations": len(graph.edges)})
        except Exception as e:
            send_sse("error", {"message": str(e)})

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if path == "/api/cases":
            from hamsa.core.cases import CaseManager
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                title = data.get("title", "New Investigation")
                desc = data.get("description", "")
                tags = data.get("tags", ["Active"])
                cm = CaseManager()
                case = cm.create_case(title=title, description=desc, tags=tags)
                self._send_json({"success": True, "case": case.to_dict()})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path.startswith("/api/cases/") and path.endswith("/annotate"):
            from hamsa.core.cases import CaseManager
            parts = path.split("/")
            case_id = parts[3]
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                node_id = data.get("node_id")
                tag = data.get("tag")
                color = data.get("color")
                notes = data.get("notes")
                cm = CaseManager()
                ok = cm.annotate_node(case_id, node_id, tag=tag, color=color, notes=notes)
                self._send_json({"success": ok})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path.startswith("/api/cases/") and path.endswith("/notes"):
            from hamsa.core.cases import CaseManager
            parts = path.split("/")
            case_id = parts[3]
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                notes = data.get("notes", "")
                cm = CaseManager()
                case = cm.update_case(case_id, notes=notes)
                self._send_json({"success": bool(case), "case": case.to_dict() if case else None})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path == "/api/evidence/capture":
            from hamsa.core.cases import CaseManager
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                case_id = data.get("case_id", "case_default")
                url = data.get("url", "")
                title = data.get("title", "Web Capture")
                notes = data.get("notes", "")
                cm = CaseManager()
                ev = cm.add_evidence(case_id=case_id, url=url, title=title, evidence_type="web_snapshot", notes=notes)
                self._send_json({"success": True, "evidence": ev.to_dict() if ev else None})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path == "/api/reset":
            from hamsa.core.cache import GLOBAL_CACHE
            GLOBAL_ORCHESTRATOR.graph.clear()
            GLOBAL_CACHE.clear()
            self._send_json({"success": True, "message": "Graph and cache reset successfully"})
            return

        if path == "/api/cache/clear":
            from hamsa.core.cache import GLOBAL_CACHE
            GLOBAL_CACHE.clear()
            self._send_json({"success": True, "message": "Two-tier cache purged"})
            return

        if path == "/api/update-sources":
            sm = SourceManager()
            total = sm.update_sources()
            self._send_json({"success": True, "total_sites": total})
            return

        if path == "/api/watchlist":
            from hamsa.core.monitor import WatchlistManager
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                action = data.get("action", "add")
                val = data.get("value", "").strip()
                t_type = data.get("target_type", "username")

                wm = WatchlistManager()
                if action == "remove":
                    removed = wm.remove(val, target_type=t_type)
                    self._send_json({"success": removed, "watchlist": [t.to_dict() for t in wm.list_all()]})
                else:
                    entry = wm.add(val, target_type=t_type, tags=data.get("tags", []), notes=data.get("notes", ""))
                    self._send_json({"success": True, "entry": entry.to_dict(), "watchlist": [t.to_dict() for t in wm.list_all()]})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path == "/api/watchlist/check":
            from hamsa.core.monitor import ScanDiffEngine, WatchlistManager
            try:
                wm = WatchlistManager()
                items = wm.list_all()
                results = []
                snapshot_dir = os.path.expanduser("~/.hamsa/snapshots")
                os.makedirs(snapshot_dir, exist_ok=True)

                for item in items:
                    t_type = TargetType.USERNAME
                    if item.target_type == "email":
                        t_type = TargetType.EMAIL
                    elif item.target_type == "phone":
                        t_type = TargetType.PHONE

                    tg = _run_coroutine_sync(GLOBAL_ORCHESTRATOR.scan([(item.value, t_type)], max_depth=2, recursive=True))
                    new_snap = tg.to_dict()
                    snap_file = os.path.join(snapshot_dir, f"{item.target_type}_{item.value.replace('/', '_')}.json")
                    old_snap = {}
                    if os.path.exists(snap_file):
                        try:
                            with open(snap_file, "r", encoding="utf-8") as f:
                                old_snap = json.load(f)
                        except Exception:
                            pass
                    diff = ScanDiffEngine.compute_diff(old_snap, new_snap)
                    wm.update_scanned(item.value, item.target_type)
                    with open(snap_file, "w", encoding="utf-8") as f:
                        json.dump(new_snap, f, indent=2, ensure_ascii=False)
                    results.append({"target": item.value, "type": item.target_type, "diff": diff})

                self._send_json({"success": True, "results": results})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path == "/api/cypher":
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                query = data.get("query", "")
                params = data.get("params", {})
                records = GLOBAL_ORCHESTRATOR.graph.execute_cypher(query, params)
                self._send_json({"success": True, "query": query, "records": records})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path == "/api/report":
            from hamsa.core.reporting import ReportGenerator
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                fmt = data.get("format", "html").lower()
                title = data.get("title", "HAMSA OSINT Intelligence Dossier")
                reporter = ReportGenerator(GLOBAL_ORCHESTRATOR.graph)
                targets = [(n.value, n.type) for n in GLOBAL_ORCHESTRATOR.graph.nodes.values() if n.confidence >= 0.95][:3]
                if not targets:
                    targets = [("Target Subject", TargetType.USERNAME)]

                if fmt in ("md", "markdown"):
                    content = reporter.generate_markdown(targets, title)
                else:
                    content = reporter.generate_html(targets, title)

                self._send_json({"success": True, "format": fmt, "content": content})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path == "/api/scan":
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                username = data.get("username")
                email = data.get("email")
                phone = data.get("phone")
                depth = int(data.get("depth", 2))
                case_id = data.get("case_id", "case_default")

                targets = []
                if username:
                    targets.append((username, TargetType.USERNAME))
                if email:
                    targets.append((email, TargetType.EMAIL))
                if phone:
                    targets.append((phone, TargetType.PHONE))

                if not targets:
                    self._send_json({"error": "No targets provided"}, status=400)
                    return

                context = {
                    "all_sites": data.get("all_sites", False),
                    "getcontact_token": data.get("getcontact_token"),
                    "truecaller_token": data.get("truecaller_token"),
                    "proxy": data.get("proxy"),
                }

                graph = _run_coroutine_sync(GLOBAL_ORCHESTRATOR.scan(targets, context=context, max_depth=depth, recursive=True))
                
                # Persist in case
                from hamsa.core.cases import CaseManager
                cm = CaseManager()
                case = cm.get_case(case_id)
                if not case:
                    case = cm.create_case(title=f"Investigation: {', '.join([t[0] for t in targets])}", case_id=case_id)
                case.graph_data = graph.to_dict()
                for t, typ in targets:
                    if not any(et.get("value") == t for et in case.targets):
                        case.targets.append({"value": t, "type": typ.value})
                cm.save_case(case)

                self._send_json(graph.to_dict())
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        self.send_error(404, "Endpoint Not Found")


def is_port_available(host: str, port: int) -> bool:
    """Checks whether a TCP port is free for binding."""
    if port == 8080:
        # CRITICAL CONSTRAINT: Never probe or bind port 8080 (reserved for user's ocrawler)
        return False
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_safe_port(host: str = "0.0.0.0", start_port: int = 8888) -> int:
    """Finds the first available port starting from start_port, strictly avoiding port 8080."""
    if start_port == 8080:
        start_port = 8888
    for p in range(start_port, start_port + 50):
        if p == 8080:
            continue
        if is_port_available(host, p):
            return p
    return 8889


def run_server(host: str = "0.0.0.0", port: int = 8888) -> None:
    """Starts the embedded Hamsa HTTP web application with strict pre-flight port verification."""
    if port == 8080 or not is_port_available(host, port):
        safe_port = find_safe_port(host, start_port=8888 if port == 8080 else port + 1)
        log_info(f"Port {port} avoided or occupied. Automatically using safe port: {safe_port}")
        port = safe_port

    # Attempt Enterprise ASGI Engine (FastAPI + Uvicorn)
    try:
        import uvicorn
        from hamsa.web.enterprise_app import app
        log_success(f"Starting HAMSA Enterprise ASGI Engine (FastAPI + Uvicorn) on: http://{host}:{port}")
        log_info(f"Interactive OpenAPI/Swagger Documentation: http://{host}:{port}/docs")
        uvicorn.run(app, host=host, port=port, log_level="info")
        return
    except ImportError:
        log_info("FastAPI/Uvicorn not found. Operating in lightweight stdlib HTTP server mode.")

    server_address = (host, port)
    httpd = HTTPServer(server_address, HamsaApiHandler)
    log_success(f"Hamsa Web Dashboard & REST API is running at: http://{host}:{port}")
    log_info("Press Ctrl+C to terminate the web server.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log_info("Shutting down Hamsa web server...")
        httpd.server_close()
