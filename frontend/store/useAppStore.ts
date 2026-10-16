import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface CacheLoadingState {
  isOpen: boolean;
  title?: string;
  step?: string;
  detail?: string;
  progress?: number;
  isSuccess?: boolean;
}

export interface TargetItem {
  id: string;
  value: string;
  type: "username" | "email" | "phone" | "image" | "generic";
  label?: string;
  addedAt: string;
  riskLevel?: "clean" | "medium" | "high";
  accountsFound?: number;
  breachesFound?: number;
  carrier?: string;
}

interface AppState {
  theme: "dark" | "light";
  sidebarOpen: boolean;
  activeTarget: string;
  activeTargetType: "username" | "email" | "phone" | "image";
  depth: number;
  recursive: boolean;
  allSites: boolean;
  getcontactToken: string;
  truecallerToken: string;
  proxy: string;
  watchlist: TargetItem[];
  cacheLoading: CacheLoadingState;
  activeCaseId: string;
  activeCaseTitle: string;
  cases: any[];
  streamLiveNodes: boolean;
  radarPings: number;

  setTheme: (theme: "dark" | "light") => void;
  toggleTheme: () => void;
  setSidebarOpen: (isOpen: boolean) => void;
  setActiveTarget: (target: string, type?: "username" | "email" | "phone" | "image") => void;
  setActiveCase: (id: string, title?: string) => void;
  setCases: (cases: any[]) => void;
  setStreamLiveNodes: (enabled: boolean) => void;
  incrementRadarPings: () => void;
  setDepth: (depth: number) => void;
  setRecursive: (recursive: boolean) => void;
  setAllSites: (allSites: boolean) => void;
  setGetcontactToken: (token: string) => void;
  setTruecallerToken: (token: string) => void;
  setProxy: (proxy: string) => void;
  addWatchlistTarget: (item: TargetItem) => void;
  removeWatchlistTarget: (id: string) => void;
  setCacheLoading: (state: Partial<CacheLoadingState> | boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: "dark",
      sidebarOpen: false,
      activeTarget: "",
      activeTargetType: "username",
      depth: 1,
      recursive: true,
      allSites: false,
      getcontactToken: "",
      truecallerToken: "",
      proxy: "",
      watchlist: [],
      cacheLoading: {
        isOpen: false,
        title: "Intelligence Recon & Caching",
        step: "Idle",
        detail: "L1 Memory & HAMSA Engine",
        progress: 0,
        isSuccess: false,
      },
      activeCaseId: "case_default",
      activeCaseTitle: "Primary Investigation Dossier",
      cases: [],
      streamLiveNodes: true,
      radarPings: 0,

      setTheme: (theme) => set({ theme }),
      toggleTheme: () =>
        set((state) => ({ theme: state.theme === "dark" ? "light" : "dark" })),
      setSidebarOpen: (isOpen) => set({ sidebarOpen: isOpen }),
      setActiveTarget: (target, type = "username") =>
        set({ activeTarget: target, activeTargetType: type }),
      setActiveCase: (id, title) =>
        set((state) => ({
          activeCaseId: id,
          activeCaseTitle: title || state.activeCaseTitle,
        })),
      setCases: (cases) => set({ cases }),
      setStreamLiveNodes: (enabled) => set({ streamLiveNodes: enabled }),
      incrementRadarPings: () => set((state) => ({ radarPings: state.radarPings + 1 })),
      setDepth: (depth) => set({ depth }),
      setRecursive: (recursive) => set({ recursive }),
      setAllSites: (allSites) => set({ allSites }),
      setGetcontactToken: (token) => set({ getcontactToken: token }),
      setTruecallerToken: (token) => set({ truecallerToken: token }),
      setProxy: (proxy) => set({ proxy }),
      addWatchlistTarget: (item) =>
        set((state) => {
          const exists = state.watchlist.some((w) => w.id === item.id);
          const nextList = exists
            ? state.watchlist.map((w) => (w.id === item.id ? item : w))
            : [item, ...state.watchlist];
          return {
            watchlist: nextList,
            activeTarget: item.value,
            activeTargetType: item.type as any,
          };
        }),
      removeWatchlistTarget: (id) =>
        set((state) => ({
          watchlist: state.watchlist.filter((w) => w.id !== id),
        })),
      setCacheLoading: (val) =>
        set((state) => {
          if (typeof val === "boolean") {
            return {
              cacheLoading: {
                ...state.cacheLoading,
                isOpen: val,
                progress: val ? 25 : 100,
                isSuccess: !val,
              },
            };
          }
          return {
            cacheLoading: {
              ...state.cacheLoading,
              ...val,
            },
          };
        }),
    }),
    {
      name: "hamsa-global-state",
      version: 1,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => {
        const { sidebarOpen: _sb, cacheLoading: _cl, ...rest } = state;
        return rest;
      },
    }
  )
);
