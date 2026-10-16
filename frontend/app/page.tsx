"use client";

import React, { useState } from "react";
import Link from "next/link";
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
  const [latestScanResult, setLatestScanResult] = useState<{
    target: string;
    type: string;
    nodes: any[];
    edges: any[];
    summary: any;
  } | null>(null);

  // System status and stats
  const { data: graphData, mutate: mutateGraph } = useSWR("/api/graph", fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 15000,
  });

  const totalEntities = graphData?.summary?.total_entities || 0;
  const totalRelations = graphData?.summary?.total_relations || 0;

  // Active displayed findings strictly scoped to the active scan
  const displayResult = latestScanResult;

  const displayAccounts = (displayResult?.nodes || []).filter(
    (n: any) => n.id?.startsWith("account:") || n.type === "account" || n.attributes?.platform
  );
  const displayBreaches = (displayResult?.nodes || []).filter(
    (n: any) => n.type === "breach" || n.id?.startsWith("breach:") || n.id?.startsWith("infostealer:")
  );
  const displayPhones = (displayResult?.nodes || []).filter(
    (n: any) => n.type === "phone" || n.id?.startsWith("phone:") || n.attributes?.carrier
  );


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

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`Server returned HTTP ${resp.status}: ${errText}`);
      }

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
      setLatestScanResult({
        target: cleanTarget,
        type: selectedType,
        nodes: nodes,
        edges: res.edges || [],
        summary: res.summary || { total_entities: nodes.length, total_relations: (res.edges || []).length },
      });
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
                    : "Enter target phone number (e.g. 0818123456 or +6289612345678)..."
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

      {/* LIVE INTELLIGENCE FINDINGS */}
      {displayResult && (
        <div className="rounded-3xl border border-[var(--md-sys-color-primary)]/40 bg-[var(--md-sys-color-surface-container)] p-6 sm:p-7 shadow-xl space-y-5 animate-in fade-in duration-300">
          {/* Header */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--md-sys-color-outline-variant)]/60 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] flex items-center justify-center text-xl shadow-md">
                <Icon icon="ph:check-bold" width="22" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg sm:text-xl font-extrabold text-[var(--md-sys-color-on-surface)] tracking-tight">
                    Intelligence Findings: <span className="text-[var(--md-sys-color-primary)] font-mono">{displayResult.target}</span>
                  </h2>
                  <span className="px-2 py-0.5 rounded-full bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] text-[10px] font-mono font-bold uppercase">
                    {displayResult.type}
                  </span>
                </div>
                <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-0.5 font-mono">
                  Identified {displayResult.summary?.total_entities || displayResult.nodes?.length || 0} entities & {displayResult.summary?.total_relations || displayResult.edges?.length || 0} relational connections
                </p>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Link
                href={`/target/${encodeURIComponent(displayResult.target)}`}
                className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] font-bold text-xs shadow-md hover:opacity-90 transition-all cursor-pointer"
              >
                <Icon icon="ph:identification-badge-duotone" width="16" />
                <span>Buka Berkas Target (Dossier)</span>
              </Link>
              <Link
                href="/graph"
                className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] font-bold text-xs shadow-sm hover:bg-[var(--md-sys-color-surface-container-high)] transition-all cursor-pointer"
              >
                <Icon icon="ph:tree-structure-bold" width="16" />
                <span>Lihat Graf Entitas</span>
              </Link>
              <a
                href={`/api/report?format=html&title=Forensic%20Report:%20${encodeURIComponent(displayResult.target)}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center p-2 rounded-xl bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-primary)] transition-all"
                title="Download Laporan Forensik HTML"
              >
                <Icon icon="ph:file-html-bold" width="16" />
              </a>
            </div>
          </div>

          {/* EMAIL THREAT ASSESSMENT BANNER (EXPLICIT FOR EMAIL SEARCHES) */}
          {displayResult.type === "email" && (
            <div
              className={`p-5 rounded-2xl border space-y-3 ${
                displayBreaches.length > 0
                  ? "bg-rose-500/10 border-rose-500/30 text-rose-300"
                  : "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                      displayBreaches.length > 0 ? "bg-rose-500 text-white" : "bg-emerald-500 text-white"
                    }`}
                  >
                    <Icon
                      icon={displayBreaches.length > 0 ? "ph:shield-warning-bold" : "ph:shield-check-bold"}
                      width="22"
                    />
                  </div>
                  <div>
                    <h3 className="font-extrabold text-sm text-[var(--md-sys-color-on-surface)]">
                      {displayBreaches.length > 0
                        ? `Peringatan: Ditemukan ${displayBreaches.length} Insiden Kebocoran / Infeksi Malware!`
                        : "Audit Selesai: Email Bersih / Belum Terdeteksi Bocor"}
                    </h3>
                    <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-0.5">
                      {displayBreaches.length > 0
                        ? "Alamat email ini teridentifikasi dalam database kebocoran kredensial publik atau log infeksi infostealer."
                        : "Pemeriksaan terhadap XposedOrNot dan Hudson Rock tidak menemukan kebocoran publik untuk email ini."}
                    </p>
                  </div>
                </div>
                <Link
                  href={`/target/${encodeURIComponent(displayResult.target)}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface)] hover:text-[var(--md-sys-color-primary)] transition-all shrink-0 self-start sm:self-auto"
                >
                  <span>Buka Tabel Breaches</span>
                  <Icon icon="ph:arrow-right-bold" width="12" />
                </Link>
              </div>

              {/* Quick Guidance / Remediation */}
              <div className="p-3 rounded-xl bg-[var(--md-sys-color-surface-container-highest)]/60 border border-[var(--md-sys-color-outline-variant)]/40 text-xs text-[var(--md-sys-color-on-surface-variant)] space-y-1">
                <div className="font-bold text-[var(--md-sys-color-on-surface)] text-[11px] uppercase tracking-wider flex items-center gap-1.5">
                  <Icon icon="ph:info-bold" width="13" className="text-[var(--md-sys-color-primary)]" />
                  Rekomendasi Tindakan Forensik
                </div>
                <p className="text-[11px] leading-relaxed">
                  {displayBreaches.length > 0
                    ? "Segera lakukan rotasi kata sandi untuk semua layanan yang terdaftar menggunakan email ini, aktifkan Multi-Factor Authentication (2FA), dan periksa komputer yang bersangkutan dengan pemindai malware."
                    : "Email dalam kondisi aman. Tetap pantau secara berkala dan gunakan kata sandi yang unik serta pengelola kata sandi (password manager)."}
                </p>
              </div>
            </div>
          )}

          {/* ACCOUNTS LIST */}
          {displayAccounts.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--md-sys-color-on-surface-variant)] flex items-center gap-1.5">
                  <Icon icon="ph:globe-duotone" width="15" className="text-sky-500" />
                  Discovered Online Platforms & Accounts ({displayAccounts.length})
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {displayAccounts.map((acc: any) => {
                  const url = acc.attributes?.profile_url || (acc.value && String(acc.value).startsWith("http") ? acc.value : null);
                  const platformName = acc.attributes?.platform || acc.label?.replace(/^account:[^:]*:/, "") || acc.value;
                  const category = acc.attributes?.category || "Profile";
                  return (
                    <div
                      key={acc.id}
                      className="p-3.5 rounded-2xl bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/60 flex flex-col justify-between hover:border-[var(--md-sys-color-primary)]/40 transition-all shadow-2xs"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-xs text-[var(--md-sys-color-on-surface)] truncate">
                          {platformName}
                        </span>
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] uppercase">
                          {category}
                        </span>
                      </div>
                      {url ? (
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-2.5 text-[11px] font-mono text-sky-500 hover:underline truncate inline-flex items-center gap-1"
                        >
                          <Icon icon="ph:arrow-square-out-bold" width="12" />
                          <span className="truncate">{url}</span>
                        </a>
                      ) : (
                        <span className="mt-2 text-[11px] font-mono text-[var(--md-sys-color-on-surface-variant)] truncate">
                          {acc.value}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* BREACHES (IF ANY) */}
          {displayBreaches.length > 0 && (
            <div className="space-y-3 pt-2">
              <span className="text-xs font-bold uppercase tracking-wider text-rose-500 flex items-center gap-1.5">
                <Icon icon="ph:shield-warning-duotone" width="15" />
                Data Breach & Infostealer Infections ({displayBreaches.length})
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {displayBreaches.map((b: any) => {
                  const host = b.attributes?.hostname || b.attributes?.computer_name;
                  const os = b.attributes?.operating_system || b.attributes?.os;
                  const date = b.attributes?.infection_date || b.attributes?.breach_date || b.attributes?.date;
                  const source = b.attributes?.source || b.source_plugin || "Infostealer Log";
                  const av = b.attributes?.antivirus;
                  return (
                    <div key={b.id} className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 space-y-2 hover:border-rose-500/50 transition-all shadow-xs">
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-bold text-xs text-rose-400 break-all">
                          {b.label || b.value}
                        </span>
                        <span className="text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 shrink-0">
                          {source}
                        </span>
                      </div>
                      <div className="space-y-1 text-[11px] font-mono text-[var(--md-sys-color-on-surface-variant)] pt-1 border-t border-rose-500/20">
                        {host && (
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] opacity-75">Hostname:</span>
                            <span className="font-bold text-[var(--md-sys-color-on-surface)] truncate max-w-[140px]">{host}</span>
                          </div>
                        )}
                        {os && (
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] opacity-75">OS:</span>
                            <span className="text-[var(--md-sys-color-on-surface)]">{os}</span>
                          </div>
                        )}
                        {av && (
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] opacity-75">Antivirus:</span>
                            <span className="text-amber-400">{av}</span>
                          </div>
                        )}
                        {date && (
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] opacity-75">Tanggal Terpapar:</span>
                            <span className="text-[var(--md-sys-color-on-surface)]">{String(date).slice(0, 10)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* PHONE / TELECOM (IF ANY) */}
          {displayPhones.length > 0 && (
            <div className="space-y-3 pt-2">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-500 flex items-center gap-1.5">
                <Icon icon="ph:phone-call-duotone" width="15" />
                Telecommunication Intelligence
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {displayPhones.map((p: any) => (
                  <div key={p.id} className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-2">
                    <div className="font-bold text-xs text-amber-400">
                      {p.label || p.value}
                    </div>
                    {p.attributes?.carrier && (
                      <div className="text-[11px] font-mono text-[var(--md-sys-color-on-surface)]">
                        Carrier: <span className="font-bold">{p.attributes.carrier}</span> ({p.attributes.country || "ID"})
                      </div>
                    )}
                    <div className="flex items-center gap-2 pt-1">
                      {p.attributes?.whatsapp_link && (
                        <a
                          href={p.attributes.whatsapp_link}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2.5 py-1 rounded-lg bg-emerald-600 text-white text-[10px] font-bold inline-flex items-center gap-1 shadow-sm hover:opacity-90"
                        >
                          <Icon icon="ph:whatsapp-logo-bold" width="12" />
                          <span>WhatsApp</span>
                        </a>
                      )}
                      {p.attributes?.telegram_link && (
                        <a
                          href={p.attributes.telegram_link}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2.5 py-1 rounded-lg bg-sky-600 text-white text-[10px] font-bold inline-flex items-center gap-1 shadow-sm hover:opacity-90"
                        >
                          <Icon icon="ph:arrow-square-out-bold" width="12" />
                          <span>Telegram</span>
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ZERO FINDINGS EMPTY STATE */}
          {displayAccounts.length === 0 && displayBreaches.length === 0 && displayPhones.length === 0 && (
            <div className="p-8 rounded-2xl bg-[var(--md-sys-color-surface-container-high)] text-center space-y-2 border border-dashed border-[var(--md-sys-color-outline-variant)]">
              <Icon icon="ph:shield-check-duotone" className="mx-auto text-emerald-500" width="32" />
              <p className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
                No matching public records or exposures detected
              </p>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-md mx-auto">
                No active accounts, data breach records, or contact tags were identified for this target across the probed platforms.
              </p>
            </div>
          )}
        </div>
      )}

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
