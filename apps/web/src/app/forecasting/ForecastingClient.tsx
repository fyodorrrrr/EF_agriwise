"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ComponentCard } from "@/components/forecast/ComponentCard";
import { formatQuarter, verdictBadgeClass, verdictLabel } from "@/components/forecast/verdict";
import { COMMODITIES, PROVINCES } from "@/lib/domain";
import { getOutlook } from "@/lib/forecast";
import { usePreferences } from "@/lib/preferences";
import type { Commodity, OutlookResponse, Province } from "@/types/forecast";

type Status = "idle" | "loading" | "ready" | "error";

export function ForecastingClient() {
  const { preferences, isHydrated, setCommodity, setProvince } = usePreferences();
  const searchParams = useSearchParams();

  // Seed the commodity from ?commodity= once, if preferences don't have one.
  const seeded = useRef(false);
  useEffect(() => {
    if (seeded.current) return;
    seeded.current = true;
    const q = searchParams.get("commodity");
    if (q && (COMMODITIES as readonly string[]).includes(q) && !preferences.commodity) {
      setCommodity(q as Commodity);
    }
  }, [searchParams, preferences.commodity, setCommodity]);

  const { commodity, province } = preferences;
  const key = commodity && province ? `${commodity}|${province}` : null;
  const [result, setResult] = useState<{ key: string; outlook: OutlookResponse } | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  useEffect(() => {
    if (!key || !commodity || !province) return;
    let cancelled = false;
    getOutlook(commodity, province)
      .then((data) => !cancelled && setResult({ key, outlook: data }))
      .catch(() => !cancelled && setErrorKey(key));
    return () => {
      cancelled = true;
    };
  }, [key, commodity, province]);

  // Derived — no stale values: `outlook` is only surfaced for the current key.
  const status: Status = !key
    ? "idle"
    : errorKey === key
      ? "error"
      : result?.key === key
        ? "ready"
        : "loading";
  const outlook = result?.key === key ? result.outlook : null;

  if (!isHydrated) return null;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <div className="page-head">
        <div>
          <h1>Forecasting</h1>
          <p>
            Observed history and a short forecast for one commodity in one CALABARZON
            province. Analytics are province-resolution — never a municipality forecast.
          </p>
        </div>
        <div className="flex gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Commodity</span>
            <select
              aria-label="Commodity"
              className="input-bare border rounded-md px-2 py-1"
              value={commodity ?? ""}
              onChange={(e) => setCommodity((e.target.value || null) as Commodity | null)}
            >
              <option value="">Select…</option>
              {COMMODITIES.map((c) => (
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
              value={province ?? ""}
              onChange={(e) => setProvince((e.target.value || null) as Province | null)}
            >
              <option value="">Select…</option>
              {PROVINCES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {(!commodity || !province) && (
        <p className="state">
          Pick a commodity and province — or set them once in{" "}
          <Link href="/setup" className="underline">
            Setup
          </Link>
          .
        </p>
      )}

      {status === "loading" && <p className="state state-loading">Loading forecast…</p>}
      {status === "error" && (
        <p className="state state-error">Couldn&apos;t reach the forecast service.</p>
      )}

      {status === "ready" && outlook && (
        <>
          <p className="text-xs text-muted">{outlook.resolution_note}</p>
          <div className="grid gap-3 md:grid-cols-3">
            <ComponentCard kind="demand" component={outlook.demand} detailed />
            <ComponentCard kind="supply" component={outlook.supply} detailed />
            <ComponentCard kind="price" component={outlook.price} detailed />
          </div>
          <OpportunityCard outlook={outlook} />
        </>
      )}
    </div>
  );
}

function OpportunityCard({ outlook }: { outlook: OutlookResponse }) {
  const opp = outlook.opportunity;

  if (opp.verdict === "INSUFFICIENT_DATA") {
    return (
      <div className="card flex flex-col gap-2">
        <div className="card-head">
          <span className="card-kicker">Opportunity</span>
          <span className="badge badge-neutral">Insufficient data</span>
        </div>
        <p className="state">
          A peer-relative opportunity score needs demand, supply, and price for every
          CALABARZON province in a shared quarter. One or more are missing here.
        </p>
      </div>
    );
  }

  return (
    <div className="card flex flex-col gap-3">
      <div className="card-head">
        <div>
          <span className="card-kicker">Opportunity</span>
          <p className="text-xs text-muted">
            Peer-relative decision support — not a physical supply gap, not a learned
            target.
          </p>
        </div>
        <span className={verdictBadgeClass(opp.verdict)}>{verdictLabel(opp.verdict)}</span>
      </div>

      <div className="flex items-baseline gap-3">
        <span className="text-2xl font-bold">{opp.score}</span>
        <span className="badge badge-accent">
          {opp.classification?.replaceAll("_", " ").toLowerCase()}
        </span>
        {opp.shared_quarter && (
          <span className="text-xs text-muted">
            shared quarter {formatQuarter(opp.shared_quarter)}
          </span>
        )}
      </div>

      <table className="w-full text-xs">
        <thead className="text-muted">
          <tr>
            <th className="text-left font-medium">Component</th>
            <th className="text-right font-medium">Weight</th>
            <th className="text-right font-medium">Score (0–100)</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(opp.breakdown).map(([key, entry]) => (
            <tr key={key}>
              <td className="py-0.5">{key.replaceAll("_", " ")}</td>
              <td className="text-right">{(entry.weight * 100).toFixed(0)}%</td>
              <td className="text-right">{entry.score.toFixed(0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
