"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import Link from "next/link";
import dynamic from "next/dynamic";
import { Icon } from "@iconify/react";
import { useAppStore } from "@/store/useAppStore";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function TargetDossierPage() {
  const params = useParams();
  const router = useRouter();
  const rawId = params?.id as string;
  const decodedRawId = rawId ? decodeURIComponent(rawId) : "";

  const { theme, watchlist, activeTarget, setActiveTarget } = useAppStore();
  const isDark = theme === "dark";

  // Resolve effective target: if rawId is "torvalds" or empty, fallback to activeTarget or watchlist[0]
  const effectiveTargetId = useMemo(() => {
    if (decodedRawId && decodedRawId !== "torvalds") {
      return decodedRawId;
    }
    if (activeTarget && activeTarget !== "torvalds") {
      return activeTarget;
    }
    if (watchlist.length > 0 && watchlist[0].value) {
      return watchlist[0].value;
    }
    return decodedRawId || "torvalds";
  }, [decodedRawId, activeTarget, watchlist]);

  const targetId = effectiveTargetId;

  // View mode: "forensic" (structured table/cards) vs "graph" (network canvas)
  const [viewMode, setViewMode] = useState<"forensic" | "graph">("forensic");
  const [activeTab, setActiveTab] = useState<"breaches" | "accounts" | "contacts" | "timeline" | "raw">("accounts");
  const [accountSearch, setAccountSearch] = useState("");

  const { data: graphData, error, isLoading, mutate } = useSWR("/api/graph", fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 10000,
  });

  const nodes = useMemo(() => graphData?.nodes || [], [graphData]);
  const edges = useMemo(() => graphData?.edges || [], [graphData]);

  // Find root node matching this target
  const targetNode = useMemo(() => {
    return nodes.find(
      (n: any) =>
        (n.value && String(n.value).toLowerCase() === targetId.toLowerCase()) ||
        (n.id && String(n.id).toLowerCase() === targetId.toLowerCase()) ||
        (n.id && String(n.id).toLowerCase().includes(targetId.toLowerCase()))
    );
  }, [nodes, targetId]);

  // Find all directly and indirectly connected edges and nodes
  const { relatedNodes, relatedEdges } = useMemo(() => {
    const matchingEdges = edges.filter(
      (e: any) =>
        (targetNode && (e.source === targetNode.id || e.target === targetNode.id)) ||
        (e.source && String(e.source).toLowerCase().includes(targetId.toLowerCase())) ||
        (e.target && String(e.target).toLowerCase().includes(targetId.toLowerCase()))
    );

    const relatedIds = new Set(
      matchingEdges.flatMap((e: any) => [e.source, e.target])
    );

    const matchedNodes = nodes.filter(
      (n: any) => relatedIds.has(n.id) || (targetNode && n.id === targetNode.id)
    );

    return { relatedNodes: matchedNodes, relatedEdges: matchingEdges };
  }, [nodes, edges, targetNode, targetId]);

  // Target type detection
  const detectedType = useMemo(() => {
    if (targetNode?.type) return targetNode.type;
    if (targetId.includes("@")) return "email";
    if (/^\+?[0-9\s-]{7,16}$/.test(targetId)) return "phone";
    return "username";
  }, [targetNode, targetId]);

  // Smart default tab based on target type
  useEffect(() => {
    if (detectedType === "email") {
      setActiveTab("breaches");
    } else if (detectedType === "phone") {
      setActiveTab("contacts");
    } else {
      setActiveTab("accounts");
    }
  }, [detectedType, targetId]);

  // Classified node subsets
  const accountNodes = useMemo(
    () => relatedNodes.filter((n: any) => n.id?.startsWith("account:") || n.type === "account" || n.attributes?.platform),
    [relatedNodes]
  );

  const breachNodes = useMemo(
    () => relatedNodes.filter((n: any) => n.type === "breach" || n.id?.startsWith("breach:") || n.id?.startsWith("infostealer:") || n.attributes?.compromised_email),
    [relatedNodes]
  );

  const contactNodes = useMemo(
    () => relatedNodes.filter((n: any) => n.type === "phone" || n.id?.startsWith("phone:") || n.attributes?.carrier || n.attributes?.source === "GetContact" || n.attributes?.source === "Truecaller"),
    [relatedNodes]
  );

  // Filtered accounts based on search
  const filteredAccounts = useMemo(() => {
    if (!accountSearch.trim()) return accountNodes;
    const q = accountSearch.toLowerCase();
    return accountNodes.filter(
      (acc: any) =>
        String(acc.label || "").toLowerCase().includes(q) ||
        String(acc.value || "").toLowerCase().includes(q) ||
        String(acc.attributes?.platform || "").toLowerCase().includes(q) ||
        String(acc.attributes?.category || "").toLowerCase().includes(q)
    );
  }, [accountNodes, accountSearch]);

  // Switch target handler
  const handleSelectTarget = (newVal: string) => {
    setActiveTarget(newVal);
    router.push(`/target/${encodeURIComponent(newVal)}`);
  };

  // ECharts Graph Option for the Target Sub-Graph
  const echartsOption = useMemo(() => {
    const typeColors: Record<string, string> = {
      username: "#10B981",
      email: "#3B82F6",
      phone: "#F59E0B",
      breach: "#EF4444",
      generic: "#06B6D4",
    };

    const chartNodes = relatedNodes.map((n: any) => ({
      id: n.id,
      name: n.label || n.value,
      value: n.type,
      symbolSize: n.id === targetNode?.id ? 38 : 22,
      itemStyle: {
        color: typeColors[n.type] || "#94A3B8",
        borderColor: n.id === targetNode?.id ? "#FFB879" : "#ffffff",
        borderWidth: n.id === targetNode?.id ? 3 : 1,
      },
      label: {
        show: true,
        position: "right",
        color: isDark ? "#EBE0D9" : "#1E1A17",
        fontSize: 11,
      },
      rawNode: n,
    }));

    const chartLinks = relatedEdges.map((e: any) => ({
      source: e.source,
      target: e.target,
      label: {
        show: true,
        formatter: e.label || e.relation_type,
        fontSize: 9,
        color: isDark ? "#94a3b8" : "#64748b",
      },
      lineStyle: {
        color: isDark ? "rgba(215, 194, 180, 0.3)" : "rgba(132, 116, 106, 0.4)",
        curveness: 0.1,
        width: 1.5,
      },
    }));

    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item",
        backgroundColor: isDark ? "#211D1A" : "#EDDFD3",
        textStyle: { color: isDark ? "#EBE0D9" : "#1E1A17", fontSize: 12 },
        formatter: (params: any) => {
          if (params.dataType === "node") {
            const n = params.data.rawNode;
            return `<b>${n.label}</b><br/>Type: ${n.type}<br/>ID: ${n.id}`;
          }
          return `${params.data.source} ➔ ${params.data.target}`;
        },
      },
      series: [
        {
          type: "graph",
          layout: "force",
          force: { repulsion: 300, edgeLength: [80, 160], gravity: 0.1 },
          roam: true,
          draggable: true,
          data: chartNodes,
          links: chartLinks,
        },
      ],
    };
  }, [relatedNodes, relatedEdges, targetNode, isDark]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 animate-in fade-in duration-200">
      
      {/* TARGET SELECTOR / INVESTIGATION SWITCHER BAR */}
      <div className="p-3.5 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)]/70 flex flex-wrap items-center justify-between gap-3 shadow-2xs">
        <div className="flex items-center gap-2.5 flex-wrap">
          <span className="text-xs font-bold text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider flex items-center gap-1.5">
            <Icon icon="ph:crosshair-duotone" width="16" className="text-[var(--md-sys-color-primary)]" />
            <span>Target Roster ({watchlist.length}):</span>
          </span>

          {watchlist.length === 0 ? (
            <span className="text-xs text-[var(--md-sys-color-on-surface-variant)] italic">
              Belum ada target tersimpan di roster
            </span>
          ) : (
            <div className="flex items-center gap-1.5 flex-wrap">
              {watchlist.map((item) => {
                const isSelected = item.value.toLowerCase() === targetId.toLowerCase();
                const icon =
                  item.type === "email"
                    ? "ph:envelope-simple-bold"
                    : item.type === "phone"
                    ? "ph:phone-bold"
                    : "ph:user-bold";
                return (
                  <button
                    key={item.id}
                    onClick={() => handleSelectTarget(item.value)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                      isSelected
                        ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] font-bold shadow-xs scale-102"
                        : "bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] hover:border-[var(--md-sys-color-primary)]/50"
                    }`}
                  >
                    <Icon icon={icon} width="12" />
                    <span>{item.value}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <Link
          href="/"
          className="inline-flex items-center gap-1 px-3 py-1 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] hover:text-[var(--md-sys-color-primary)] text-xs font-bold transition-all"
        >
          <Icon icon="ph:plus-bold" width="12" />
          <span>Pindai Target Baru</span>
        </Link>
      </div>

      {/* HEADER HERO DOSSIER BANNER */}
      <div className="relative overflow-hidden rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 sm:p-7 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] flex items-center justify-center text-[var(--md-sys-color-primary)] text-2xl flex-shrink-0 shadow-sm">
              <Icon
                icon={
                  detectedType === "email"
                    ? "ph:envelope-open-duotone"
                    : detectedType === "phone"
                    ? "ph:phone-call-duotone"
                    : "ph:fingerprint-duotone"
                }
                width="32"
                height="32"
              />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-xl sm:text-2xl font-extrabold text-[var(--md-sys-color-on-surface)] tracking-tight font-mono">
                  {targetId}
                </h1>
                <span className="px-2.5 py-0.5 rounded-full bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] text-[10px] font-mono font-bold uppercase">
                  {detectedType}
                </span>
                {breachNodes.length > 0 && (
                  <span className="px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/40 text-[10px] font-mono font-bold uppercase flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
                    <span>{breachNodes.length} Kebocoran</span>
                  </span>
                )}
              </div>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-1 font-mono">
                Terhubung dengan {relatedNodes.length} entitas intelijen & {relatedEdges.length} korelasi relasional
              </p>
            </div>
          </div>

          {/* QUICK ACTIONS & VIEW MODE SWITCHER */}
          <div className="flex items-center gap-2 self-stretch sm:self-auto flex-wrap">
            {/* View Mode Switcher */}
            <div className="flex rounded-xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-highest)] p-1">
              <button
                onClick={() => setViewMode("forensic")}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  viewMode === "forensic"
                    ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-2xs"
                    : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
                }`}
                title="Tampilan Tabel & Kartu Forensik (Mudah Dibaca)"
              >
                <Icon icon="ph:table-duotone" width="15" />
                <span>Tabel & Kartu</span>
              </button>
              <button
                onClick={() => setViewMode("graph")}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  viewMode === "graph"
                    ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-2xs"
                    : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
                }`}
                title="Visualisasi Jaringan Node Graph"
              >
                <Icon icon="ph:tree-structure-duotone" width="15" />
                <span>Node Graph</span>
              </button>
            </div>

            <a
              href={`/api/report?format=html&title=Forensic%20Dossier:%20${encodeURIComponent(targetId)}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] font-bold text-xs shadow-sm hover:bg-[var(--md-sys-color-surface-container-high)] transition-all cursor-pointer"
            >
              <Icon icon="ph:file-html-bold" width="15" className="text-[var(--md-sys-color-primary)]" />
              <span>Export HTML/PDF</span>
            </a>
          </div>
        </div>

        {/* TABS HEADER */}
        {viewMode === "forensic" && (
          <div className="flex items-center gap-2 border-b border-[var(--md-sys-color-outline-variant)]/60 mt-6 pt-2 overflow-x-auto">
            {[
              { id: "breaches", label: "Kebocoran & Malware", count: breachNodes.length, icon: "ph:shield-warning-duotone" },
              { id: "accounts", label: "Akun Platform Online", count: accountNodes.length, icon: "ph:globe-duotone" },
              { id: "contacts", label: "Telekomunikasi & Kontak", count: contactNodes.length, icon: "ph:phone-call-duotone" },
              { id: "timeline", label: "Korelasi Relasi", count: relatedEdges.length, icon: "ph:git-fork-duotone" },
              { id: "raw", label: "Payload JSON", count: null, icon: "ph:code-duotone" },
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
                  <span className={`px-1.5 py-0.2 rounded-md text-[10px] font-mono ${
                    tab.id === "breaches" && breachNodes.length > 0
                      ? "bg-rose-500/20 text-rose-400 font-bold"
                      : "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)]"
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* VIEW MODE 1: VISUAL NODE GRAPH (WHEN TOGGLED) */}
      {viewMode === "graph" && (
        <div className="p-4 rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] space-y-3">
          <div className="flex items-center justify-between border-b border-[var(--md-sys-color-outline-variant)]/60 pb-3">
            <div>
              <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)] flex items-center gap-2">
                <Icon icon="ph:tree-structure-duotone" width="18" className="text-[var(--md-sys-color-primary)]" />
                <span>Topologi Relasi Langsung untuk: {targetId}</span>
              </h3>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)]">
                {relatedNodes.length} entitas terhubung melalui {relatedEdges.length} relasi langsung.
              </p>
            </div>
            <Link
              href="/graph"
              className="px-3 py-1.5 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-xs font-bold text-[var(--md-sys-color-primary)] hover:underline inline-flex items-center gap-1"
            >
              <span>Buka Layar Penuh Graph Global</span>
              <Icon icon="ph:arrow-square-out-bold" width="12" />
            </Link>
          </div>

          <div className="w-full h-[520px] rounded-2xl bg-[var(--md-sys-color-surface-container-lowest)] overflow-hidden">
            {relatedNodes.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-[var(--md-sys-color-on-surface-variant)] font-mono">
                Belum ada node relasi dalam graph untuk target ini.
              </div>
            ) : (
              <ReactECharts option={echartsOption} style={{ height: "100%", width: "100%" }} />
            )}
          </div>
        </div>
      )}

      {/* VIEW MODE 2: FORENSIC TABLES & CARDS (DEFAULT & EASY TO READ) */}
      {viewMode === "forensic" && (
        <div className="space-y-6">

          {/* TAB: BREACHES & MALWARE */}
          {activeTab === "breaches" && (
            <div className="space-y-4 animate-in fade-in duration-150">
              {/* THREAT ASSESSMENT CARD */}
              <div className={`p-5 rounded-3xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
                breachNodes.length > 0
                  ? "bg-rose-500/10 border-rose-500/30 text-rose-400"
                  : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              }`}>
                <div className="flex items-center gap-3.5">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0 ${
                    breachNodes.length > 0 ? "bg-rose-500/20 text-rose-400" : "bg-emerald-500/20 text-emerald-400"
                  }`}>
                    <Icon icon={breachNodes.length > 0 ? "ph:shield-warning-duotone" : "ph:shield-check-duotone"} width="28" />
                  </div>
                  <div>
                    <h3 className="font-extrabold text-base text-[var(--md-sys-color-on-surface)]">
                      {breachNodes.length > 0
                        ? `Peringatan: Ditemukan ${breachNodes.length} Insiden Kebocoran / Infeksi!`
                        : "Perimeter Aman: Tidak Ada Kebocoran Data Ditemukan"}
                    </h3>
                    <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-0.5 max-w-xl">
                      {breachNodes.length > 0
                        ? "Kredensial atau alamat email ini terdeteksi pada kebocoran data publik (XposedOrNot) atau infeksi malware infostealer (Hudson Rock). Lakukan reset kata sandi segera."
                        : "Alamat atau identitas ini tidak ditemukan pada basis data kebocoran data terindeks maupun log infostealer."}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1.5 rounded-xl font-mono text-xs font-bold uppercase tracking-wider ${
                    breachNodes.length > 0 ? "bg-rose-500/20 text-rose-300 border border-rose-500/40" : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                  }`}>
                    {breachNodes.length > 0 ? "HIGH RISK EXPOSURE" : "CLEAN PERIMETER"}
                  </span>
                </div>
              </div>

              {/* BREACH INCIDENTS TABLE / CARDS */}
              {breachNodes.length === 0 ? (
                <div className="p-10 rounded-3xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center space-y-2">
                  <Icon icon="ph:check-circle-duotone" className="mx-auto text-emerald-500" width="36" />
                  <p className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
                    Tidak ada kebocoran data untuk &quot;{targetId}&quot;
                  </p>
                  <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-md mx-auto">
                    Kredensial belum pernah terkompromi dalam pangkalan data publik yang terindeks.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {breachNodes.map((b: any) => {
                    const isInfostealer = b.id?.startsWith("infostealer:") || b.attributes?.operating_system;
                    return (
                      <div
                        key={b.id}
                        className="p-5 rounded-2xl border border-rose-500/30 bg-[var(--md-sys-color-surface-container)] hover:bg-[var(--md-sys-color-surface-container-high)] transition-all flex flex-col justify-between space-y-3 shadow-2xs"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-rose-500/20 text-rose-500 flex items-center justify-center flex-shrink-0">
                              <Icon icon={isInfostealer ? "ph:laptop-duotone" : "ph:database-duotone"} width="22" />
                            </div>
                            <div>
                              <h4 className="font-bold text-sm text-[var(--md-sys-color-on-surface)]">
                                {b.attributes?.breach_title || b.label}
                              </h4>
                              <span className="text-[10px] font-mono text-rose-400">
                                {isInfostealer ? "Infostealer Malware Log" : `Domain Leak: ${b.attributes?.domain || "Public Breach"}`}
                              </span>
                            </div>
                          </div>
                          <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 text-[10px] font-mono font-bold uppercase">
                            {isInfostealer ? "Malware" : "Breach"}
                          </span>
                        </div>

                        {/* INFOSTEALER DETAILS (IF APPLICABLE) */}
                        {isInfostealer ? (
                          <div className="p-3 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] space-y-1.5 text-xs font-mono">
                            {b.attributes?.computer_name && (
                              <div className="flex justify-between text-[11px]">
                                <span className="text-[var(--md-sys-color-on-surface-variant)]">Komputer Korban:</span>
                                <span className="text-[var(--md-sys-color-on-surface)] font-bold">{b.attributes.computer_name}</span>
                              </div>
                            )}
                            {b.attributes?.operating_system && (
                              <div className="flex justify-between text-[11px]">
                                <span className="text-[var(--md-sys-color-on-surface-variant)]">Sistem Operasi:</span>
                                <span className="text-[var(--md-sys-color-on-surface)] font-bold">{b.attributes.operating_system}</span>
                              </div>
                            )}
                            {b.attributes?.antivirus && Array.isArray(b.attributes.antivirus) && b.attributes.antivirus.length > 0 && (
                              <div className="flex justify-between text-[11px]">
                                <span className="text-[var(--md-sys-color-on-surface-variant)]">Antivirus:</span>
                                <span className="text-[var(--md-sys-color-on-surface)]">{b.attributes.antivirus.join(", ")}</span>
                              </div>
                            )}
                            {b.attributes?.infection_date && (
                              <div className="flex justify-between text-[11px]">
                                <span className="text-[var(--md-sys-color-on-surface-variant)]">Tanggal Infeksi:</span>
                                <span className="text-rose-400 font-bold">{String(b.attributes.infection_date).slice(0, 10)}</span>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="p-3 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] space-y-1 text-xs text-[var(--md-sys-color-on-surface-variant)]">
                            <p className="text-[11px]">
                              Insiden kebocoran kredensial tercatat pada pangkalan data XposedOrNot. Kata sandi akun yang terasosiasi kemungkinan telah beredar.
                            </p>
                          </div>
                        )}

                        <div className="flex items-center justify-between text-xs pt-2 border-t border-[var(--md-sys-color-outline-variant)]/40">
                          <span className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] font-mono">
                            Sumber: {b.source_plugin || "Threat Intel"}
                          </span>
                          <span className="text-[11px] font-bold text-rose-400">
                            Tindakan: Reset Password
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB: ONLINE ACCOUNTS */}
          {activeTab === "accounts" && (
            <div className="space-y-4 animate-in fade-in duration-150">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
                    Akun & Profil Online Terverifikasi ({accountNodes.length})
                  </h3>
                  <p className="text-xs text-[var(--md-sys-color-on-surface-variant)]">
                    Daftar platform tempat username atau email ini terdaftar.
                  </p>
                </div>

                <div className="relative w-full sm:w-64">
                  <Icon icon="ph:magnifying-glass-duotone" className="absolute left-3 top-2.5 text-[var(--md-sys-color-on-surface-variant)]" width="15" />
                  <input
                    type="text"
                    placeholder="Cari platform atau kategori..."
                    value={accountSearch}
                    onChange={(e) => setAccountSearch(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] outline-none focus:border-[var(--md-sys-color-primary)] font-medium"
                  />
                </div>
              </div>

              {filteredAccounts.length === 0 ? (
                <div className="p-10 rounded-3xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center space-y-2">
                  <Icon icon="ph:globe-duotone" className="mx-auto text-[var(--md-sys-color-on-surface-variant)]" width="36" />
                  <p className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
                    Tidak ada akun platform yang cocok
                  </p>
                  <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-sm mx-auto">
                    {accountNodes.length === 0
                      ? "Tidak ada akun online yang terdeteksi untuk entitas ini. Jalankan pemindaian dengan opsi 690+ situs untuk cakupan lebih luas."
                      : "Pencarian Anda tidak cocok dengan akun yang ditemukan."}
                  </p>
                </div>
              ) : (
                <div className="rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] overflow-hidden shadow-2xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface-variant)] font-mono uppercase text-[10px]">
                          <th className="py-3 px-4 font-bold">Platform</th>
                          <th className="py-3 px-4 font-bold">Kategori</th>
                          <th className="py-3 px-4 font-bold">URL Profil Terdeteksi</th>
                          <th className="py-3 px-4 font-bold text-center">Status</th>
                          <th className="py-3 px-4 font-bold text-right">Aksi</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--md-sys-color-outline-variant)]/50">
                        {filteredAccounts.map((acc: any) => {
                          const url = acc.attributes?.profile_url || (acc.value && String(acc.value).startsWith("http") ? acc.value : null);
                          const platform = acc.attributes?.platform || acc.label?.replace(/^account:[^:]*:/, "") || acc.value;
                          const category = acc.attributes?.category || "Profile";
                          return (
                            <tr key={acc.id} className="hover:bg-[var(--md-sys-color-surface-container-high)] transition-colors">
                              <td className="py-3 px-4 font-bold text-[var(--md-sys-color-on-surface)] flex items-center gap-2">
                                <Icon icon="ph:browser-duotone" width="16" className="text-sky-500 flex-shrink-0" />
                                <span>{platform}</span>
                              </td>
                              <td className="py-3 px-4 font-mono text-[11px]">
                                <span className="px-2 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] uppercase text-[10px]">
                                  {category}
                                </span>
                              </td>
                              <td className="py-3 px-4 font-mono text-sky-500 truncate max-w-xs">
                                {url ? (
                                  <a href={url} target="_blank" rel="noopener noreferrer" className="hover:underline truncate block">
                                    {url}
                                  </a>
                                ) : (
                                  <span className="text-[var(--md-sys-color-on-surface-variant)]">{acc.value}</span>
                                )}
                              </td>
                              <td className="py-3 px-4 text-center font-mono">
                                <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-bold text-[10px]">
                                  Terdaftar (200)
                                </span>
                              </td>
                              <td className="py-3 px-4 text-right">
                                {url && (
                                  <a
                                    href={url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-1.5 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] text-sky-500 hover:opacity-80 inline-flex items-center gap-1 text-[11px] font-bold"
                                  >
                                    <Icon icon="ph:arrow-square-out-bold" width="13" />
                                    <span>Buka</span>
                                  </a>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB: CONTACTS & PHONE */}
          {activeTab === "contacts" && (
            <div className="space-y-4 animate-in fade-in duration-150">
              <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
                Intelijen Telekomunikasi & Kontak ({contactNodes.length})
              </h3>

              {contactNodes.length === 0 ? (
                <div className="p-10 rounded-3xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center space-y-2">
                  <Icon icon="ph:phone-slash-duotone" className="mx-auto text-[var(--md-sys-color-on-surface-variant)]" width="36" />
                  <p className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
                    Tidak ada nomor telepon terkait
                  </p>
                  <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-sm mx-auto">
                    Pindai nomor telepon dari beranda untuk memetakan operator seluler dan tag kontak.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {contactNodes.map((c: any) => (
                    <div
                      key={c.id}
                      className="p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5 space-y-3 flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-500 flex items-center justify-center">
                            <Icon icon="ph:phone-call-duotone" width="22" />
                          </div>
                          <div>
                            <span className="font-bold text-sm text-[var(--md-sys-color-on-surface)] font-mono">
                              {c.label || c.value}
                            </span>
                            <div className="text-[10px] font-mono text-[var(--md-sys-color-primary)]">
                              {c.attributes?.line_type || "Mobile Line"}
                            </div>
                          </div>
                        </div>
                        <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-mono text-[10px] uppercase font-bold">
                          {c.attributes?.country || "ID"}
                        </span>
                      </div>

                      {c.attributes?.carrier && (
                        <div className="p-3 rounded-xl bg-[var(--md-sys-color-surface-container)] text-xs flex justify-between">
                          <span className="text-[var(--md-sys-color-on-surface-variant)]">Operator Seluler:</span>
                          <b className="text-[var(--md-sys-color-on-surface)]">{c.attributes.carrier}</b>
                        </div>
                      )}

                      <div className="flex items-center gap-2 pt-1">
                        {c.attributes?.whatsapp_link && (
                          <a
                            href={c.attributes.whatsapp_link}
                            target="_blank"
                            rel="noreferrer"
                            className="flex-1 py-1.5 rounded-xl bg-emerald-600 text-white text-xs font-bold inline-flex items-center justify-center gap-1.5 shadow-sm hover:opacity-90"
                          >
                            <Icon icon="ph:whatsapp-logo-bold" width="14" />
                            <span>WhatsApp</span>
                          </a>
                        )}
                        {c.attributes?.telegram_link && (
                          <a
                            href={c.attributes.telegram_link}
                            target="_blank"
                            rel="noreferrer"
                            className="flex-1 py-1.5 rounded-xl bg-sky-600 text-white text-xs font-bold inline-flex items-center justify-center gap-1.5 shadow-sm hover:opacity-90"
                          >
                            <Icon icon="ph:arrow-square-out-bold" width="14" />
                            <span>Telegram</span>
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB: TIMELINE & RELATIONS LIST (EASY TO READ WITHOUT GRAPH) */}
          {activeTab === "timeline" && (
            <div className="space-y-4 animate-in fade-in duration-150">
              <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
                Daftar Hubungan & Korelasi Relasional ({relatedEdges.length})
              </h3>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)]">
                Berikut adalah penjelasan hubungan langsung antar entitas tanpa harus membaca garis graph.
              </p>

              {relatedEdges.length === 0 ? (
                <div className="p-8 rounded-2xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center text-xs text-[var(--md-sys-color-on-surface-variant)]">
                  Belum ada relasi yang terhubung ke target ini.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {relatedEdges.map((e: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-2xl border border-[var(--md-sys-color-outline-variant)]/60 bg-[var(--md-sys-color-surface-container)] flex items-center justify-between text-xs font-mono"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] flex items-center justify-center text-[10px] font-bold">
                          {idx + 1}
                        </span>
                        <span className="text-[var(--md-sys-color-on-surface)] font-bold">{e.source}</span>
                        <Icon icon="ph:arrow-right-bold" className="text-[var(--md-sys-color-primary)]" width="14" />
                        <span className="text-sky-400 font-bold">{e.target}</span>
                      </div>
                      <span className="px-2.5 py-0.5 rounded-full bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] text-[10px] uppercase font-bold">
                        {e.label || e.relation_type}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB: RAW JSON */}
          {activeTab === "raw" && (
            <div className="p-5 rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] space-y-2">
              <h3 className="text-xs font-mono font-bold uppercase text-[var(--md-sys-color-primary)]">
                Payload Entitas & Relasi
              </h3>
              <pre className="text-xs p-4 rounded-xl bg-[var(--md-sys-color-surface-container-lowest)] text-[var(--md-sys-color-on-surface-variant)] overflow-x-auto font-mono max-h-96">
                {JSON.stringify({ targetNode, relatedNodes, relatedEdges }, null, 2)}
              </pre>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
