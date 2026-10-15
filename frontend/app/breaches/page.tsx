"use client";

import React from "react";
import useSWR from "swr";
import Link from "next/link";
import { Icon } from "@iconify/react";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function BreachesPage() {
  const { data: graphData, isLoading } = useSWR("/api/graph", fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 15000,
  });

  const nodes = graphData?.nodes || [];
  const breachNodes = nodes.filter(
    (n: any) => n.type === "breach" || n.attributes?.domain || n.attributes?.infected_path
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 animate-in fade-in duration-200">
      
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Icon icon="ph:shield-warning-duotone" width="24" className="text-rose-500" />
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-[var(--md-sys-color-on-surface)]">
              Breach & Threat Intelligence Radar
            </h1>
          </div>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-1">
            Aggregates live incident feeds from XposedOrNot and HudsonRock infostealer compromised machine logs.
          </p>
        </div>

        <div className="px-3.5 py-1.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-500 text-xs font-mono font-bold">
          {breachNodes.length} Incident(s) Detected
        </div>
      </div>

      {/* TABLE / CARD LIST */}
      {isLoading ? (
        <div className="p-12 text-center text-xs font-mono text-[var(--md-sys-color-on-surface-variant)] flex items-center justify-center gap-2">
          <Icon icon="ph:spinner-bold" className="animate-spin text-[var(--md-sys-color-primary)]" width="18" />
          <span>Querying Threat Database...</span>
        </div>
      ) : breachNodes.length === 0 ? (
        <div className="p-12 rounded-3xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-500 flex items-center justify-center mx-auto text-xl">
            ✓
          </div>
          <h3 className="text-base font-bold text-[var(--md-sys-color-on-surface)]">
            Perimeter Secure: Zero Breach Exposure
          </h3>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-md mx-auto">
            None of the currently tracked email addresses or credentials appear in indexed threat dumps or infostealer malware logs.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {breachNodes.map((b: any) => (
            <div
              key={b.id}
              className="p-5 rounded-2xl border border-rose-500/30 bg-[var(--md-sys-color-surface-container)] hover:bg-[var(--md-sys-color-surface-container-high)] transition-all flex flex-col justify-between space-y-3 shadow-2xs"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-rose-500/20 text-rose-500 flex items-center justify-center flex-shrink-0">
                    <Icon icon="ph:shield-warning-bold" width="18" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-[var(--md-sys-color-on-surface)]">
                      {b.label}
                    </h4>
                    <span className="text-[10px] font-mono text-rose-400">
                      Domain: {b.attributes?.domain || "Public Leak"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-1.5 text-xs text-[var(--md-sys-color-on-surface-variant)] border-t border-[var(--md-sys-color-outline-variant)]/40 pt-3">
                {b.attributes?.breached_date && (
                  <div className="flex justify-between">
                    <span>Incident Date:</span>
                    <b className="font-mono text-[var(--md-sys-color-on-surface)]">{b.attributes.breached_date}</b>
                  </div>
                )}
                {b.attributes?.infected_path && (
                  <div className="flex flex-col gap-0.5">
                    <span>Infected System:</span>
                    <span className="font-mono text-[10px] text-rose-400 truncate bg-[var(--md-sys-color-surface-container-highest)] p-1 rounded">
                      {b.attributes.infected_path}
                    </span>
                  </div>
                )}
              </div>

              <div className="pt-1 flex justify-end">
                <Link
                  href={`/target/${encodeURIComponent(b.value || b.label)}`}
                  className="text-xs font-bold text-[var(--md-sys-color-primary)] hover:underline inline-flex items-center gap-1"
                >
                  <span>Investigate Identity</span>
                  <Icon icon="ph:arrow-right-bold" width="11" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}
