"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@iconify/react";
import { useAppStore } from "@/store/useAppStore";

export default function BottomNav() {
  const pathname = usePathname();
  const { activeTarget, watchlist } = useAppStore();

  const isHome = pathname === "/";
  const isGraph = pathname === "/graph";
  const isTimeline = pathname === "/timeline";
  const isDetail = pathname.startsWith("/target");
  const isBreaches = pathname === "/breaches";
  const isContacts = pathname === "/contacts";

  const currentTarget = activeTarget || (watchlist.length > 0 ? watchlist[0].value : null);
  const targetPath = currentTarget ? `/target/${encodeURIComponent(currentTarget)}` : "/";

  const navItemClass = (active: boolean) =>
    `flex flex-col items-center justify-center flex-1 py-1 text-[9px] font-semibold transition-all ${
      active
        ? "text-[var(--md-sys-color-primary)] font-bold scale-105"
        : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
    }`;

  return (
    <nav className="md:hidden fixed bottom-0 left-0 z-30 w-full h-16 border-t border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)]/95 backdrop-blur-md flex items-center justify-around px-1 shadow-lg">
      <Link href="/" className={navItemClass(isHome)}>
        <Icon icon={isHome ? "ph:house-fill" : "ph:house-duotone"} width="18" height="18" />
        <span className="mt-0.5">Roster</span>
      </Link>
      <Link href={targetPath} className={navItemClass(isDetail)}>
        <Icon icon={isDetail ? "ph:user-focus-fill" : "ph:user-focus-duotone"} width="18" height="18" />
        <span className="mt-0.5">Target</span>
      </Link>
      <Link href="/graph" className={navItemClass(isGraph)}>
        <Icon icon={isGraph ? "ph:tree-structure-fill" : "ph:tree-structure-duotone"} width="18" height="18" />
        <span className="mt-0.5">Graph</span>
      </Link>
      <Link href="/timeline" className={navItemClass(isTimeline)}>
        <Icon icon={isTimeline ? "ph:clock-countdown-fill" : "ph:clock-countdown-duotone"} width="18" height="18" />
        <span className="mt-0.5">Timeline</span>
      </Link>
      <Link href="/breaches" className={navItemClass(isBreaches)}>
        <Icon icon={isBreaches ? "ph:shield-warning-fill" : "ph:shield-warning-duotone"} width="18" height="18" />
        <span className="mt-0.5">Breaches</span>
      </Link>
      <Link href="/contacts" className={navItemClass(isContacts)}>
        <Icon icon={isContacts ? "ph:phone-call-fill" : "ph:phone-call-duotone"} width="18" height="18" />
        <span className="mt-0.5">Phone</span>
      </Link>
    </nav>
  );
}
