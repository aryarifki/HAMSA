"use client";

import React from "react";
import KnowledgeNetworkGraph from "@/components/graph/KnowledgeNetworkGraph";

export default function GraphPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-[var(--md-sys-color-on-surface)]">
            Knowledge Correlation Graph
          </h1>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-0.5">
            Interactive multi-entity network visualizer powered by ECharts with force-directed and circular topology.
          </p>
        </div>
      </div>

      <KnowledgeNetworkGraph />
    </div>
  );
}
