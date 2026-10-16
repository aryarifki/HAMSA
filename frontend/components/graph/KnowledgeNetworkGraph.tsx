"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import { Icon } from "@iconify/react";
import { useAppStore } from "@/store/useAppStore";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load intelligence graph");
  return res.json();
};

interface GraphNode {
  id: string;
  label: string;
  type: string;
  value: string;
  confidence: number;
  source_plugin?: string;
  attributes?: Record<string, any>;
}

interface GraphEdge {
  source: string;
  target: string;
  relation_type: string;
  label?: string;
  confidence?: number;
}

interface GraphData {
  summary: {
    total_entities: number;
    total_relations: number;
  };
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export default function KnowledgeNetworkGraph() {
  const { theme, activeCaseId, activeCaseTitle, setCacheLoading } = useAppStore();
  const isDark = theme === "dark";

  const { data, error, isLoading, mutate } = useSWR<GraphData>(
    `/api/graph?case_id=${encodeURIComponent(activeCaseId)}`,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 10000 }
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>("all");
  const [layoutMode, setLayoutMode] = useState<"force" | "circular">("force");
  const [graphViewMode, setGraphViewMode] = useState<"network" | "table">("network");
  const [liveStreaming, setLiveStreaming] = useState(false);
  const [streamStats, setStreamStats] = useState({ nodes: 0, edges: 0, lastEvent: "Idle" });
  const [annotationNote, setAnnotationNote] = useState("");
  const [annotationTag, setAnnotationTag] = useState("Suspect");
  const [liveNodes, setLiveNodes] = useState<GraphNode[]>([]);
  const [liveEdges, setLiveEdges] = useState<GraphEdge[]>([]);
  const chartInstanceRef = useRef<any>(null);

  // Sync SWR data into live working state
  useEffect(() => {
    if (data?.nodes) {
      setLiveNodes(data.nodes);
    }
    if (data?.edges) {
      setLiveEdges(data.edges);
    }
  }, [data]);

  // Category Colors
  const typeColors: Record<string, string> = {
    username: "#10B981",
    email: "#3B82F6",
    phone: "#F59E0B",
    breach: "#EF4444",
    generic: "#06B6D4",
    image: "#8B5CF6",
    device: "#EC4899",
    location: "#A855F7",
  };

  // Real-Time EventSource Scan Trigger
  const handleStartLiveStream = (targetVal?: string, targetType?: string) => {
    const val = targetVal || prompt("Enter target to stream live reconnaissance:", "torvalds");
    if (!val) return;
    const typ = targetType || (val.includes("@") ? "email" : /^\+?[0-9]{7,15}$/.test(val) ? "phone" : "username");

    setLiveStreaming(true);
    setStreamStats({ nodes: 0, edges: 0, lastEvent: "Initiating live stream..." });

    const sseUrl = `/api/scan/stream?${typ}=${encodeURIComponent(val)}&case_id=${encodeURIComponent(activeCaseId)}&depth=2`;
    const es = new EventSource(sseUrl);

    es.addEventListener("node_added", (evt) => {
      try {
        const node: GraphNode = JSON.parse(evt.data);
        setLiveNodes((prev) => {
          if (prev.some((n) => n.id === node.id)) return prev;
          return [...prev, node];
        });
        setStreamStats((s) => ({ ...s, nodes: s.nodes + 1, lastEvent: `Discovered: ${node.label}` }));
      } catch (err) {}
    });

    es.addEventListener("edge_added", (evt) => {
      try {
        const edge: GraphEdge = JSON.parse(evt.data);
        setLiveEdges((prev) => {
          if (prev.some((e) => e.source === edge.source && e.target === edge.target)) return prev;
          return [...prev, edge];
        });
        setStreamStats((s) => ({ ...s, edges: s.edges + 1 }));
      } catch (err) {}
    });

    es.addEventListener("complete", () => {
      setStreamStats((s) => ({ ...s, lastEvent: "Reconnaissance Complete" }));
      setTimeout(() => {
        setLiveStreaming(false);
        es.close();
        mutate();
      }, 1500);
    });

    es.addEventListener("error", () => {
      setLiveStreaming(false);
      es.close();
      mutate();
    });
  };

  // Node Annotation (Mark Suspect, verified lead)
  const handleAnnotateNode = async () => {
    if (!selectedNode) return;
    try {
      await fetch(`/api/cases/${encodeURIComponent(activeCaseId)}/annotate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          node_id: selectedNode.id,
          tag: annotationTag,
          color: annotationTag === "Primary Suspect" ? "#ef4444" : annotationTag === "Verified Lead" ? "#10b981" : "#f59e0b",
          notes: annotationNote,
        }),
      });

      // Update in local state
      setLiveNodes((prev) =>
        prev.map((n) =>
          n.id === selectedNode.id
            ? {
                ...n,
                attributes: {
                  ...n.attributes,
                  investigator_tag: annotationTag,
                  investigator_notes: annotationNote,
                },
              }
            : n
        )
      );

      setCacheLoading({
        isOpen: true,
        title: "Node Annotated",
        step: `Marked ${selectedNode.label} as ${annotationTag}`,
        progress: 100,
        isSuccess: true,
      });
      setTimeout(() => setCacheLoading(false), 800);
    } catch (err) {
      alert("Failed to annotate node: " + err);
    }
  };

  // Capture Digital Evidence
  const handleCaptureEvidence = async () => {
    if (!selectedNode) return;
    const url = selectedNode.attributes?.url || selectedNode.value;
    try {
      const res = await fetch("/api/evidence/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_id: activeCaseId,
          url: url,
          title: `Evidence: ${selectedNode.label}`,
          notes: `Captured from node ${selectedNode.id}`,
        }),
      });
      const d = await res.json();
      if (d.success) {
        setCacheLoading({
          isOpen: true,
          title: "Evidence Secured",
          step: `Saved forensic snapshot for ${selectedNode.label}`,
          progress: 100,
          isSuccess: true,
        });
        setTimeout(() => setCacheLoading(false), 800);
      }
    } catch (err) {
      alert("Failed to capture evidence: " + err);
    }
  };

  const filteredNodes = useMemo(() => {
    return liveNodes.filter((n) => {
      const matchType = selectedTypeFilter === "all" || n.type === selectedTypeFilter;
      return matchType;
    });
  }, [liveNodes, selectedTypeFilter]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return liveEdges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  }, [liveEdges, filteredNodeIds]);

  // Lookup of relational connections per node
  const nodeConnections = useMemo(() => {
    const map: Record<string, { count: number; targets: string[] }> = {};
    liveEdges.forEach((edge) => {
      if (!map[edge.source]) map[edge.source] = { count: 0, targets: [] };
      if (!map[edge.target]) map[edge.target] = { count: 0, targets: [] };
      map[edge.source].count += 1;
      map[edge.source].targets.push(edge.target);
      map[edge.target].count += 1;
      map[edge.target].targets.push(edge.source);
    });
    return map;
  }, [liveEdges]);

  // Entities filtered for the human-readable table view
  const tableNodes = useMemo(() => {
    return filteredNodes.filter((n) => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        (n.label && n.label.toLowerCase().includes(q)) ||
        (n.value && n.value.toLowerCase().includes(q)) ||
        (n.source_plugin && n.source_plugin.toLowerCase().includes(q)) ||
        (n.type && n.type.toLowerCase().includes(q))
      );
    });
  }, [filteredNodes, searchQuery]);

  const chartOption = useMemo(() => {
    const categories = Array.from(new Set(liveNodes.map((n) => n.type))).map((type) => ({
      name: type.toUpperCase(),
      itemStyle: { color: typeColors[type] || "#94a3b8" },
    }));

    const chartNodes = filteredNodes.map((n) => {
      const isSelected = selectedNode?.id === n.id;
      const isSearchMatch = searchQuery
        ? (n.label && String(n.label).toLowerCase().includes(searchQuery.toLowerCase())) ||
          (n.value && String(n.value).toLowerCase().includes(searchQuery.toLowerCase()))
        : true;

      // Dim non-matching nodes when search is active
      const nodeOpacity = searchQuery ? (isSearchMatch ? 1.0 : 0.15) : 1.0;
      const customColor = n.attributes?.custom_color;

      return {
        id: n.id,
        name: n.label,
        value: n.value,
        category: n.type.toUpperCase(),
        symbolSize: isSelected ? 34 : isSearchMatch && searchQuery ? 30 : n.attributes?.initial_target ? 26 : 18,
        itemStyle: {
          color: customColor || typeColors[n.type] || "#94a3b8",
          borderColor: isSelected ? "#FFB879" : isSearchMatch && searchQuery ? "#FFB879" : "#ffffff",
          borderWidth: isSelected || (isSearchMatch && searchQuery) ? 3 : 1,
          opacity: nodeOpacity,
          shadowBlur: isSelected ? 20 : isSearchMatch && searchQuery ? 15 : 4,
          shadowColor: isSelected || (isSearchMatch && searchQuery) ? "rgba(255, 184, 121, 0.7)" : "rgba(0,0,0,0.3)",
        },
        label: {
          show: isSelected || (isSearchMatch && searchQuery) || !searchQuery,
          position: "right",
          color: isDark ? "#EBE0D9" : "#1E1A17",
          fontSize: 11,
          fontWeight: isSelected || (isSearchMatch && searchQuery) ? "bold" : "normal",
        },
        rawNode: n,
      };
    });

    const chartLinks = filteredEdges.map((e) => ({
      source: e.source,
      target: e.target,
      label: {
        show: false,
        formatter: e.label || e.relation_type,
        fontSize: 9,
      },
      lineStyle: {
        color: isDark ? "rgba(215, 194, 180, 0.25)" : "rgba(132, 116, 106, 0.35)",
        curveness: 0.1,
        width: 1.5,
      },
    }));

    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item",
        backgroundColor: isDark ? "#211D1A" : "#EDDFD3",
        borderColor: isDark ? "#52443C" : "#D7C2B4",
        textStyle: { color: isDark ? "#EBE0D9" : "#1E1A17", fontSize: 12 },
        formatter: (params: any) => {
          if (params.dataType === "node") {
            const n = params.data.rawNode;
            const tag = n.attributes?.investigator_tag ? `<br/><b style="color:#FFB879;">[${n.attributes.investigator_tag}]</b>` : "";
            return `<b>${n.label}</b>${tag}<br/>Type: ${n.type}<br/>Source: ${n.source_plugin || "Core"}<br/>Confidence: ${Math.round(n.confidence * 100)}%`;
          }
          return `${params.data.source} ➔ ${params.data.target}`;
        },
      },
      legend: {
        data: categories.map((c) => c.name),
        textStyle: { color: isDark ? "#D7C2B4" : "#4E453F", fontSize: 11 },
        top: 10,
        left: 20,
      },
      series: [
        {
          type: "graph",
          layout: layoutMode,
          force: {
            repulsion: 420,
            edgeLength: [60, 160],
            gravity: 0.08,
          },
          circular: {
            rotateLabel: true,
          },
          roam: true,
          draggable: true,
          data: chartNodes,
          links: chartLinks,
          categories: categories,
          emphasis: {
            focus: "adjacency",
            lineStyle: { width: 3 },
          },
        },
      ],
    };
  }, [filteredNodes, filteredEdges, layoutMode, isDark, selectedNode, searchQuery]);

  const onChartClick = (params: any) => {
    if (params.dataType === "node") {
      setSelectedNode(params.data.rawNode);
      setAnnotationNote(params.data.rawNode.attributes?.investigator_notes || "");
      setAnnotationTag(params.data.rawNode.attributes?.investigator_tag || "Primary Suspect");
    }
  };

  const handleExportPNG = () => {
    if (chartInstanceRef.current) {
      const base64 = chartInstanceRef.current.getDataURL({
        type: "png",
        pixelRatio: 2,
        backgroundColor: isDark ? "#141210" : "#F9EDE1",
      });
      const a = document.createElement("a");
      a.href = base64;
      a.download = `hamsa_case_${activeCaseId}_${Date.now()}.png`;
      a.click();
    }
  };

  return (
    <div className="relative w-full h-[calc(100vh-7rem)] flex flex-col md:flex-row overflow-hidden rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)]">
      
      {/* CANVAS MAIN VIEW */}
      <div className="flex-1 relative h-full flex flex-col">
        {/* TOP TOOLBAR */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 px-4 py-3 border-b border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-high)]/80 backdrop-blur-md z-10">
          <div className="flex items-center gap-2 flex-wrap">
            {/* VIEW MODE TOGGLE (NETWORK GRAPH VS FORENSIC TABLE) */}
            <div className="flex items-center rounded-xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-highest)] p-0.5 shadow-2xs">
              <button
                type="button"
                onClick={() => setGraphViewMode("network")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg font-bold transition-all cursor-pointer ${
                  graphViewMode === "network"
                    ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-xs"
                    : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
                }`}
              >
                <Icon icon="ph:graph-bold" width="14" />
                <span>Graf Jaringan</span>
              </button>
              <button
                type="button"
                onClick={() => setGraphViewMode("table")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg font-bold transition-all cursor-pointer ${
                  graphViewMode === "table"
                    ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-xs"
                    : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
                }`}
              >
                <Icon icon="ph:table-bold" width="14" />
                <span>Tabel Forensik</span>
              </button>
            </div>

            {/* SEARCH HIGHLIGHT INPUT */}
            <div className="relative w-44 sm:w-56">
              <Icon icon="ph:magnifying-glass-duotone" className="absolute left-2.5 top-2.5 text-[var(--md-sys-color-on-surface-variant)]" width="16" />
              <input
                type="text"
                placeholder={graphViewMode === "table" ? "Cari nama, value, plugin..." : "Sorot entitas di graf..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] outline-none focus:border-[var(--md-sys-color-primary)] font-medium"
              />
            </div>

            {/* FILTER TYPE DROPDOWN */}
            <select
              value={selectedTypeFilter}
              onChange={(e) => setSelectedTypeFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] font-semibold cursor-pointer outline-none"
            >
              <option value="all">Semua Tipe Entitas</option>
              <option value="username">Usernames</option>
              <option value="email">Emails</option>
              <option value="phone">Phones</option>
              <option value="breach">Kebocoran Data (Breaches)</option>
              <option value="generic">Entitas Lainnya</option>
            </select>

            {/* LAYOUT MODE BUTTONS (ONLY VISIBLE IN GRAPH MODE) */}
            {graphViewMode === "network" && (
              <div className="flex items-center rounded-xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-highest)] p-0.5">
                <button
                  type="button"
                  onClick={() => setLayoutMode("force")}
                  className={`px-2.5 py-1 text-xs rounded-lg font-bold transition-all cursor-pointer ${
                    layoutMode === "force"
                      ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)]"
                      : "text-[var(--md-sys-color-on-surface-variant)]"
                  }`}
                >
                  Force
                </button>
                <button
                  type="button"
                  onClick={() => setLayoutMode("circular")}
                  className={`px-2.5 py-1 text-xs rounded-lg font-bold transition-all cursor-pointer ${
                    layoutMode === "circular"
                      ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)]"
                      : "text-[var(--md-sys-color-on-surface-variant)]"
                  }`}
                >
                  Circular
                </button>
              </div>
            )}
          </div>

          {/* ACTION BUTTONS & LIVE RADAR STREAM TRIGGER */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleStartLiveStream()}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer ${
                liveStreaming
                  ? "bg-rose-500 text-white animate-pulse"
                  : "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] hover:opacity-90"
              }`}
            >
              <Icon icon="ph:broadcast-duotone" width="15" />
              <span>{liveStreaming ? "Streaming..." : "Live Radar Recon"}</span>
            </button>

            <button
              onClick={() => mutate()}
              className="p-1.5 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] hover:bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface)] border border-[var(--md-sys-color-outline-variant)] text-xs cursor-pointer shadow-2xs"
              title="Refresh Graph"
            >
              <Icon icon="ph:arrows-clockwise-bold" width="15" />
            </button>

            {graphViewMode === "network" && (
              <button
                onClick={handleExportPNG}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] hover:bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface)] border border-[var(--md-sys-color-outline-variant)] text-xs font-semibold cursor-pointer shadow-2xs"
              >
                <Icon icon="ph:download-simple-bold" width="14" />
                <span>Snapshot</span>
              </button>
            )}
          </div>
        </div>

        {/* LIVE STREAMING RADAR STATUS BAR */}
        {liveStreaming && (
          <div className="px-4 py-2 bg-emerald-500/15 border-b border-emerald-500/30 flex items-center justify-between text-xs font-mono text-emerald-400 animate-in fade-in">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>RADAR SSE STREAM ACTIVE: {streamStats.lastEvent}</span>
            </div>
            <div className="flex items-center gap-3">
              <span>+{streamStats.nodes} Nodes</span>
              <span>+{streamStats.edges} Links</span>
            </div>
          </div>
        )}

        {/* ECHARTS CANVAS OR FORENSIC TABLE */}
        <div className="flex-1 w-full h-full relative overflow-hidden">
          {isLoading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <Icon icon="ph:spinner-bold" className="animate-spin text-[var(--md-sys-color-primary)]" width="36" />
              <p className="text-xs font-mono text-[var(--md-sys-color-on-surface-variant)]">
                Synthesizing Graph Entities for {activeCaseTitle}...
              </p>
            </div>
          ) : liveNodes.length === 0 ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] flex items-center justify-center text-3xl mb-3">
                🪬
              </div>
              <h3 className="text-base font-bold text-[var(--md-sys-color-on-surface)]">
                Belum Ada Entitas Intelijen di {activeCaseTitle}
              </h3>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-sm mt-1">
                Lakukan pelacakan target di Beranda atau klik &quot;Live Radar Recon&quot; untuk mengumpulkan entitas korelasi.
              </p>
            </div>
          ) : graphViewMode === "table" ? (
            /* FORENSIC TABLE VIEW */
            <div className="h-full overflow-y-auto p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--md-sys-color-on-surface-variant)] pb-2 border-b border-[var(--md-sys-color-outline-variant)]">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-[var(--md-sys-color-on-surface)]">
                    {tableNodes.length} Entitas
                  </span>
                  <span>•</span>
                  <span>{liveEdges.length} Relasi Kausalitas Terkoneksi</span>
                </div>
                <div className="text-[11px] font-mono text-[var(--md-sys-color-primary)]">
                  Klik baris untuk membuka Workbench & Aksi Forensik di samping →
                </div>
              </div>

              {tableNodes.length === 0 ? (
                <div className="py-12 text-center text-xs text-[var(--md-sys-color-on-surface-variant)]">
                  Tidak ada entitas yang sesuai dengan filter atau pencarian &quot;{searchQuery}&quot;.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)]">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] text-[11px] font-bold uppercase tracking-wider border-b border-[var(--md-sys-color-outline-variant)]">
                      <tr>
                        <th className="py-3 px-4">Tipe & Identitas</th>
                        <th className="py-3 px-4">Plugin Sumber</th>
                        <th className="py-3 px-4 text-center">Confidence</th>
                        <th className="py-3 px-4 text-center">Koneksi</th>
                        <th className="py-3 px-4">Atribut & Bukti</th>
                        <th className="py-3 px-4 text-right">Aksi</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--md-sys-color-outline-variant)]/60">
                      {tableNodes.map((node) => {
                        const isSelected = selectedNode?.id === node.id;
                        const conn = nodeConnections[node.id] || { count: 0, targets: [] };
                        const color = typeColors[node.type] || "#94a3b8";

                        return (
                          <tr
                            key={node.id}
                            onClick={() => {
                              setSelectedNode(node);
                              setAnnotationNote(node.attributes?.investigator_notes || "");
                              setAnnotationTag(node.attributes?.investigator_tag || "Primary Suspect");
                            }}
                            className={`cursor-pointer transition-colors ${
                              isSelected
                                ? "bg-[var(--md-sys-color-primary)]/15 font-medium"
                                : "hover:bg-[var(--md-sys-color-surface-container-high)]"
                            }`}
                          >
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2.5">
                                <span
                                  className="w-2.5 h-2.5 rounded-full shrink-0"
                                  style={{ backgroundColor: color }}
                                />
                                <div className="min-w-0">
                                  <div className="font-bold text-[var(--md-sys-color-on-surface)] truncate max-w-xs md:max-w-sm">
                                    {node.label}
                                  </div>
                                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)]">
                                    {node.type}
                                  </span>
                                </div>
                              </div>
                            </td>

                            <td className="py-3 px-4 font-mono text-[11px] text-[var(--md-sys-color-on-surface-variant)]">
                              {node.source_plugin || "core_scanner"}
                            </td>

                            <td className="py-3 px-4 text-center">
                              <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-bold font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                {Math.round(node.confidence * 100)}%
                              </span>
                            </td>

                            <td className="py-3 px-4 text-center">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface)]">
                                <Icon icon="ph:git-commit-bold" width="12" />
                                {conn.count} relasi
                              </span>
                            </td>

                            <td className="py-3 px-4">
                              <div className="flex flex-wrap gap-1 max-w-xs">
                                {node.attributes && Object.keys(node.attributes).length > 0 ? (
                                  Object.entries(node.attributes).slice(0, 2).map(([k, v]) => (
                                    <span
                                      key={k}
                                      className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] font-mono truncate max-w-[140px]"
                                      title={`${k}: ${String(v)}`}
                                    >
                                      {k}: {String(v)}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] italic">
                                    -
                                  </span>
                                )}
                              </div>
                            </td>

                            <td className="py-3 px-4 text-right">
                              <div className="inline-flex items-center gap-1.5">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigator.clipboard.writeText(node.value || node.label);
                                  }}
                                  className="p-1 rounded hover:bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] cursor-pointer"
                                  title="Salin Nilai"
                                >
                                  <Icon icon="ph:copy-bold" width="13" />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedNode(node);
                                    setAnnotationNote(node.attributes?.investigator_notes || "");
                                    setAnnotationTag(node.attributes?.investigator_tag || "Primary Suspect");
                                  }}
                                  className="px-2 py-1 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] hover:bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-primary)] font-bold text-[11px] cursor-pointer"
                                >
                                  Workbench
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : (
            <ReactECharts
              option={chartOption}
              style={{ width: "100%", height: "100%" }}
              onEvents={{ click: onChartClick }}
              onChartReady={(instance: any) => {
                chartInstanceRef.current = instance;
              }}
              opts={{ renderer: "canvas" }}
            />
          )}
        </div>
      </div>

      {/* RIGHT SIDE INVESTIGATION WORKBENCH & INSPECTOR DRAWER */}
      {selectedNode && (
        <aside className="w-full md:w-80 lg:w-96 border-t md:border-t-0 md:border-l border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-high)] p-5 flex flex-col justify-between overflow-y-auto z-10 shadow-xl space-y-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--md-sys-color-outline-variant)]">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: typeColors[selectedNode.type] || "#94a3b8" }} />
                <h4 className="font-bold text-sm text-[var(--md-sys-color-on-surface)] uppercase tracking-wider">
                  Investigator Workbench
                </h4>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-lg hover:bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] cursor-pointer"
              >
                <Icon icon="ph:x-bold" width="14" />
              </button>
            </div>

            <div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--md-sys-color-on-surface-variant)]">
                Entity Label
              </div>
              <div className="text-base font-extrabold text-[var(--md-sys-color-on-surface)] break-all mt-0.5">
                {selectedNode.label}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)]/60 font-mono text-xs">
              <div>
                <span className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] block">Type</span>
                <span className="font-bold text-[var(--md-sys-color-primary)] uppercase">{selectedNode.type}</span>
              </div>
              <div>
                <span className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] block">Confidence</span>
                <span className="font-bold text-emerald-500">{Math.round(selectedNode.confidence * 100)}%</span>
              </div>
            </div>

            {/* ACTION BUTTONS: PIVOT, CAPTURE, ANNOTATE */}
            <div className="space-y-2 pt-2 border-t border-[var(--md-sys-color-outline-variant)]/60">
              <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--md-sys-color-primary)]">
                Forensic Actions & Pivoting
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleStartLiveStream(selectedNode.value, selectedNode.type)}
                  className="py-2 px-2.5 rounded-xl bg-[var(--md-sys-color-primary)] hover:opacity-90 text-[var(--md-sys-color-on-primary)] text-xs font-bold transition-all shadow-xs flex items-center justify-center gap-1 cursor-pointer"
                >
                  <Icon icon="ph:arrows-split-bold" width="14" />
                  <span>Pivot / Scan</span>
                </button>
                <button
                  onClick={handleCaptureEvidence}
                  className="py-2 px-2.5 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] hover:bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] text-xs font-semibold transition-all flex items-center justify-center gap-1 cursor-pointer"
                >
                  <Icon icon="ph:camera-bold" width="14" />
                  <span>Capture Proof</span>
                </button>
              </div>
            </div>

            {/* MANUAL ANNOTATION SECTION */}
            <div className="space-y-2 pt-2 border-t border-[var(--md-sys-color-outline-variant)]/60">
              <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--md-sys-color-on-surface-variant)]">
                Manual Marking & Notes
              </div>
              <div className="flex gap-2">
                {["Primary Suspect", "Verified Lead", "Review Later"].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setAnnotationTag(t)}
                    className={`flex-1 py-1 px-1.5 rounded-lg text-[10px] font-bold transition-all border cursor-pointer ${
                      annotationTag === t
                        ? "bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] border-[var(--md-sys-color-primary)]"
                        : "bg-[var(--md-sys-color-surface-container)] border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)]"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <textarea
                rows={2}
                placeholder="Investigator note on this entity..."
                value={annotationNote}
                onChange={(e) => setAnnotationNote(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] outline-none focus:border-[var(--md-sys-color-primary)] transition-all font-mono"
              />
              <button
                onClick={handleAnnotateNode}
                className="w-full py-1.5 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] hover:bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] text-xs font-bold cursor-pointer"
              >
                Save Marking to Case
              </button>
            </div>

            {/* RAW ATTRIBUTES PAYLOAD */}
            <div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--md-sys-color-on-surface-variant)] mb-1.5">
                Attributes Payload
              </div>
              <pre className="text-[11px] p-3 rounded-xl bg-[var(--md-sys-color-surface-container-lowest)] text-[var(--md-sys-color-on-surface-variant)] border border-[var(--md-sys-color-outline-variant)]/50 overflow-x-auto max-h-40 font-mono">
                {JSON.stringify(selectedNode.attributes || {}, null, 2)}
              </pre>
            </div>
          </div>

          <div className="pt-3 border-t border-[var(--md-sys-color-outline-variant)]">
            <button
              onClick={() => setSelectedNode(null)}
              className="w-full py-2 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] hover:bg-[var(--md-sys-color-surface-container)] text-xs font-semibold text-[var(--md-sys-color-on-surface)] transition-colors cursor-pointer"
            >
              Close Workbench
            </button>
          </div>
        </aside>
      )}

    </div>
  );
}
