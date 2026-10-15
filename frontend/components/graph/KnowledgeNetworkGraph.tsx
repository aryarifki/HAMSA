"use client";

import React, { useState, useMemo, useRef } from "react";
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
  const { theme } = useAppStore();
  const isDark = theme === "dark";

  const { data, error, isLoading, mutate } = useSWR<GraphData>(
    "/api/graph",
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 15000 }
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>("all");
  const [layoutMode, setLayoutMode] = useState<"force" | "circular">("force");
  const chartInstanceRef = useRef<any>(null);

  const rawNodes = data?.nodes || [];
  const rawEdges = data?.edges || [];

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

  const filteredNodes = useMemo(() => {
    return rawNodes.filter((n) => {
      const matchType = selectedTypeFilter === "all" || n.type === selectedTypeFilter;
      const matchSearch =
        !searchQuery ||
        n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        n.value.toLowerCase().includes(searchQuery.toLowerCase());
      return matchType && matchSearch;
    });
  }, [rawNodes, selectedTypeFilter, searchQuery]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return rawEdges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  }, [rawEdges, filteredNodeIds]);

  const chartOption = useMemo(() => {
    const categories = Array.from(new Set(rawNodes.map((n) => n.type))).map((type) => ({
      name: type.toUpperCase(),
      itemStyle: { color: typeColors[type] || "#94a3b8" },
    }));

    const chartNodes = filteredNodes.map((n) => {
      const isSelected = selectedNode?.id === n.id;
      return {
        id: n.id,
        name: n.label,
        value: n.value,
        category: n.type.toUpperCase(),
        symbolSize: isSelected ? 32 : (n.attributes?.initial_target ? 26 : 18),
        itemStyle: {
          color: typeColors[n.type] || "#94a3b8",
          borderColor: isSelected ? "#FFB879" : "#ffffff",
          borderWidth: isSelected ? 3 : 1,
          shadowBlur: isSelected ? 15 : 4,
          shadowColor: isSelected ? "rgba(255, 184, 121, 0.6)" : "rgba(0,0,0,0.3)",
        },
        label: {
          show: true,
          position: "right",
          color: isDark ? "#EBE0D9" : "#1E1A17",
          fontSize: 11,
          fontWeight: isSelected ? "bold" : "normal",
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
            return `<b>${n.label}</b><br/>Type: ${n.type}<br/>Source: ${n.source_plugin || "Core"}<br/>Confidence: ${Math.round(n.confidence * 100)}%`;
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
            repulsion: 400,
            edgeLength: [60, 150],
            gravity: 0.1,
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
  }, [filteredNodes, filteredEdges, layoutMode, isDark, selectedNode]);

  const onChartClick = (params: any) => {
    if (params.dataType === "node") {
      setSelectedNode(params.data.rawNode);
    }
  };

  const handleExportPNG = () => {
    if (chartInstanceRef.current) {
      const base64 = chartInstanceRef.current.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: isDark ? "#141210" : "#F9EDE1" });
      const a = document.createElement("a");
      a.href = base64;
      a.download = `hamsa_knowledge_graph_${Date.now()}.png`;
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
            {/* SEARCH INPUT */}
            <div className="relative w-48 sm:w-60">
              <Icon icon="ph:magnifying-glass-duotone" className="absolute left-2.5 top-2.5 text-[var(--md-sys-color-on-surface-variant)]" width="16" />
              <input
                type="text"
                placeholder="Search node on canvas..."
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
              <option value="all">All Entity Types</option>
              <option value="username">Usernames</option>
              <option value="email">Emails</option>
              <option value="phone">Phones</option>
              <option value="breach">Breaches</option>
              <option value="generic">Names / Tags</option>
            </select>

            {/* LAYOUT MODE BUTTONS */}
            <div className="flex items-center rounded-xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-highest)] p-0.5">
              <button
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
          </div>

          {/* ACTION BUTTONS */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => mutate()}
              className="p-1.5 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] hover:bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface)] border border-[var(--md-sys-color-outline-variant)] text-xs cursor-pointer shadow-2xs"
              title="Refresh Graph"
            >
              <Icon icon="ph:arrows-clockwise-bold" width="15" />
            </button>
            <button
              onClick={handleExportPNG}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] hover:bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface)] border border-[var(--md-sys-color-outline-variant)] text-xs font-semibold cursor-pointer shadow-2xs"
            >
              <Icon icon="ph:download-simple-bold" width="14" />
              <span>Snapshot</span>
            </button>
          </div>
        </div>

        {/* ECHARTS CANVAS */}
        <div className="flex-1 w-full h-full relative">
          {isLoading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <Icon icon="ph:spinner-bold" className="animate-spin text-[var(--md-sys-color-primary)]" width="36" />
              <p className="text-xs font-mono text-[var(--md-sys-color-on-surface-variant)]">
                Synthesizing Graph Entities...
              </p>
            </div>
          ) : rawNodes.length === 0 ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] flex items-center justify-center text-3xl mb-3">
                🪬
              </div>
              <h3 className="text-base font-bold text-[var(--md-sys-color-on-surface)]">
                No Active Intelligence Graph
              </h3>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-sm mt-1">
                Launch a scan on the home page or open the sidebar to investigate a target and build the entity correlation graph.
              </p>
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

      {/* RIGHT SIDE INSPECTOR DRAWER */}
      {selectedNode && (
        <aside className="w-full md:w-80 lg:w-96 border-t md:border-t-0 md:border-l border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-high)] p-5 flex flex-col justify-between overflow-y-auto z-10 shadow-xl">
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--md-sys-color-outline-variant)]">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: typeColors[selectedNode.type] || "#94a3b8" }} />
                <h4 className="font-bold text-sm text-[var(--md-sys-color-on-surface)] uppercase tracking-wider">
                  Entity Inspector
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
                Label
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

            <div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--md-sys-color-on-surface-variant)] mb-1.5">
                Attributes Payload
              </div>
              <pre className="text-[11px] p-3 rounded-xl bg-[var(--md-sys-color-surface-container-lowest)] text-[var(--md-sys-color-on-surface-variant)] border border-[var(--md-sys-color-outline-variant)]/50 overflow-x-auto max-h-56 font-mono">
                {JSON.stringify(selectedNode.attributes || {}, null, 2)}
              </pre>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[var(--md-sys-color-outline-variant)]">
            <button
              onClick={() => setSelectedNode(null)}
              className="w-full py-2 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] hover:bg-[var(--md-sys-color-surface-container)] text-xs font-semibold text-[var(--md-sys-color-on-surface)] transition-colors cursor-pointer"
            >
              Close Inspector
            </button>
          </div>
        </aside>
      )}

    </div>
  );
}
