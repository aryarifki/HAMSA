"use client";

import React, { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { Icon } from "@iconify/react";
import { useAppStore } from "@/store/useAppStore";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

interface TimelineEvent {
  timestamp: string;
  category: string;
  event: string;
  details: string;
  node_id?: string;
}

export default function TimelinePage() {
  const { activeCaseId, activeCaseTitle } = useAppStore();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  const { data, error, isLoading } = useSWR<{ timeline: TimelineEvent[]; case_id: string }>(
    `/api/timeline?case_id=${encodeURIComponent(activeCaseId)}`,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 10000 }
  );

  const events = data?.timeline || [];

  const categories = ["ALL", ...Array.from(new Set(events.map((e) => e.category)))];

  const filteredEvents = events.filter((e) => {
    const matchCat = selectedCategory === "ALL" || e.category === selectedCategory;
    const matchSearch =
      !searchTerm ||
      e.event.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.details.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.timestamp.toLowerCase().includes(searchTerm.toLowerCase());
    return matchCat && matchSearch;
  });

  const getCategoryColor = (category: string) => {
    const cat = category.toLowerCase();
    if (cat.includes("security") || cat.includes("breach") || cat.includes("malware")) {
      return "text-rose-400 bg-rose-500/15 border-rose-500/30";
    }
    if (cat.includes("physical") || cat.includes("device") || cat.includes("photo")) {
      return "text-amber-400 bg-amber-500/15 border-amber-500/30";
    }
    if (cat.includes("identity") || cat.includes("account")) {
      return "text-emerald-400 bg-emerald-500/15 border-emerald-500/30";
    }
    return "text-sky-400 bg-sky-500/15 border-sky-500/30";
  };

  const getCategoryIcon = (category: string) => {
    const cat = category.toLowerCase();
    if (cat.includes("security") || cat.includes("breach")) return "ph:shield-warning-duotone";
    if (cat.includes("malware") || cat.includes("infected")) return "ph:bug-duotone";
    if (cat.includes("physical") || cat.includes("photo")) return "ph:camera-duotone";
    if (cat.includes("device")) return "ph:device-mobile-duotone";
    return "ph:clock-duotone";
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 animate-in fade-in duration-200">
      
      {/* HEADER HERO */}
      <div className="relative overflow-hidden rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] flex items-center justify-center text-[var(--md-sys-color-primary)] text-2xl flex-shrink-0 shadow-sm">
              <Icon icon="ph:clock-countdown-duotone" width="32" height="32" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-extrabold text-[var(--md-sys-color-on-surface)] tracking-tight">
                  Chronoforensic Timeline
                </h1>
                <span className="px-2 py-0.5 rounded-full bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] text-[10px] font-mono font-bold uppercase">
                  {events.length} Events
                </span>
              </div>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-1 font-mono">
                Workspace: {activeCaseTitle} ({activeCaseId})
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-stretch sm:self-auto">
            <Link
              href="/graph"
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] font-bold text-xs shadow-sm hover:bg-[var(--md-sys-color-surface-container-high)] transition-all cursor-pointer"
            >
              <Icon icon="ph:tree-structure-bold" width="15" />
              <span>Network Graph</span>
            </Link>
            <a
              href={`/api/report?format=html&title=${encodeURIComponent(activeCaseTitle)}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] font-bold text-xs shadow-md hover:opacity-90 transition-all cursor-pointer"
            >
              <Icon icon="ph:file-html-bold" width="15" />
              <span>Export Dossier</span>
            </a>
          </div>
        </div>

        {/* SEARCH & CATEGORY FILTER BAR */}
        <div className="mt-6 pt-4 border-t border-[var(--md-sys-color-outline-variant)]/60 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
          <div className="relative flex-1 max-w-md">
            <Icon
              icon="ph:magnifying-glass-duotone"
              width="16"
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--md-sys-color-on-surface-variant)]"
            />
            <input
              type="text"
              placeholder="Search chronological events, breaches, or locations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-xs rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] outline-none focus:border-[var(--md-sys-color-primary)] transition-all font-mono"
            />
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                  selectedCategory === cat
                    ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] font-bold shadow-xs"
                    : "bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* TIMELINE STREAM */}
      <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-[var(--md-sys-color-outline-variant)]">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-[var(--md-sys-color-on-surface-variant)]">
            Loading chronological intelligence stream...
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] space-y-2">
            <Icon icon="ph:calendar-blank-duotone" width="40" className="mx-auto text-[var(--md-sys-color-primary)] opacity-50" />
            <p className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">No Timestamped Incidents Discovered</p>
            <p className="text-xs">Run reconnaissance on targets with photo EXIF, breach data, or malware logs to populate the timeline.</p>
          </div>
        ) : (
          filteredEvents.map((evt, idx) => {
            const badgeClass = getCategoryColor(evt.category);
            const iconName = getCategoryIcon(evt.category);

            return (
              <div
                key={idx}
                className="relative group transition-all duration-200"
              >
                {/* TIMELINE NODE PIN */}
                <div className="absolute -left-6 sm:-left-8 top-4 w-4 h-4 rounded-full bg-[var(--md-sys-color-surface-container-highest)] border-2 border-[var(--md-sys-color-primary)] group-hover:scale-125 transition-transform" />

                {/* EVENT CARD */}
                <div className="rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-5 shadow-sm hover:border-[var(--md-sys-color-primary)]/50 transition-all space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${badgeClass}`}>
                        <Icon icon={iconName} width="13" />
                        <span>{evt.category}</span>
                      </span>
                      <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
                        {evt.event}
                      </h3>
                    </div>

                    <span className="font-mono text-xs font-semibold text-[var(--md-sys-color-primary)] bg-[var(--md-sys-color-surface-container-highest)] px-2.5 py-1 rounded-lg border border-[var(--md-sys-color-outline-variant)]/60 self-start sm:self-auto">
                      {evt.timestamp}
                    </span>
                  </div>

                  <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
                    {evt.details}
                  </p>

                  {evt.node_id && (
                    <div className="pt-2 border-t border-[var(--md-sys-color-outline-variant)]/40 flex items-center justify-between text-[11px] font-mono text-[var(--md-sys-color-on-surface-variant)]">
                      <span>Node Ref: {evt.node_id}</span>
                      <Link
                        href="/graph"
                        className="text-[var(--md-sys-color-primary)] hover:underline inline-flex items-center gap-1 font-sans font-bold"
                      >
                        <span>Focus on Graph</span>
                        <Icon icon="ph:arrow-right-bold" width="11" />
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

    </div>
  );
}
