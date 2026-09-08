"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { COMMODITIES, PROVINCES } from "@/lib/domain";
import { getCatalog } from "@/lib/forecast";
import { usePreferences } from "@/lib/preferences";
import type { Commodity, Province } from "@/types/forecast";

export default function SetupPage() {
  const { preferences, setCommodity, setProvince } = usePreferences();
  const [commodities, setCommodities] = useState<readonly Commodity[]>(COMMODITIES);
  const [provinces, setProvinces] = useState<readonly Province[]>(PROVINCES);
  const [catalogError, setCatalogError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCatalog()
      .then((catalog) => {
        if (cancelled) return;
        setCommodities(catalog.commodities);
        setProvinces(catalog.provinces);
      })
      .catch(() => {
        if (!cancelled) setCatalogError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const ready = preferences.commodity !== null && preferences.province !== null;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <div className="page-head">
        <div>
          <h1>Setup</h1>
          <p>
            Choose the commodity and CALABARZON province you want AgriWise to focus on. Your
            choice is saved on this device — no account needed.
          </p>
        </div>
      </div>

      {catalogError && (
        <p className="state state-error">
          Couldn&apos;t load the latest options from the server. Showing the standard
          commodity and province list.
        </p>
      )}

      <div className="card flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">Commodity</span>
          <select
            aria-label="Commodity"
            className="input-bare border rounded-md px-2 py-1"
            value={preferences.commodity ?? ""}
            onChange={(e) => setCommodity((e.target.value || null) as Commodity | null)}
          >
            <option value="">Select a commodity…</option>
            {commodities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">Province</span>
          <select
            aria-label="Province"
            className="input-bare border rounded-md px-2 py-1"
            value={preferences.province ?? ""}
            onChange={(e) => setProvince((e.target.value || null) as Province | null)}
          >
            <option value="">Select a province…</option>
            {provinces.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>

        <p className="text-sm text-muted">
          Analytics are province-resolution; municipality selection is not available yet.
        </p>
      </div>

      {ready ? (
        <Link href="/" className="btn btn-accent btn-sm self-start">
          Continue to Dashboard
        </Link>
      ) : (
        <p className="text-sm text-muted">Select both fields to continue.</p>
      )}
    </div>
  );
}
