"use client";

import React from "react";
import useSWR from "swr";
import Link from "next/link";
import { Icon } from "@iconify/react";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function ContactsPage() {
  const { data: graphData, isLoading } = useSWR("/api/graph", fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 15000,
  });

  const nodes = graphData?.nodes || [];
  const phoneNodes = nodes.filter(
    (n: any) => n.type === "phone" || n.attributes?.carrier || n.attributes?.source === "GetContact" || n.attributes?.source === "Truecaller"
  );

  const dorkNodes = nodes.filter((n: any) => n.attributes?.google_search_url);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 animate-in fade-in duration-200">
      
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Icon icon="ph:phone-call-duotone" width="24" className="text-amber-500" />
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-[var(--md-sys-color-on-surface)]">
              Phone Intelligence & Contact Tags
            </h1>
          </div>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-1">
            E.164 normalization, telecommunication carrier mapping, GetContact/Truecaller crowd-sourced tags, and directory dorks.
          </p>
        </div>

        <div className="px-3.5 py-1.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-500 text-xs font-mono font-bold">
          {phoneNodes.length} Phone Entities
        </div>
      </div>

      {/* PHONE NODES LIST */}
      {isLoading ? (
        <div className="p-12 text-center text-xs font-mono text-[var(--md-sys-color-on-surface-variant)] flex items-center justify-center gap-2">
          <Icon icon="ph:spinner-bold" className="animate-spin text-[var(--md-sys-color-primary)]" width="18" />
          <span>Retrieving Phone Intelligence Records...</span>
        </div>
      ) : phoneNodes.length === 0 ? (
        <div className="p-12 rounded-3xl border border-dashed border-[var(--md-sys-color-outline-variant)] text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/15 border border-amber-500/30 text-amber-500 flex items-center justify-center mx-auto text-xl">
            📞
          </div>
          <h3 className="text-base font-bold text-[var(--md-sys-color-on-surface)]">
            No Phone Numbers in Active Graph
          </h3>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-md mx-auto">
            Scan a phone number on the Home page (e.g. +628123456789) to extract carrier metadata, WhatsApp/Telegram presence, and crowd-sourced contact tags.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {phoneNodes.map((p: any) => (
            <div
              key={p.id}
              className="p-5 rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] hover:bg-[var(--md-sys-color-surface-container-high)] transition-all flex flex-col justify-between space-y-3 shadow-2xs"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-bold text-sm text-[var(--md-sys-color-on-surface)]">
                    {p.label}
                  </h4>
                  <span className="text-[10px] font-mono text-[var(--md-sys-color-primary)]">
                    {p.attributes?.source || "Telecom"}
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] text-[10px] font-mono uppercase text-[var(--md-sys-color-on-surface-variant)]">
                  {p.attributes?.line_type || "GSM Mobile"}
                </span>
              </div>

              <div className="space-y-1.5 text-xs text-[var(--md-sys-color-on-surface-variant)] border-t border-[var(--md-sys-color-outline-variant)]/40 pt-3">
                {p.attributes?.carrier && (
                  <div className="flex justify-between">
                    <span>Operator:</span>
                    <b className="text-[var(--md-sys-color-on-surface)]">{p.attributes.carrier}</b>
                  </div>
                )}
                {p.attributes?.tag && (
                  <div className="flex flex-col gap-0.5">
                    <span>Contact Tag:</span>
                    <span className="font-mono text-xs text-[var(--md-sys-color-primary)] font-bold bg-[var(--md-sys-color-surface-container-highest)] p-1.5 rounded">
                      &quot;{p.attributes.tag}&quot;
                    </span>
                  </div>
                )}
              </div>

              <div className="pt-2 flex items-center justify-between">
                {p.attributes?.whatsapp_url ? (
                  <a
                    href={p.attributes.whatsapp_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-emerald-500 font-bold hover:underline inline-flex items-center gap-1"
                  >
                    <Icon icon="ph:whatsapp-logo-bold" width="14" />
                    <span>WhatsApp</span>
                  </a>
                ) : (
                  <span className="text-[10px] text-[var(--md-sys-color-on-surface-variant)]">E.164 Verified</span>
                )}

                <Link
                  href={`/target/${encodeURIComponent(p.value || p.label)}`}
                  className="text-xs font-bold text-[var(--md-sys-color-primary)] hover:underline inline-flex items-center gap-1"
                >
                  <span>Dossier</span>
                  <Icon icon="ph:arrow-right-bold" width="11" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CALLER DIRECTORY DORKS SECTION */}
      {dorkNodes.length > 0 && (
        <div className="space-y-3 pt-4 border-t border-[var(--md-sys-color-outline-variant)]">
          <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)] flex items-center gap-2">
            <Icon icon="ph:google-logo-bold" width="16" />
            <span>Generated Caller Directory Dorks</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {dorkNodes.map((d: any) => (
              <a
                key={d.id}
                href={d.attributes?.google_search_url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-3.5 rounded-xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] hover:bg-[var(--md-sys-color-surface-container-high)] flex items-center justify-between gap-3 text-xs text-sky-500 hover:underline group"
              >
                <div className="truncate">
                  <div className="font-semibold text-[var(--md-sys-color-on-surface)] group-hover:text-sky-500 truncate">
                    {d.label}
                  </div>
                  <div className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] font-mono truncate mt-0.5">
                    {d.attributes?.search_query}
                  </div>
                </div>
                <Icon icon="ph:arrow-square-out-bold" width="15" className="flex-shrink-0" />
              </a>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
