"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";
import type { Commodity, Province } from "@/types/forecast";

export const PREFERENCES_STORAGE_KEY = "agriwise.preferences";

export interface AppPreferences {
  commodity: Commodity | null;
  province: Province | null;
}

const EMPTY: AppPreferences = { commodity: null, province: null };

interface PreferencesContextValue {
  preferences: AppPreferences;
  /** False during SSR and the first client render, true once mounted. */
  isHydrated: boolean;
  setCommodity: (commodity: Commodity | null) => void;
  setProvince: (province: Province | null) => void;
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

function readStored(): AppPreferences | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(PREFERENCES_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<AppPreferences>;
    return {
      commodity: parsed.commodity ?? null,
      province: parsed.province ?? null,
    };
  } catch {
    return null;
  }
}

const noopSubscribe = () => () => {};

export function AppPreferencesProvider({ children }: { children: React.ReactNode }) {
  // Lazy init: EMPTY during SSR (readStored returns null without `window`),
  // the persisted value on the client's first render.
  const [preferences, setPreferences] = useState<AppPreferences>(() => readStored() ?? EMPTY);

  // `false` on the server and the hydrating render, `true` afterwards — lets
  // consumers avoid a flash of empty state without a setState-in-effect.
  const isHydrated = useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );

  useEffect(() => {
    try {
      window.localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(preferences));
    } catch {
      // Storage unavailable (private mode / quota) — preferences stay in-memory.
    }
  }, [preferences]);

  const setCommodity = useCallback(
    (commodity: Commodity | null) => setPreferences((prev) => ({ ...prev, commodity })),
    [],
  );
  const setProvince = useCallback(
    (province: Province | null) => setPreferences((prev) => ({ ...prev, province })),
    [],
  );

  const value = useMemo(
    () => ({ preferences, isHydrated, setCommodity, setProvince }),
    [preferences, isHydrated, setCommodity, setProvince],
  );

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  const value = useContext(PreferencesContext);
  if (value === null) {
    throw new Error("usePreferences must be used within an AppPreferencesProvider");
  }
  return value;
}
