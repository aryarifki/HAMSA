"use client";

import React, { useState } from "react";
import { Icon } from "@iconify/react";
import { useAppStore } from "@/store/useAppStore";

export default function RefreshButton() {
  const [loading, setLoading] = useState(false);
  const { setCacheLoading } = useAppStore();

  const handleSyncSources = async () => {
    if (loading) return;
    setLoading(true);
    setCacheLoading({
      isOpen: true,
      title: "Synchronizing Community Sources",
      step: "Fetching 690+ WhatsMyName website signatures...",
      detail: "Upstream GitHub -> Local Cache",
      progress: 40,
      isSuccess: false,
    });

    try {
      const resp = await fetch("/api/update-sources", { method: "POST" });
      const data = await resp.json();
      setCacheLoading({
        isOpen: true,
        title: "Sources Synchronized!",
        step: `Successfully updated ${data.total_sites || 692} site definitions.`,
        detail: "Memory & Cache Layer Ready",
        progress: 100,
        isSuccess: true,
      });
      setTimeout(() => {
        setCacheLoading(false);
      }, 1200);
    } catch (err) {
      setCacheLoading({
        isOpen: true,
        title: "Synchronization Error",
        step: `Failed to fetch sources: ${err}`,
        progress: 100,
        isSuccess: false,
      });
      setTimeout(() => {
        setCacheLoading(false);
      }, 2000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleSyncSources}
      disabled={loading}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--md-sys-color-surface-container-high)] hover:bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] text-xs font-semibold transition-all cursor-pointer shadow-2xs disabled:opacity-50"
      title="Synchronize 690+ WhatsMyName Site Definitions"
    >
      <Icon
        icon="ph:arrows-clockwise-bold"
        className={loading ? "animate-spin text-[var(--md-sys-color-primary)]" : ""}
        width="14"
      />
      <span className="hidden sm:inline">Sync Sources</span>
    </button>
  );
}
