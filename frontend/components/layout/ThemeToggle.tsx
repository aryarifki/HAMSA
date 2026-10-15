"use client";

import React, { useEffect, useState } from "react";
import { Icon } from "@iconify/react";
import { useAppStore } from "@/store/useAppStore";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useAppStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  if (!mounted) {
    return (
      <div className="w-9 h-9 rounded-lg bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] opacity-40" />
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg bg-[var(--md-sys-color-surface-container-high)] hover:bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] transition-all cursor-pointer shadow-2xs group"
      title={isDark ? "Switch to Light Theme" : "Switch to Dark Theme"}
      aria-label="Toggle Color Theme"
    >
      <Icon
        icon={isDark ? "ph:sun-duotone" : "ph:moon-stars-duotone"}
        className="transition-transform group-hover:rotate-12"
        width="18"
        height="18"
      />
    </button>
  );
}
