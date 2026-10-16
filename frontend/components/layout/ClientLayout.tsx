"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@iconify/react";
import BottomNav from "./BottomNav";
import RefreshButton from "./RefreshButton";
import Sidebar from "./Sidebar";
import ThemeToggle from "./ThemeToggle";
import ReconLoadingOverlay from "@/components/ui/ReconLoadingOverlay";
import { useAppStore } from "@/store/useAppStore";
import { initOfflineIcons } from "@/lib/offlineIcons";

// Pre-load all Phosphor offline icons
initOfflineIcons();


export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const isHome = pathname === "/";
  const isGraph = pathname === "/graph";
  const isDetail = pathname.startsWith("/target");
  const isBreaches = pathname === "/breaches";
  const isContacts = pathname === "/contacts";
  const isTimeline = pathname === "/timeline";

  const { activeTarget, watchlist, sidebarOpen, setSidebarOpen, activeCaseTitle } = useAppStore();

  const currentTarget = activeTarget || (watchlist.length > 0 ? watchlist[0].value : null);
  const targetPath = currentTarget ? `/target/${encodeURIComponent(currentTarget)}` : "/";

  const desktopNavLinkClass = (active: boolean) =>
    `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold tracking-tight transition-all duration-150 ${
      active
        ? "bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] shadow-2xs font-bold"
        : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-surface-container-high)]"
    }`;

  return (
    <>
      {/* GLOBAL RECON & CACHE LOADING OVERLAY */}
      <ReconLoadingOverlay />

      {/* GLOBAL TOP NAVIGATION */}
      <header className="sticky top-0 z-40 w-full border-b border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)]/90 backdrop-blur-md transition-colors duration-200">
        <div className="flex items-center justify-between px-3 sm:px-6 h-14 max-w-7xl mx-auto">
          {/* LEFT: BRAND & SIDEBAR TRIGGER */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded-lg bg-[var(--md-sys-color-surface-container-high)] hover:bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] transition-all cursor-pointer shadow-2xs"
              title="Toggle Investigation Controls Panel"
              aria-label="Toggle Controls Panel"
            >
              <Icon icon="ph:sliders-horizontal-duotone" width="18" />
            </button>

            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-8.5 h-8.5 relative flex-shrink-0 flex items-center justify-center rounded-xl bg-[var(--md-sys-color-surface-container-high)]/70 border border-[var(--md-sys-color-outline-variant)]/60 p-1 shadow-2xs group-hover:border-[var(--md-sys-color-primary)]/60 transition-all">
                <span className="text-lg">🪬</span>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-extrabold text-base tracking-tight text-[var(--md-sys-color-on-surface)] group-hover:text-[var(--md-sys-color-primary)] transition-colors">
                  HAMSA
                </span>
                <span className="hidden sm:inline-block text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] border border-[var(--md-sys-color-outline-variant)] uppercase tracking-wider">
                  OSINT
                </span>
              </div>
            </Link>

            <button
              onClick={() => setSidebarOpen(true)}
              className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-xs text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-primary)] transition-all cursor-pointer"
              title="Switch Investigation Case Workspace"
            >
              <Icon icon="ph:folder-user-duotone" width="14" className="text-[var(--md-sys-color-primary)]" />
              <span className="font-mono text-[11px] truncate max-w-[150px]">{activeCaseTitle || "Primary Case"}</span>
            </button>
          </div>

          {/* CENTER: DESKTOP NAVIGATION MENU */}
          <nav className="hidden md:flex items-center gap-1">
            <Link href="/" className={desktopNavLinkClass(isHome)}>
              <Icon icon={isHome ? "ph:house-fill" : "ph:house-duotone"} width="15" />
              <span>Roster</span>
            </Link>
            <Link href={targetPath} className={desktopNavLinkClass(isDetail)}>
              <Icon icon={isDetail ? "ph:user-focus-fill" : "ph:user-focus-duotone"} width="15" />
              <span>Target Dossier</span>
            </Link>
            <Link href="/graph" className={desktopNavLinkClass(isGraph)}>
              <Icon icon={isGraph ? "ph:tree-structure-fill" : "ph:tree-structure-duotone"} width="15" />
              <span>Knowledge Graph</span>
            </Link>
            <Link href="/timeline" className={desktopNavLinkClass(isTimeline)}>
              <Icon icon={isTimeline ? "ph:clock-countdown-fill" : "ph:clock-countdown-duotone"} width="15" />
              <span>Timeline</span>
            </Link>
            <Link href="/breaches" className={desktopNavLinkClass(isBreaches)}>
              <Icon icon={isBreaches ? "ph:shield-warning-fill" : "ph:shield-warning-duotone"} width="15" />
              <span>Breach Radar</span>
            </Link>
            <Link href="/contacts" className={desktopNavLinkClass(isContacts)}>
              <Icon icon={isContacts ? "ph:phone-call-fill" : "ph:phone-call-duotone"} width="15" />
              <span>Contacts</span>
            </Link>
          </nav>

          {/* RIGHT: ACTIONS & THEME */}
          <div className="flex items-center gap-2">
            <RefreshButton />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <div className="flex min-h-[calc(100vh-3.5rem)] pb-20 md:pb-8">
        <Sidebar />
        <div className="flex-1 min-w-0">{children}</div>
      </div>

      {/* MOBILE BOTTOM NAVIGATION */}
      <BottomNav />
    </>
  );
}
