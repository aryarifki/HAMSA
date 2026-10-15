"use client";

import React, { useState } from "react";
import { Icon } from "@iconify/react";
import { useAppStore } from "@/store/useAppStore";

export default function Sidebar() {
  const {
    sidebarOpen,
    setSidebarOpen,
    depth,
    setDepth,
    recursive,
    setRecursive,
    allSites,
    setAllSites,
    getcontactToken,
    setGetcontactToken,
    truecallerToken,
    setTruecallerToken,
    proxy,
    setProxy,
    setCacheLoading,
  } = useAppStore();

  const [activeTab, setActiveTab] = useState<"params" | "tokens">("params");
  const [localProxy, setLocalProxy] = useState(proxy);
  const [localGc, setLocalGc] = useState(getcontactToken);
  const [localTc, setLocalTc] = useState(truecallerToken);

  const handleSaveSettings = () => {
    setProxy(localProxy);
    setGetcontactToken(localGc);
    setTruecallerToken(localTc);
    setCacheLoading({
      isOpen: true,
      title: "Settings Applied",
      step: "Updated BYOT tokens and network proxy routing.",
      progress: 100,
      isSuccess: true,
    });
    setTimeout(() => setCacheLoading(false), 800);
  };

  const handleClearGraph = async () => {
    if (!confirm("Are you sure you want to clear the entire active intelligence graph?")) return;
    try {
      await fetch("/api/reset", { method: "POST" });
      setCacheLoading({
        isOpen: true,
        title: "Graph Cleared",
        step: "In-memory knowledge graph and entity links purged.",
        progress: 100,
        isSuccess: true,
      });
      setTimeout(() => {
        setCacheLoading(false);
        window.location.reload();
      }, 700);
    } catch (e) {
      alert("Failed to reset graph: " + e);
    }
  };

  if (!sidebarOpen) return null;

  return (
    <>
      {/* BACKDROP FOR MOBILE */}
      <div
        onClick={() => setSidebarOpen(false)}
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-xs md:hidden"
      />

      {/* DRAWER CONTAINER */}
      <aside className="fixed top-14 left-0 z-40 w-80 sm:w-96 h-[calc(100vh-3.5rem)] border-r border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)]/98 backdrop-blur-xl flex flex-col shadow-2xl transition-all duration-300">
        
        {/* HEADER */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-high)]">
          <div className="flex items-center gap-2">
            <Icon icon="ph:sliders-horizontal-duotone" width="18" className="text-[var(--md-sys-color-primary)]" />
            <h2 className="text-sm font-bold tracking-tight text-[var(--md-sys-color-on-surface)]">
              Investigation Controls
            </h2>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1.5 rounded-lg hover:bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] transition-colors cursor-pointer"
          >
            <Icon icon="ph:x-bold" width="16" />
          </button>
        </div>

        {/* TABS */}
        <div className="flex border-b border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] text-xs font-semibold">
          <button
            onClick={() => setActiveTab("params")}
            className={`flex-1 py-2.5 text-center transition-colors cursor-pointer ${
              activeTab === "params"
                ? "border-b-2 border-[var(--md-sys-color-primary)] text-[var(--md-sys-color-primary)] font-bold bg-[var(--md-sys-color-surface-container-high)]"
                : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
            }`}
          >
            Parameters & Depth
          </button>
          <button
            onClick={() => setActiveTab("tokens")}
            className={`flex-1 py-2.5 text-center transition-colors cursor-pointer ${
              activeTab === "tokens"
                ? "border-b-2 border-[var(--md-sys-color-primary)] text-[var(--md-sys-color-primary)] font-bold bg-[var(--md-sys-color-surface-container-high)]"
                : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
            }`}
          >
            BYOT API Tokens
          </button>
        </div>

        {/* BODY */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {activeTab === "params" ? (
            <>
              {/* RECURSION DEPTH */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs font-semibold">
                  <span className="text-[var(--md-sys-color-on-surface)]">Investigation Depth</span>
                  <span className="px-2 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] font-mono text-[var(--md-sys-color-primary)]">
                    Round {depth}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[1, 2, 3].map((d) => (
                    <button
                      key={d}
                      onClick={() => setDepth(d)}
                      className={`py-2 px-3 rounded-xl border text-xs font-bold transition-all cursor-pointer ${
                        depth === d
                          ? "bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] border-[var(--md-sys-color-primary)] shadow-2xs"
                          : "bg-[var(--md-sys-color-surface-container-high)] border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)]"
                      }`}
                    >
                      Round {d}
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)]">
                  {depth === 1
                    ? "Direct lookup only (no recursive secondary scans)."
                    : depth === 2
                    ? "Autonomous Round 2: auto-scans newly discovered real names and handles."
                    : "Deep crawl: 3-tier deep knowledge expansion."}
                </p>
              </div>

              {/* RECURSIVE TOGGLE */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]">
                <div>
                  <div className="text-xs font-bold text-[var(--md-sys-color-on-surface)]">
                    Agent Brain Auto-Recursion
                  </div>
                  <div className="text-[11px] text-[var(--md-sys-color-on-surface-variant)]">
                    Filter garbage tokens & prioritize leads
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={recursive}
                  onChange={(e) => setRecursive(e.target.checked)}
                  className="w-4 h-4 accent-[var(--md-sys-color-primary)] cursor-pointer"
                />
              </div>

              {/* ALL 690+ SITES TOGGLE */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]">
                <div>
                  <div className="text-xs font-bold text-[var(--md-sys-color-on-surface)]">
                    Full 690+ Sites Scan
                  </div>
                  <div className="text-[11px] text-[var(--md-sys-color-on-surface-variant)]">
                    Default 50 sites; enable for deep hunt
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={allSites}
                  onChange={(e) => setAllSites(e.target.checked)}
                  className="w-4 h-4 accent-[var(--md-sys-color-primary)] cursor-pointer"
                />
              </div>

              {/* PROXY SETTING */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--md-sys-color-on-surface)]">
                  HTTP/SOCKS Proxy Route
                </label>
                <input
                  type="text"
                  placeholder="e.g. http://127.0.0.1:9050"
                  value={localProxy}
                  onChange={(e) => setLocalProxy(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] outline-none focus:border-[var(--md-sys-color-primary)] transition-all"
                />
              </div>
            </>
          ) : (
            <>
              {/* GETCONTACT TOKEN */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--md-sys-color-on-surface)] flex items-center justify-between">
                  <span>GetContact Session Token</span>
                  <span className="text-[10px] text-emerald-500 font-mono">BYOT Live</span>
                </label>
                <textarea
                  rows={3}
                  placeholder="Paste your GetContact JWT session token here..."
                  value={localGc}
                  onChange={(e) => setLocalGc(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] outline-none focus:border-[var(--md-sys-color-primary)] transition-all font-mono"
                />
                <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)]">
                  Enables direct crowd-sourced tags and contact name extraction without fallback dorking.
                </p>
              </div>

              {/* TRUECALLER TOKEN */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--md-sys-color-on-surface)] flex items-center justify-between">
                  <span>Truecaller Bearer Token</span>
                  <span className="text-[10px] text-sky-500 font-mono">BYOT Live</span>
                </label>
                <textarea
                  rows={2}
                  placeholder="Paste your Truecaller Bearer token here..."
                  value={localTc}
                  onChange={(e) => setLocalTc(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] outline-none focus:border-[var(--md-sys-color-primary)] transition-all font-mono"
                />
              </div>
            </>
          )}
        </div>

        {/* FOOTER ACTIONS */}
        <div className="p-4 border-t border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-high)] space-y-2">
          <button
            onClick={handleSaveSettings}
            className="w-full py-2.5 rounded-xl bg-[var(--md-sys-color-primary)] hover:opacity-90 text-[var(--md-sys-color-on-primary)] text-xs font-bold transition-all shadow-md cursor-pointer flex items-center justify-center gap-1.5"
          >
            <Icon icon="ph:check-bold" width="14" />
            Apply Settings
          </button>
          <button
            onClick={handleClearGraph}
            className="w-full py-2 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] hover:bg-rose-500/20 text-rose-500 border border-rose-500/30 text-xs font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5"
          >
            <Icon icon="ph:trash-bold" width="14" />
            Reset Knowledge Graph
          </button>
        </div>

      </aside>
    </>
  );
}
