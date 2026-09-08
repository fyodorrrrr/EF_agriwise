import { afterEach, describe, expect, it } from "vitest";
import { act, cleanup, render, renderHook } from "@testing-library/react";

import { AppPreferencesProvider, PREFERENCES_STORAGE_KEY, usePreferences } from "@/lib/preferences";

afterEach(() => {
  cleanup();
  localStorage.clear();
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AppPreferencesProvider>{children}</AppPreferencesProvider>
);

describe("usePreferences", () => {
  it("starts empty when localStorage has nothing", () => {
    const { result } = renderHook(() => usePreferences(), { wrapper });

    expect(result.current.preferences).toEqual({ commodity: null, province: null });
  });

  it("hydrates from localStorage", () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ commodity: "Rice", province: "Laguna" }),
    );

    const { result } = renderHook(() => usePreferences(), { wrapper });

    expect(result.current.preferences).toEqual({ commodity: "Rice", province: "Laguna" });
    expect(result.current.isHydrated).toBe(true);
  });

  it("persists updates back to localStorage", () => {
    const { result } = renderHook(() => usePreferences(), { wrapper });

    act(() => result.current.setCommodity("Banana"));
    act(() => result.current.setProvince("Cavite"));

    expect(result.current.preferences).toEqual({ commodity: "Banana", province: "Cavite" });
    expect(JSON.parse(localStorage.getItem(PREFERENCES_STORAGE_KEY)!)).toEqual({
      commodity: "Banana",
      province: "Cavite",
    });
  });

  it("ignores corrupt stored data without throwing", () => {
    localStorage.setItem(PREFERENCES_STORAGE_KEY, "{ not json");

    const { result } = renderHook(() => usePreferences(), { wrapper });

    expect(result.current.preferences).toEqual({ commodity: null, province: null });
  });

  it("throws when used outside the provider", () => {
    function Bare() {
      usePreferences();
      return null;
    }
    expect(() => render(<Bare />)).toThrow(/AppPreferencesProvider/);
  });
});
