"use client";

import React, { useState } from "react";
import useSWR from "swr";
import { Icon } from "@iconify/react";
import TargetCard from "@/components/home/TargetCard";
import { useAppStore, TargetItem } from "@/store/useAppStore";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function HomePage() {
  const {
    watchlist,
    addWatchlistTarget,
    removeWatchlistTarget,
    setActiveTarget,
    depth,
    allSites,
    proxy,
    getcontactToken,
    truecallerToken,
    setCacheLoading,
  } = useAppStore();

  const [inputTarget, setInputTarget] = useState("");
  const [selectedType, setSelectedType] = useState<"username" | "email" | "phone">("username");
  const [isScanning, setIsScanning] = useState(false);

  // System status and stats
  const { data: graphData, mutate: mutateGraph } = useSWR("/api/graph", fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 15000,
  });

  const totalEntities = graphData?.summary?.total_entities || 0;
  const totalRelations = graphData?.summary?.total_relations || 0;

  const handleLaunchScan = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanTarget = inputTarget.trim();
    if (!cleanTarget) return;

    setIsScanning(true);
    setCacheLoading({
      isOpen: true,
      title: "Executing Intelligence Pipeline",
      step: `Dispatching plugins for '${cleanTarget}' (${selectedType})...`,
      detail: `Depth: Round ${depth} | 690+ WMN: ${allSites ? "Enabled" : "Capped 50"}`,
      progress: 20,
      isSuccess: false,
    });

    try {
      const payload: Record<string, any> = {
        depth: depth,
        all_sites: allSites,
        getcontact_token: getcontactToken,
        truecaller_token: truecallerToken,
        proxy: proxy,
      };
      if (selectedType === "username") payload.username = cleanTarget;
      if (selectedType === "email") payload.email = cleanTarget;
      if (selectedType === "phone") payload.phone = cleanTarget;

      const resp = await fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const res = await resp.json();

      // Count breaches and accounts for the card
      const nodes = res.nodes || [];
      const breachCount = nodes.filter((n: any) => n.type === "breach").length;
      const accountCount = nodes.filter((n: any) => n.type === "username" || n.type === "account").length;

      const newItem: TargetItem = {
        id: `${selectedType}:${cleanTarget.toLowerCase()}`,
        value: cleanTarget,
        type: selectedType,
        label: cleanTarget,
        addedAt: new Date().toISOString(),
        riskLevel: breachCount > 0 ? "high" : "clean",
        accountsFound: accountCount,
        breachesFound: breachCount,
      };

      addWatchlistTarget(newItem);
      setActiveTarget(cleanTarget, selectedType);
      mutateGraph();

      setCacheLoading({
        isOpen: true,
        title: "Reconnaissance Complete!",
        step: `Discovered ${res.summary?.total_entities || nodes.length} entities and ${res.summary?.total_relations || 0} relations.`,
        detail: "Synthesized into Knowledge Graph",
        progress: 100,
        isSuccess: true,
      });

      setInputTarget("");
      setTimeout(() => setCacheLoading(false), 1200);
    } catch (err) {
      setCacheLoading({
        isOpen: true,
        title: "Scan Interrupted",
        step: `Error communicating with scan gateway: ${err}`,
        progress: 100,
        isSuccess: false,
      });
      setTimeout(() => setCacheLoading(false), 2000);
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-8 animate-in fade-in duration-300">
      
      {/* HERO LAUNCHER BAR */}
      <div className="relative overflow-hidden rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 sm:p-8 shadow-xl">
        <div className="absolute inset-0 bg-terminal-grid opacity-20 pointer-events-none" />
        <div className="absolute -top-24 -right-24 w-60 h-60 rounded-full bg-[var(--md-sys-color-primary)]/15 blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-xs font-mono font-bold text-[var(--md-sys-color-primary)]">
            <span className="w-2 h-2 rounded-full bg-[var(--md-sys-color-primary)] animate-ping" />
            <span>HAMSA AUTONOMOUS RECON SYSTEM</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-[var(--md-sys-color-on-surface)]">
            Investigate Any Digital Identity
          </h1>

          <p className="text-xs sm:text-sm text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            Correlate 690+ community platform accounts, public data breach dumps, infostealer malware logs, and crowd-sourced phone contact tags into an interactive knowledge graph.
          </p>

          {/* SEARCH & INPUT FORM */}
          <form onSubmit={handleLaunchScan} className="pt-2 flex flex-col sm:flex-row gap-2.5">
            {/* TYPE SELECTOR */}
            <div className="flex rounded-xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-highest)] p-1">
              {(["username", "email", "phone"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setSelectedType(t)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold capitalize transition-all cursor-pointer ${
                    selectedType === t
                      ? "bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] shadow-2xs"
                      : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* INPUT FIELD */}
            <div className="relative flex-1">
              <input
                type="text"
                required
                value={inputTarget}
                onChange={(e) => setInputTarget(e.target.value)}
                placeholder={
                  selectedType === "username"
                    ? "Enter target username (e.g. torvalds)..."
                    : selectedType === "email"
                    ? "Enter target email address (e.g. victim@domain.com)..."
                    : "Enter target phone number (e.g. +628123456789 or 08123456789)..."
                }
                className="w-full px-4 py-2.5 text-xs sm:text-sm rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] outline-none focus:border-[var(--md-sys-color-primary)] font-medium transition-all shadow-inner"
              />
            </div>

            {/* SUBMIT BUTTON */}
            <button
              type="submit"
              disabled={isScanning}
              className="px-6 py-2.5 rounded-xl bg-[var(--md-sys-color-primary)] hover:opacity-90 text-[var(--md-sys-color-on-primary)] font-bold text-xs sm:text-sm tracking-wide shadow-md transition-all cursor-pointer flex items-center justify-center gap-2 flex-shrink-0 disabled:opacity-50"
            >
              {isScanning ? (
                <>
                  <Icon icon="ph:spinner-bold" className="animate-spin" width="16" />
                  <span>Hunting...</span>
                </>
              ) : (
                <>
                  <Icon icon="ph:lightning-bold" width="16" />
                  <span>Launch Recon</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* QUICK STATS METRICS */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4.5 rounded-2xl border border-[var(--md-sys-color-outline-variant)]/70 bg-[var(--md-sys-color-surface-container)] flex items-center gap-3.5 shadow-2xs">
          <div className="w-10 h-10 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] flex items-center justify-center">
            <Icon icon="ph:tree-structure-duotone" width="22" />
          </div>
          <div>
            <div className="text-[11px] font-semibold text-[var(--md-sys-color-on-surface-variant)] uppercase">
              Entities In Graph
            </div>
            <div className="text-xl font-extrabold font-mono text-[var(--md-sys-color-on-surface)]">
              {totalEntities}
            </div>
          </div>
        </div>

        <div className="p-4.5 rounded-2xl border border-[var(--md-sys-color-outline-variant)]/70 bg-[var(--md-sys-color-surface-container)] flex items-center gap-3.5 shadow-2xs">
          <div className="w-10 h-10 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] text-sky-500 flex items-center justify-center">
            <Icon icon="ph:arrows-split-duotone" width="22" />
          </div>
          <div>
            <div className="text-[11px] font-semibold text-[var(--md-sys-color-on-surface-variant)] uppercase">
              Correlations
            </div>
            <div className="text-xl font-extrabold font-mono text-[var(--md-sys-color-on-surface)]">
              {totalRelations}
            </div>
          </div>
        </div>

        <div className="p-4.5 rounded-2xl border border-[var(--md-sys-color-outline-variant)]/70 bg-[var(--md-sys-color-surface-container)] flex items-center gap-3.5 shadow-2xs">
          <div className="w-10 h-10 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] text-amber-500 flex items-center justify-center">
            <Icon icon="ph:globe-stand-duotone" width="22" />
          </div>
          <div>
            <div className="text-[11px] font-semibold text-[var(--md-sys-color-on-surface-variant)] uppercase">
              Platforms Pool
            </div>
            <div className="text-xl font-extrabold font-mono text-[var(--md-sys-color-on-surface)]">
              692+
            </div>
          </div>
        </div>

        <div className="p-4.5 rounded-2xl border border-[var(--md-sys-color-outline-variant)]/70 bg-[var(--md-sys-color-surface-container)] flex items-center gap-3.5 shadow-2xs">
          <div className="w-10 h-10 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] text-emerald-500 flex items-center justify-center">
            <Icon icon="ph:cpu-duotone" width="22" />
          </div>
          <div>
            <div className="text-[11px] font-semibold text-[var(--md-sys-color-on-surface-variant)] uppercase">
              Autonomous Brain
            </div>
            <div className="text-xl font-extrabold font-mono text-emerald-500">
              Active
            </div>
          </div>
        </div>
      </div>

      {/* TARGET ROSTER CARDS */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon icon="ph:identification-badge-duotone" width="20" className="text-[var(--md-sys-color-primary)]" />
            <h2 className="text-lg font-bold tracking-tight text-[var(--md-sys-color-on-surface)]">
              Active Target Roster
            </h2>
          </div>
          <span className="text-xs text-[var(--md-sys-color-on-surface-variant)] font-mono">
            {watchlist.length} Target(s) Tracked
          </span>
        </div>

        {watchlist.length === 0 ? (
          <div className="p-10 rounded-3xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center space-y-2">
            <Icon icon="ph:magnifying-glass-duotone" className="mx-auto text-[var(--md-sys-color-on-surface-variant)]" width="32" />
            <p className="text-sm font-semibold text-[var(--md-sys-color-on-surface)]">
              No targets in your roster yet
            </p>
            <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-sm mx-auto">
              Enter a username, email, or phone number above to start building your investigative intelligence graph.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4.5">
            {watchlist.map((item) => (
              <TargetCard key={item.id} item={item} onRemove={removeWatchlistTarget} />
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
