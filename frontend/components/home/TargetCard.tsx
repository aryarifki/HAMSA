"use client";

import React from "react";
import Link from "next/link";
import { Icon } from "@iconify/react";
import { TargetItem, useAppStore } from "@/store/useAppStore";

export default function TargetCard({
  item,
  onRemove,
}: {
  item: TargetItem;
  onRemove?: (id: string) => void;
}) {
  const { setActiveTarget } = useAppStore();

  const typeIcons: Record<string, string> = {
    username: "ph:user-circle-duotone",
    email: "ph:envelope-simple-duotone",
    phone: "ph:phone-call-duotone",
    image: "ph:image-duotone",
    generic: "ph:identification-card-duotone",
  };

  const isHighRisk = (item.breachesFound || 0) > 0 || item.riskLevel === "high";

  return (
    <div className="group relative bg-[var(--md-sys-color-surface-container)] hover:bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/70 hover:border-[var(--md-sys-color-primary)]/50 rounded-2xl p-4.5 transition-all duration-200 shadow-2xs hover:shadow-md flex flex-col justify-between">
      {/* TOP ROW */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)]/60 flex items-center justify-center text-[var(--md-sys-color-primary)] flex-shrink-0 group-hover:scale-105 transition-transform">
            <Icon icon={typeIcons[item.type] || "ph:fingerprint-duotone"} width="22" height="22" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Link
                href={`/target/${encodeURIComponent(item.value)}`}
                onClick={() => setActiveTarget(item.value, item.type as any)}
                className="font-bold text-sm sm:text-base text-[var(--md-sys-color-on-surface)] hover:text-[var(--md-sys-color-primary)] truncate block tracking-tight"
              >
                {item.value}
              </Link>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] uppercase">
                {item.type}
              </span>
            </div>
            {item.label && item.label !== item.value && (
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] truncate mt-0.5">
                {item.label}
              </p>
            )}
          </div>
        </div>

        {/* RISK BADGE */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase font-mono border ${
              isHighRisk
                ? "bg-rose-500/15 border-rose-500/40 text-[var(--color-negative)]"
                : "bg-emerald-500/15 border-emerald-500/40 text-[var(--color-positive)]"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isHighRisk ? "bg-[var(--color-negative)] animate-ping" : "bg-[var(--color-positive)]"
              }`}
            />
            {isHighRisk ? "Breached" : "Clean"}
          </span>

          {onRemove && (
            <button
              onClick={() => onRemove(item.id)}
              className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] hover:text-rose-500 transition-all cursor-pointer"
              title="Remove from Roster"
            >
              <Icon icon="ph:trash-duotone" width="16" />
            </button>
          )}
        </div>
      </div>

      {/* METRICS ROW */}
      <div className="grid grid-cols-3 gap-2 border-t border-[var(--md-sys-color-outline-variant)]/40 mt-3 pt-3 text-center">
        <div>
          <div className="text-[10px] font-semibold text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider">
            Accounts
          </div>
          <div className="text-sm font-bold font-mono text-[var(--md-sys-color-on-surface)] mt-0.5">
            {item.accountsFound ?? "-"}
          </div>
        </div>
        <div>
          <div className="text-[10px] font-semibold text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider">
            Breaches
          </div>
          <div
            className={`text-sm font-bold font-mono mt-0.5 ${
              (item.breachesFound || 0) > 0 ? "text-[var(--color-negative)]" : "text-[var(--color-positive)]"
            }`}
          >
            {item.breachesFound ?? 0}
          </div>
        </div>
        <div>
          <div className="text-[10px] font-semibold text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider">
            Network/Carrier
          </div>
          <div className="text-xs font-semibold text-[var(--md-sys-color-primary)] mt-0.5 truncate px-1">
            {item.carrier || "Global Web"}
          </div>
        </div>
      </div>

      {/* BOTTOM ACTION */}
      <div className="mt-3 pt-2 flex items-center justify-between text-xs text-[var(--md-sys-color-on-surface-variant)]">
        <span className="text-[11px] font-mono">
          {new Date(item.addedAt).toLocaleDateString()}
        </span>
        <Link
          href={`/target/${encodeURIComponent(item.value)}`}
          onClick={() => setActiveTarget(item.value, item.type as any)}
          className="inline-flex items-center gap-1 text-[var(--md-sys-color-primary)] font-bold hover:underline"
        >
          <span>Deep Dossier</span>
          <Icon icon="ph:arrow-right-bold" width="12" />
        </Link>
      </div>
    </div>
  );
}
