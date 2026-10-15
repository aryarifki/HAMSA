"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import Link from "next/link";
import { Icon } from "@iconify/react";
import { useAppStore } from "@/store/useAppStore";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function TargetDossierPage() {
  const params = useParams();
  const rawId = params?.id as string;
  const targetId = decodeURIComponent(rawId || "torvalds");
  const { theme } = useAppStore();

  const [activeTab, setActiveTab] = useState<"accounts" | "breaches" | "contacts" | "raw">("accounts");

  const { data: graphData, error, isLoading } = useSWR("/api/graph", fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 15000,
  });

  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];

  // Find nodes relevant to this target
  const targetNode = nodes.find(
    (n: any) =>
      n.value.toLowerCase() === targetId.toLowerCase() ||
      n.id.toLowerCase().includes(targetId.toLowerCase())
  );

  const relatedEdges = edges.filter(
    (e: any) =>
      (targetNode && (e.source === targetNode.id || e.target === targetNode.id)) ||
      e.source.includes(targetId) ||
      e.target.includes(targetId)
  );

  const relatedNodeIds = new Set(
    relatedEdges.flatMap((e: any) => [e.source, e.target])
  );

  const relatedNodes = nodes.filter((n: any) => relatedNodeIds.has(n.id) || (targetNode && n.id === targetNode.id));

  const accountNodes = relatedNodes.filter((n: any) => n.type === "username" || n.type === "account" || n.attributes?.platform);
  const breachNodes = relatedNodes.filter((n: any) => n.type === "breach" || n.attributes?.compromised_email);
  const contactNodes = relatedNodes.filter((n: any) => n.type === "phone" || n.attributes?.carrier || n.attributes?.source === "GetContact" || n.attributes?.source === "Truecaller");

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 animate-in fade-in duration-200">
      
      {/* HEADER BANNER */}
      <div className="relative overflow-hidden rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 sm:p-7 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] flex items-center justify-center text-[var(--md-sys-color-primary)] text-2xl flex-shrink-0 shadow-sm">
              <Icon icon="ph:fingerprint-duotone" width="32" height="32" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-extrabold text-[var(--md-sys-color-on-surface)] tracking-tight">
                  {targetId}
                </h1>
                <span className="px-2 py-0.5 rounded-full bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] text-[10px] font-mono font-bold uppercase">
                  {targetNode?.type || "TARGET"}
                </span>
              </div>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-1 font-mono">
                Correlated Across {relatedNodes.length} Graph Entities & {relatedEdges.length} Relations
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-stretch sm:self-auto">
            <a
              href={`/api/report?format=html&title=Forensic%20Report:%20${encodeURIComponent(targetId)}`}
              target="_blank"
              rel="noreferrer"
              className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] font-bold text-xs shadow-sm hover:bg-[var(--md-sys-color-surface-container-high)] transition-all cursor-pointer"
            >
              <Icon icon="ph:file-html-bold" width="15" className="text-[var(--md-sys-color-primary)]" />
              <span>Export Dossier</span>
            </a>
            <Link
              href="/graph"
              className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] font-bold text-xs shadow-md hover:opacity-90 transition-all cursor-pointer"
            >
              <Icon icon="ph:tree-structure-bold" width="15" />
              <span>View in Graph</span>
            </Link>
          </div>
        </div>

        {/* TABS HEADER */}
        <div className="flex items-center gap-2 border-b border-[var(--md-sys-color-outline-variant)]/60 mt-6 pt-2 overflow-x-auto">
          {[
            { id: "accounts", label: "Discovered Accounts", count: accountNodes.length, icon: "ph:globe-duotone" },
            { id: "breaches", label: "Breaches & Malware", count: breachNodes.length, icon: "ph:shield-warning-duotone" },
            { id: "contacts", label: "Phone & Contacts", count: contactNodes.length, icon: "ph:phone-call-duotone" },
            { id: "raw", label: "Raw Metadata", count: null, icon: "ph:code-duotone" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 text-xs font-bold transition-all border-b-2 cursor-pointer whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-[var(--md-sys-color-primary)] text-[var(--md-sys-color-primary)] font-extrabold"
                  : "border-transparent text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
              }`}
            >
              <Icon icon={tab.icon} width="16" />
              <span>{tab.label}</span>
              {tab.count !== null && (
                <span className="px-1.5 py-0.2 rounded-md bg-[var(--md-sys-color-surface-container-highest)] text-[10px] font-mono">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* TAB 1: DISCOVERED ACCOUNTS */}
      {activeTab === "accounts" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
              Discovered Online Accounts ({accountNodes.length})
            </h3>
          </div>

          {accountNodes.length === 0 ? (
            <div className="p-8 rounded-2xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center text-xs text-[var(--md-sys-color-on-surface-variant)]">
              No platform accounts recorded for this entity yet. Run a scan with `--all-sites` to expand hunting.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {accountNodes.map((acc: any) => (
                <div
                  key={acc.id}
                  className="p-4 rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] hover:bg-[var(--md-sys-color-surface-container-high)] transition-all flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-[var(--md-sys-color-on-surface)]">
                      {acc.attributes?.platform || acc.label}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] uppercase">
                      {acc.attributes?.category || "Profile"}
                    </span>
                  </div>

                  {acc.attributes?.profile_url && (
                    <a
                      href={acc.attributes.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-3 text-xs text-sky-500 hover:underline truncate inline-flex items-center gap-1 font-mono"
                    >
                      <Icon icon="ph:arrow-square-out-bold" width="13" />
                      <span>{acc.attributes.profile_url}</span>
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: BREACHES & MALWARE */}
      {activeTab === "breaches" && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
            Breach Exposures & Malware Logs ({breachNodes.length})
          </h3>

          {breachNodes.length === 0 ? (
            <div className="p-8 rounded-2xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center text-xs text-[var(--color-positive)] font-bold">
              ✓ No public breach exposures or infostealer malware logs found for this identity!
            </div>
          ) : (
            <div className="space-y-3">
              {breachNodes.map((b: any) => (
                <div
                  key={b.id}
                  className="p-4 rounded-2xl border border-rose-500/30 bg-rose-500/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-rose-500/20 text-rose-500 flex items-center justify-center flex-shrink-0">
                      <Icon icon="ph:warning-octagon-duotone" width="22" />
                    </div>
                    <div>
                      <div className="font-bold text-sm text-[var(--md-sys-color-on-surface)]">
                        {b.label}
                      </div>
                      <div className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-0.5">
                        Domain: {b.attributes?.domain || "Public Leak"} | Date: {b.attributes?.breached_date || "Recorded"}
                      </div>
                    </div>
                  </div>

                  {b.attributes?.infected_path && (
                    <div className="text-[11px] font-mono px-3 py-1 rounded bg-[var(--md-sys-color-surface-container-highest)] text-rose-400">
                      Infostealer Path: {b.attributes.infected_path}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CONTACTS & PHONE */}
      {activeTab === "contacts" && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
            Phone Metadata & Crowd-Sourced Contact Tags ({contactNodes.length})
          </h3>

          {contactNodes.length === 0 ? (
            <div className="p-8 rounded-2xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center text-xs text-[var(--md-sys-color-on-surface-variant)]">
              No telephone records or contact tags attached to this entity.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {contactNodes.map((c: any) => (
                <div
                  key={c.id}
                  className="p-4 rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-[var(--md-sys-color-on-surface)]">
                      {c.label}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)]">
                      {c.attributes?.source || "Telecom"}
                    </span>
                  </div>
                  {c.attributes?.carrier && (
                    <p className="text-xs text-[var(--md-sys-color-on-surface-variant)]">
                      Operator: <b className="text-[var(--md-sys-color-on-surface)]">{c.attributes.carrier}</b> ({c.attributes.country || "ID"})
                    </p>
                  )}
                  {c.attributes?.tag && (
                    <div className="text-xs p-2 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] font-mono text-[var(--md-sys-color-primary)]">
                      Tag: &quot;{c.attributes.tag}&quot;
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: RAW METADATA */}
      {activeTab === "raw" && (
        <div className="p-5 rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] space-y-2">
          <h3 className="text-xs font-mono font-bold uppercase text-[var(--md-sys-color-primary)]">
            Correlated Node & Edge Payload
          </h3>
          <pre className="text-xs p-4 rounded-xl bg-[var(--md-sys-color-surface-container-lowest)] text-[var(--md-sys-color-on-surface-variant)] overflow-x-auto font-mono max-h-96">
            {JSON.stringify({ targetNode, relatedNodes, relatedEdges }, null, 2)}
          </pre>
        </div>
      )}

    </div>
  );
}
